"""
engine.py  -  the vectorized backtest engine. The measuring instrument.

Binding contract (docs/03_STRATEGY_SPECS.md section 0.2):
  - A strategy hands the engine a matrix of TARGET weights W(t), decided at the close
    of date t using only data with timestamps <= t. W_i(t) >= 0, sum_i W_i(t) <= 1.
  - The engine applies W(t) to the returns from t to t+1 via the built-in shift:
        r_p(t) = sum_i W_i(t-1) * r_i(t)  -  the sacred lag. Strategies never shift.
  - Cash is the residual (1 - sum W) and earns exactly zero.

Cost hook (dormant at 0, DEC-002 when on):
  - Trades happen at the close of t, moving the book from W(t-1) to W(t). The traded
    notional is sum_i |W_i(t) - W_i(t-1)| = 2 * tau(t), where tau is the one-sided
    turnover 0.5 * sum |dW|. The cost is applied multiplicatively to the equity at the
    close of t:  E(t) = E(t-1) * (1 + gross_r_p(t)) * (1 - cost_rate * 2 * tau(t)).
  - Inception convention: the very first funding trade of the evaluation window (cash
    -> initial book, which every strategy pays once) is excluded from both turnover
    and costs, so strategies are compared on their ONGOING trading, not their day-one
    buy-in. Documented here and in the results reports.

Turnover is computed on TARGET weights (drift between rebalances ignored), per
docs/03 section 7. Drift-aware simulation with no-trade bands is a Phase 2 extension.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

WEIGHT_TOLERANCE = 1e-9


@dataclass
class BacktestResult:
    """Everything downstream layers need, on the engine's full date index."""
    gross_returns: pd.Series   # daily portfolio return before costs
    net_returns: pd.Series     # after the cost hook (== gross when cost_per_side=0)
    turnover: pd.Series        # daily one-sided turnover tau(t), inception excluded
    costs: pd.Series           # daily cost drag actually charged
    equity: pd.Series          # cumulative net equity, starts at 1.0 on the first index date
    weights: pd.DataFrame      # the validated target weights the run used


def validate_weights(weights: pd.DataFrame, close: pd.DataFrame) -> None:
    """
    Enforce the contract before any math runs:
      - long-only: no weight below zero,
      - no leverage: row sums <= 1,
      - no ghost positions: positive weight requires a non-NaN close that day.
    Raises ValueError with the offending dates, so a buggy strategy fails loudly.
    """
    w = weights.fillna(0.0)
    if (w.to_numpy() < -WEIGHT_TOLERANCE).any():
        bad = w.index[(w < -WEIGHT_TOLERANCE).any(axis=1)]
        raise ValueError(f"Negative weights (long-only contract) on dates: {list(bad[:5])}")
    sums = w.sum(axis=1)
    if (sums > 1.0 + 1e-6).any():
        bad = sums[sums > 1.0 + 1e-6]
        raise ValueError(f"Weights sum > 1 (no-leverage contract) on {len(bad)} dates, "
                         f"first: {bad.index[0]} (sum={bad.iloc[0]:.6f})")
    aligned_close = close.reindex(index=w.index, columns=w.columns)
    ghost = (w > WEIGHT_TOLERANCE) & aligned_close.isna()
    if ghost.to_numpy().any():
        bad = w.index[ghost.any(axis=1)]
        raise ValueError(f"Positive weight on NaN price (ghost position) on dates: {list(bad[:5])}")


def run_backtest(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_side: float = 0.0,
) -> BacktestResult:
    """
    Run the vectorized backtest.

    close:   daily close panel (dates x assets), NaN before an asset exists.
    weights: daily TARGET weights W(t) on the same calendar (subset of columns fine).
    cost_per_side: fraction of traded notional charged per side (0 = costs off).

    Returns BacktestResult on the weights' date index (equity starts at 1.0 there).
    """
    weights = weights.sort_index().fillna(0.0)
    validate_weights(weights, close)

    close = close.reindex(columns=weights.columns)
    rets = close.pct_change(fill_method=None)
    rets = rets.reindex(index=weights.index)

    # The sacred lag: weights decided at t earn the t -> t+1 return.
    w_lag = weights.shift(1).fillna(0.0)
    gross = (w_lag * rets).sum(axis=1, skipna=True)  # W>0 on NaN ret impossible post-validation
    gross.name = "gross"

    # One-sided turnover on target weights; the first funding trade is excluded.
    dw = weights.diff()
    dw.iloc[0] = 0.0  # inception: prior book treated as the initial target, not cash
    tau = 0.5 * dw.abs().sum(axis=1)
    tau.name = "turnover"

    cost = 2.0 * tau * cost_per_side
    cost.name = "cost"

    net = (1.0 + gross) * (1.0 - cost) - 1.0
    net.name = "net"

    equity = (1.0 + net).cumprod()
    # Normalize so the first date of the run is exactly 1.0 growth base:
    # (1+net) on day one already compounds from 1.0, so no extra step needed.
    equity.name = "equity"

    return BacktestResult(
        gross_returns=gross,
        net_returns=net,
        turnover=tau,
        costs=cost,
        equity=equity,
        weights=weights,
    )


