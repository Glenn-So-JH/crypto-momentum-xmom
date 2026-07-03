"""
alphas.py  -  the alpha stable (Handoff #8 WS-B).

Each alpha is a pure function close-panel -> raw signal panel (same shape, strictly
trailing). The market-neutral pipeline (xmom.neutral) then z-scores the signal
cross-sectionally and builds the hedged long-short book, so what differentiates the
alphas is the INFORMATION in the raw signal, not the portfolio construction.

The stable aims for economically distinct ideas, not one idea reparametrized:
  - ts_trend_{10,30,90}: own trailing return at fast/medium/slow horizons (the
    classic time-series trend family; different horizons capture different flows),
  - xs_rank_{21,63}: cross-sectional percentile rank of trailing return (the
    relative-momentum family, rank-transformed so outliers cannot dominate),
  - sharpe_mom_30: trailing return scaled by its own realized vol (risk-adjusted
    momentum: is the move signal or just variance?),
  - donchian_55: position inside the trailing 55-day close-price channel (breakout
    logic: where price sits in its recent range, not how fast it got there),
  - macd_12_26: EMA(12) minus EMA(26), price-normalized (moving-average distance:
    trend curvature at short horizons),
  - mom_accel_30: 14-day change in 30-day momentum (acceleration: is the trend
    strengthening or fading?).

A funding/term-structure momentum sleeve is deliberately ABSENT: it needs perp
funding-rate data we do not ingest yet. Labeled future work in the report.

Notes: the discovery panel stores daily closes, so the Donchian channel is the
close-based variant. All windows are trailing; tests perturb the future and assert
earlier signal values do not move.
"""

from __future__ import annotations

import pandas as pd


def ts_trend(close: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Own trailing L-day simple return."""
    return close.pct_change(lookback, fill_method=None)


def xs_rank(close: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Cross-sectional percentile rank of the trailing return, centered at 0."""
    r = close.pct_change(lookback, fill_method=None)
    return r.rank(axis=1, pct=True) - 0.5


def sharpe_mom(close: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
    """Trailing return divided by trailing daily-return vol (risk-adjusted momentum)."""
    r = close.pct_change(lookback, fill_method=None)
    vol = close.pct_change(fill_method=None).rolling(lookback, min_periods=lookback).std(ddof=1)
    return r / vol.where(vol > 0)


def donchian(close: pd.DataFrame, window: int = 55) -> pd.DataFrame:
    """
    Position inside the trailing close-price channel, in [-1, 1]:
    +1 at the channel high, -1 at the low. Flat channels give NaN (no information).
    """
    hi = close.rolling(window, min_periods=window).max()
    lo = close.rolling(window, min_periods=window).min()
    half_range = 0.5 * (hi - lo)
    mid = 0.5 * (hi + lo)
    return (close - mid) / half_range.where(half_range > 0)


def macd(close: pd.DataFrame, fast: int = 12, slow: int = 26) -> pd.DataFrame:
    """EMA(fast) minus EMA(slow), normalized by price (scale-free trend distance)."""
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    return (ema_fast - ema_slow) / close


def mom_accel(close: pd.DataFrame, lookback: int = 30, delta: int = 14) -> pd.DataFrame:
    """Change in L-day momentum over the last `delta` days (trend acceleration)."""
    mom = close.pct_change(lookback, fill_method=None)
    return mom - mom.shift(delta)


# The registry the analytics layer iterates over. Keys are ledger family names.
ALPHAS: dict[str, dict] = {
    "ts_trend_10": {"fn": lambda c: ts_trend(c, 10), "family": "ts_trend",
                    "description": "10d own trailing return (fast trend)"},
    "ts_trend_30": {"fn": lambda c: ts_trend(c, 30), "family": "ts_trend",
                    "description": "30d own trailing return (medium trend)"},
    "ts_trend_90": {"fn": lambda c: ts_trend(c, 90), "family": "ts_trend",
                    "description": "90d own trailing return (slow trend)"},
    "xs_rank_21": {"fn": lambda c: xs_rank(c, 21), "family": "xs_rank",
                   "description": "21d return, cross-sectional percentile rank"},
    "xs_rank_63": {"fn": lambda c: xs_rank(c, 63), "family": "xs_rank",
                   "description": "63d return, cross-sectional percentile rank"},
    "sharpe_mom_30": {"fn": lambda c: sharpe_mom(c, 30), "family": "sharpe_mom",
                      "description": "30d return / 30d realized vol"},
    "donchian_55": {"fn": lambda c: donchian(c, 55), "family": "breakout",
                    "description": "position in trailing 55d close channel"},
    "macd_12_26": {"fn": lambda c: macd(c, 12, 26), "family": "ma_distance",
                   "description": "(EMA12 - EMA26) / price"},
    "mom_accel_30": {"fn": lambda c: mom_accel(c, 30, 14), "family": "acceleration",
                     "description": "14d change in 30d momentum"},
}
