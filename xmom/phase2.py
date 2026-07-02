"""
phase2.py  -  the Phase 2 base case and challenger (docs/05 sections 2 and 3).

Base case (DEC-001): long-only time-series momentum at a short lookback, gated by a
BTC 200-day SMA regime switch, sized by inverse volatility with a 25% per-name cap,
scaled to a 30% annualized vol target (DEC-003, de-risk only), weekly rebalance with
no-trade bands (the drift engine applies the bands; this module produces targets).

Challenger: identical overlays, but the holder set is the top-3 by trailing return
(relative selection) instead of own-return-positive (absolute selection). The
comparison isolates exactly one difference, per docs/05 section 3.

Implementation choices registered before running (see PHASE2_RESULTS registration):
per-asset vol = trailing 30-day std of daily returns; portfolio vol forecast =
trailing 90-day covariance of daily returns, annualized with 365.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import engine, strategies

VOL_WINDOW = 30          # per-asset sizing vol (registered default)
COV_WINDOW = 90          # portfolio vol forecast window (registered default)
NAME_CAP = 0.25          # per-name weight cap (docs/05 section 2)
VOL_TARGET = 0.30        # DEC-003, annualized, de-risk only
GATE_SMA = 200           # BTC regime gate length
ANN = 365


def cap_weights(w: pd.Series, cap: float = NAME_CAP, max_iter: int = 50) -> pd.Series:
    """
    Cap any single name at `cap`, redistributing the excess proportionally among
    uncapped names. If everything hits the cap, the remainder stays in cash (long-only,
    no leverage: total may end below 1).
    """
    w = w.copy()
    for _ in range(max_iter):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = float((w[over] - cap).sum())
        w[over] = cap
        under = ~over & (w > 0)
        if not under.any() or w[under].sum() <= 0:
            break  # everyone capped: excess goes to cash
        w[under] = w[under] + excess * (w[under] / w[under].sum())
    return w.clip(upper=cap + 1e-12)


def gate_series(close: pd.DataFrame, asset: str = "BTC", n: int = GATE_SMA) -> pd.Series:
    """True when the market regime is ON (BTC strictly above its N-day SMA)."""
    sma = close[asset].rolling(n, min_periods=n).mean()
    return close[asset] > sma


def build_targets(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    t0: pd.Timestamp,
    lookback: int = 21,
    mode: str = "tsmom",          # "tsmom" (base) or "xsmom" (challenger)
    top_n: int = 3,
    skip: int = 0,
    vol_target: float = VOL_TARGET,
    name_cap: float = NAME_CAP,
    gate_n: int = GATE_SMA,
) -> pd.DataFrame:
    """
    Target weights on rebalance days (Mondays from t0), for the drift engine.
    All inputs are trailing; nothing here can see past the rebalance close.
    """
    rets = close.pct_change(fill_method=None)
    vol = rets.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=1)
    r_sig = strategies.trailing_return(close, lookback, skip)
    elig = strategies.eligibility(close, universe, lookback, skip)
    gate = gate_series(close, "BTC", gate_n)
    reb_days = engine.rebalance_days(close.index, start=t0)

    targets = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        if not bool(gate.loc[t]):
            continue  # regime off: whole book in cash
        eligible = elig.loc[t] & vol.loc[t].notna() & (vol.loc[t] > 0)
        if mode == "tsmom":
            holders = eligible & (r_sig.loc[t] > 0)
            names = list(holders[holders].index)
        else:
            names = strategies._ranked_selection(
                r_sig.loc[t], eligible, ascending=False, top_n=top_n, quantile=None
            )
        if not names:
            continue

        inv_vol = 1.0 / vol.loc[t, names]
        w = inv_vol / inv_vol.sum()
        w = cap_weights(w, name_cap)

        # Vol targeting, de-risk only: scale down if the trailing-cov forecast runs hot.
        hist = rets[names].loc[:t].tail(COV_WINDOW)
        if len(hist) >= VOL_WINDOW:
            cov = hist.cov(ddof=1).to_numpy() * ANN
            forecast = float(np.sqrt(max(w.to_numpy() @ cov @ w.to_numpy(), 0.0)))
            if forecast > vol_target and forecast > 0:
                w = w * (vol_target / forecast)
        targets.loc[t, w.index] = w.to_numpy()
    return targets