def validate_ls_weights(weights: pd.DataFrame, close: pd.DataFrame, gross_cap: float) -> None:
    """
    Long-short contract (Handoff #8): weights may be negative, but
      - gross exposure sum_i |W_i(t)| must stay <= gross_cap,
      - no ghost positions: |weight| > 0 requires a non-NaN close that day.
    """
    w = weights.fillna(0.0)
    gross = w.abs().sum(axis=1)
    if (gross > gross_cap + 1e-6).any():
        bad = gross[gross > gross_cap + 1e-6]
        raise ValueError(f"Gross exposure > {gross_cap} on {len(bad)} dates, "
                         f"first: {bad.index[0]} (gross={bad.iloc[0]:.4f})")
    aligned_close = close.reindex(index=w.index, columns=w.columns)
    ghost = (w.abs() > WEIGHT_TOLERANCE) & aligned_close.isna()
    if ghost.to_numpy().any():
        bad = w.index[ghost.any(axis=1)]
        raise ValueError(f"Nonzero weight on NaN price (ghost position) on dates: {list(bad[:5])}")


def run_ls_backtest(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_per_side: float = 0.0,
    funding_rate_annual: float = 0.0,
    gross_cap: float | None = None,
) -> BacktestResult:
    """
    Long-short vectorized backtest for market-neutral books.

    Same sacred lag as run_backtest: W(t) earns the t -> t+1 return, r_p(t) =
    sum_i W_i(t-1) * r_i(t), weights are NAV fractions, cash earns zero. Shorts are
    abstracted perp exposures: a negative weight earns the negative of the asset
    return. A coin whose price series ends mid-hold contributes zero from its last
    close onward (exit at last print; alphas should exit via the universe first).

    Realism hooks, both dormant by default (Handoff #8 WS-A.3):
      - cost_per_side charged on traded notional sum|dW| (inception excluded),
      - funding_rate_annual/365 charged daily on LAGGED gross exposure (a crude
        stand-in for perp funding paid on both legs; refine at the realism layer).
    """
    from . import config as _config

    gross_cap = _config.MN_GROSS_CAP if gross_cap is None else gross_cap
    weights = weights.sort_index().fillna(0.0)
    validate_ls_weights(weights, close, gross_cap)

    close = close.reindex(columns=weights.columns)
    rets = close.pct_change(fill_method=None).reindex(index=weights.index)

    w_lag = weights.shift(1).fillna(0.0)
    gross_ret = (w_lag * rets).fillna(0.0).sum(axis=1)
    gross_ret.name = "gross"

    dw = weights.diff()
    dw.iloc[0] = 0.0
    tau = 0.5 * dw.abs().sum(axis=1)
    tau.name = "turnover"

    gross_exposure_lag = w_lag.abs().sum(axis=1)
    funding = gross_exposure_lag * (funding_rate_annual / 365.0)
    cost = 2.0 * tau * cost_per_side + funding
    cost.name = "cost"

    net = (1.0 + gross_ret) * (1.0 - cost) - 1.0
    net.name = "net"
    equity = (1.0 + net).cumprod()
    equity.name = "equity"

    return BacktestResult(gross_returns=gross_ret, net_returns=net, turnover=tau,
                          costs=cost, equity=equity, weights=weights)


