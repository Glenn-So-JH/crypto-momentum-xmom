"""
strategies.py  -  the Stage 1C classic-strategy library (S1 to S6).

Every function implements its section of docs/03_STRATEGY_SPECS.md exactly and returns
a DAILY target-weight DataFrame ready for the engine: weights are zero before the
evaluation-window start t0, rebalance on Mondays (section 0.3), respect eligibility
(section 0.4), and never shift (the engine owns the sacred lag).

Deterministic tie-break (section 0.6): assets are pre-sorted alphabetically and all
rank sorts are stable, so equal signal values resolve by ticker ascending.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import engine


def trailing_return(close: pd.DataFrame, lookback: int, skip: int = 0) -> pd.DataFrame:
    """R(t; L, k) = P(t-k) / P(t-L) - 1, on the daily-complete panel (section 0.1)."""
    return close.shift(skip) / close.shift(lookback) - 1.0


def eligibility(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    lookback: int,
    skip: int = 0,
) -> pd.DataFrame:
    """Section 0.4: in universe at t, valid closes at t-L, t-k, and t."""
    u = universe.reindex(index=close.index, columns=close.columns).fillna(False)
    return (
        u
        & close.shift(lookback).notna()
        & close.shift(skip).notna()
        & close.notna()
    )


def _empty_daily(close: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=close.index, columns=close.columns)


def _zero_before(weights: pd.DataFrame, t0: pd.Timestamp) -> pd.DataFrame:
    weights = weights.copy()
    weights.loc[weights.index < t0] = 0.0
    return weights


def s1_buy_and_hold(close: pd.DataFrame, t0: pd.Timestamp, asset: str = "BTC") -> pd.DataFrame:
    """Section 1: 100% in `asset` from t0, never rebalanced, no universe rule."""
    w = _empty_daily(close)
    w.loc[w.index >= t0, asset] = 1.0
    return w


def s2_equal_weight(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    t0: pd.Timestamp,
) -> pd.DataFrame:
    """Section 2: 1/n over all eligible assets, weekly, universe-exit between Mondays."""
    elig = eligibility(close, universe, lookback=1, skip=0)
    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        e = elig.loc[t]
        n = int(e.sum())
        if n > 0:
            reb_w.loc[t, e[e].index] = 1.0 / n
    daily = engine.expand_rebalance_weights(reb_w, close.index, universe)
    return _zero_before(daily, t0)


def s3_ma_filter(
    close: pd.DataFrame,
    t0: pd.Timestamp,
    asset: str = "BTC",
    n: int = 200,
) -> pd.DataFrame:
    """Section 3: hold `asset` when price > its own N-day SMA at the Monday close, else cash."""
    sma = close[asset].rolling(n, min_periods=n).mean()
    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    signal = (close[asset] > sma).astype(float)  # strict inequality per spec
    reb_w[asset] = signal.reindex(reb_days).fillna(0.0)
    daily = engine.expand_rebalance_weights(reb_w, close.index, universe=None)
    return _zero_before(daily, t0)


def s4_tsmom(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    t0: pd.Timestamp,
    lookback: int,
) -> pd.DataFrame:
    """Section 4: equal-weight every eligible asset whose own L-day return is > 0."""
    r = trailing_return(close, lookback, 0)
    elig = eligibility(close, universe, lookback, 0)
    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        holders = elig.loc[t] & (r.loc[t] > 0)
        h = int(holders.sum())
        if h > 0:
            reb_w.loc[t, holders[holders].index] = 1.0 / h
    daily = engine.expand_rebalance_weights(reb_w, close.index, universe)
    return _zero_before(daily, t0)


def _ranked_selection(
    scores: pd.Series,
    eligible: pd.Series,
    ascending: bool,
    top_n: int | None,
    quantile: float | None,
) -> list[str]:
    """
    Rank eligible assets by score with the section 0.6 tie-break and return the
    selected tickers. Exactly one of top_n / quantile must be set.
    """
    s = scores[eligible[eligible].index].dropna()
    if s.empty:
        return []
    s = s.sort_index()  # alphabetical first...
    s = s.sort_values(ascending=ascending, kind="stable")  # ...stable sort keeps it on ties
    n_eligible = len(s)
    if top_n is not None:
        n_hold = min(top_n, n_eligible)
    else:
        n_hold = max(1, int(np.ceil(quantile * n_eligible)))
    return list(s.index[:n_hold])


def s5_xsmom(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    t0: pd.Timestamp,
    lookback: int = 30,
    skip: int = 0,
    top_n: int | None = 3,
    quantile: float | None = None,
) -> pd.DataFrame:
    """Section 5: hold the top-N (or top-quantile) of eligible assets by R(t; L, k)."""
    r = trailing_return(close, lookback, skip)
    elig = eligibility(close, universe, lookback, skip)
    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        selected = _ranked_selection(r.loc[t], elig.loc[t], ascending=False,
                                     top_n=top_n, quantile=quantile)
        if selected:
            reb_w.loc[t, selected] = 1.0 / len(selected)
    daily = engine.expand_rebalance_weights(reb_w, close.index, universe)
    return _zero_before(daily, t0)


def s6_reversal(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    t0: pd.Timestamp,
    lookback: int = 7,
    bottom_n: int = 3,
) -> pd.DataFrame:
    """Section 6: hold the bottom-N of eligible assets by trailing 7-day return."""
    r = trailing_return(close, lookback, 0)
    elig = eligibility(close, universe, lookback, 0)
    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        selected = _ranked_selection(r.loc[t], elig.loc[t], ascending=True,
                                     top_n=bottom_n, quantile=None)
        if selected:
            reb_w.loc[t, selected] = 1.0 / len(selected)
    daily = engine.expand_rebalance_weights(reb_w, close.index, universe)
    return _zero_before(daily, t0)