def run_drift_backtest(
    close: pd.DataFrame,
    rebalance_targets: pd.DataFrame,
    universe: pd.DataFrame | None,
    band: float = 0.20,
    cost_per_side: float = 0.0,
) -> BacktestResult:
    """
    Drift-aware simulation with no-trade bands (docs/05 section 5). Phase 2 engine.

    Between rebalances, ACTUAL weights drift with prices: w_i <- w_i (1+r_i) / (1+r_p).
    On a rebalance day (a row of `rebalance_targets`), each asset trades only if:
      - its holder status flips (target zero vs held, or newly held), which ALWAYS
        trades (signal flips and gate flips are never suppressed), or
      - |target - drifted| > band * target (the no-trade band suppresses re-truing).
    Mid-week universe exits force a full sell of that name immediately.

    Costs: traded notional sum|w_new - w_drift| charged cost_per_side multiplicatively
    at that close. The inception funding trade (first rebalance from all-cash) is
    excluded from turnover and costs, matching run_backtest's convention.

    The date index runs from the first rebalance day to the end of `close`.
    """
    if not (0.0 <= band < 1.0):
        raise ValueError(f"band must be in [0, 1): {band}")
    validate_weights(rebalance_targets, close)

    cols = list(rebalance_targets.columns)
    t0 = rebalance_targets.index[0]
    index = close.index[close.index >= t0]
    rets = close[cols].pct_change(fill_method=None).reindex(index).to_numpy()
    is_rebalance = index.isin(rebalance_targets.index)
    targets = rebalance_targets.reindex(index)[cols].to_numpy()
    if universe is not None:
        u = universe.reindex(index=index, columns=cols).fillna(False).to_numpy()
    else:
        u = np.ones((len(index), len(cols)), dtype=bool)

    n = len(index)
    w = np.zeros(len(cols))
    gross = np.zeros(n)
    tau = np.zeros(n)
    cost = np.zeros(n)
    net = np.zeros(n)
    weights_hist = np.zeros((n, len(cols)))

    for i in range(n):
        if i > 0:
            r = np.nan_to_num(rets[i], nan=0.0)
            rp = float(np.dot(w, r))
            gross[i] = rp
            w = w * (1.0 + r) / (1.0 + rp) if rp > -1.0 else np.zeros_like(w)

        if is_rebalance[i]:
            tgt = np.nan_to_num(targets[i], nan=0.0)
            new_w = w.copy()
            for j in range(len(cols)):
                flip = (tgt[j] > WEIGHT_TOLERANCE) != (w[j] > WEIGHT_TOLERANCE)
                if flip:
                    new_w[j] = tgt[j]
                elif tgt[j] > WEIGHT_TOLERANCE and abs(tgt[j] - w[j]) > band * tgt[j]:
                    new_w[j] = tgt[j]
        else:
            new_w = w.copy()
        # Mid-week universe exit: force-sell names that left the screen.
        exited = (~u[i]) & (new_w > WEIGHT_TOLERANCE)
        new_w[exited] = 0.0

        traded = float(np.abs(new_w - w).sum()) if i > 0 else 0.0  # inception excluded
        tau[i] = 0.5 * traded
        cost[i] = traded * cost_per_side
        net[i] = (1.0 + gross[i]) * (1.0 - cost[i]) - 1.0
        w = new_w
        weights_hist[i] = w

    net_s = pd.Series(net, index=index, name="net")
    gross_s = pd.Series(gross, index=index, name="gross")
    tau_s = pd.Series(tau, index=index, name="turnover")
    cost_s = pd.Series(cost, index=index, name="cost")
    equity = (1.0 + net_s).cumprod()
    equity.name = "equity"
    weights_df = pd.DataFrame(weights_hist, index=index, columns=cols)
    return BacktestResult(gross_returns=gross_s, net_returns=net_s, turnover=tau_s,
                          costs=cost_s, equity=equity, weights=weights_df)


def evaluation_window(index: pd.DatetimeIndex, warmup_days: int) -> pd.Timestamp:
    """
    docs/03 section 0.5: the common evaluation window starts at the first rebalance
    day (Monday) at least `warmup_days` after the start of the cleaned panel.
    Returns that start date; the window always runs to the end of the index.
    """
    threshold = index[0] + pd.Timedelta(days=warmup_days)
    mondays = index[(index.weekday == 0) & (index >= threshold)]
    if len(mondays) == 0:
        raise ValueError(f"No Monday found after {warmup_days}-day warmup: panel too short")
    return mondays[0]


def rebalance_days(index: pd.DatetimeIndex, start: pd.Timestamp | None = None) -> pd.DatetimeIndex:
    """Every Monday in the index (docs/03 section 0.3), optionally from `start`."""
    days = index[index.weekday == 0]
    if start is not None:
        days = days[days >= start]
    return days


def expand_rebalance_weights(
    rebalance_weights: pd.DataFrame,
    index: pd.DatetimeIndex,
    universe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Turn weights defined on rebalance days into a daily target matrix per docs/03
    section 0.3: hold the last rebalance target constant between Mondays, and on
    non-rebalance days force W_i(t) = W_i(last rebalance) * U_i(t) (mid-week universe
    exits go to cash immediately, no renormalization).
    """
    daily = rebalance_weights.reindex(index).ffill().fillna(0.0)
    if universe is not None:
        mask = universe.reindex(index=index, columns=daily.columns).fillna(False).astype(float)
        is_rebalance = pd.Series(index.isin(rebalance_weights.index), index=index)
        # On rebalance days the strategy already consumed the universe; between them,
        # apply the exit rule elementwise.
        daily = daily.where(is_rebalance, daily * mask)
    return daily
