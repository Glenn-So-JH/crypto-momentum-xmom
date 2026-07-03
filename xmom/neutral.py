"""
neutral.py  -  market-neutral long-short book construction (Handoff #8 WS-A).

Pipeline per rebalance day, for any raw alpha signal:
  1. eligibility: in point-in-time universe, valid price, valid vol and beta,
  2. cross-sectional z-score of the signal over eligible names, winsorized,
  3. candidate weights proportional to z / vol (inverse-vol sizing), unit gross,
  4. beta hedge: adjust the market-asset leg so the book's ex-ante beta is ~0
     (betas from a rolling look-ahead-safe OLS against the market factor),
  5. one scalar s applies the vol target and the caps together:
         s = min(vol_target / forecast_vol, gross_cap / gross, name_cap / max|w|)
     Scaling by a single scalar preserves the book's shape, so the hedge ratio
     (and therefore beta neutrality) survives the caps by construction. The hedge
     leg is exempt from the name cap (capping it would re-introduce beta).

Risk model: single market factor. r_i = beta_i r_m + e_i, so
  portfolio var = (w . beta)^2 var_m + sum_i w_i^2 var_e,i
which for a hedged book is dominated by the diagonal residual term. Deliberately
simple; a sector factor is noted as future work.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, engine


def rolling_beta(
    rets: pd.DataFrame,
    market_rets: pd.Series,
    window: int = config.MN_BETA_WINDOW,
    min_periods: int = config.MN_BETA_MIN_PERIODS,
) -> pd.DataFrame:
    """Trailing OLS beta of each column to the market: cov(r_i, r_m) / var(r_m)."""
    cov = rets.rolling(window, min_periods=min_periods).cov(market_rets)
    var = market_rets.rolling(window, min_periods=min_periods).var()
    return cov.div(var, axis=0)


def residual_vol(
    rets: pd.DataFrame,
    market_rets: pd.Series,
    betas: pd.DataFrame,
    window: int = config.MN_RESID_VOL_WINDOW,
) -> pd.DataFrame:
    """Trailing std of the factor-model residual e_i = r_i - beta_i r_m."""
    resid = rets - betas * np.asarray(market_rets).reshape(-1, 1)
    return resid.rolling(window, min_periods=window // 2).std(ddof=1)


def cross_sectional_zscore(
    signal_row: pd.Series,
    eligible: pd.Series,
    winsor: float = config.MN_ZSCORE_WINSOR,
) -> pd.Series:
    """Z-score over the eligible cross-section, clipped at +/- winsor. Zero elsewhere."""
    z = pd.Series(0.0, index=signal_row.index)
    values = signal_row[eligible[eligible].index].dropna()
    if len(values) < 5:
        return z  # too thin a cross-section to standardize meaningfully
    sd = values.std(ddof=1)
    if not sd > 0:
        return z
    z.loc[values.index] = ((values - values.mean()) / sd).clip(-winsor, winsor)
    return z


def forecast_vol(w: pd.Series, betas: pd.Series, resid: pd.Series, market_vol_daily: float) -> float:
    """Annualized factor-model vol forecast for a weight row."""
    b = float((w * betas.reindex(w.index).fillna(0.0)).sum())
    factor_var = (b * market_vol_daily) ** 2
    resid_var = float(((w ** 2) * (resid.reindex(w.index).fillna(0.0) ** 2)).sum())
    return float(np.sqrt(max(factor_var + resid_var, 0.0) * config.ANNUALIZATION))


def build_book_row(
    z: pd.Series,
    vol: pd.Series,
    betas: pd.Series,
    resid: pd.Series,
    market_vol_daily: float,
    hedge_asset: str = config.MN_MARKET_ASSET,
    vol_target: float = config.MN_VOL_TARGET,
    gross_cap: float = config.MN_GROSS_CAP,
    name_cap: float = config.MN_NAME_CAP,
) -> pd.Series:
    """One rebalance day: z-scores in, hedged, sized, capped weight row out."""
    w = pd.Series(0.0, index=z.index)
    live = z[(z != 0.0) & vol.notna() & (vol > 0) & betas.notna()]
    if live.empty:
        return w
    raw = live / vol.loc[live.index]
    gross = raw.abs().sum()
    if not gross > 0:
        return w
    w.loc[raw.index] = raw / gross  # unit-gross candidate book

    # Beta hedge on the market leg (its beta to itself is 1 by construction).
    book_beta = float((w * betas.reindex(w.index).fillna(0.0)).sum())
    w.loc[hedge_asset] = w.get(hedge_asset, 0.0) - book_beta

    # One scalar enforces vol target and caps while preserving the hedge ratio.
    fc = forecast_vol(w, betas, resid, market_vol_daily)
    scalars = []
    if fc > 0:
        scalars.append(vol_target / fc)
    g = w.abs().sum()
    if g > 0:
        scalars.append(gross_cap / g)
    non_hedge = w.drop(index=hedge_asset, errors="ignore").abs()
    if len(non_hedge) and non_hedge.max() > 0:
        scalars.append(name_cap / non_hedge.max())
    return w * min(scalars) if scalars else w


def build_alpha_book(
    close: pd.DataFrame,
    universe: pd.DataFrame,
    signal: pd.DataFrame,
    t0: pd.Timestamp,
    **kwargs,
) -> pd.DataFrame:
    """
    Full pipeline: raw signal panel -> daily beta-neutral long-short target weights.
    Weekly Monday rebalance, held between rebalances, forced flat on universe exit.
    Everything trailing; nothing reads past the rebalance close.
    """
    rets = close.pct_change(fill_method=None)
    market_rets = rets[config.MN_MARKET_ASSET]
    vol = rets.rolling(config.MN_VOL_WINDOW, min_periods=config.MN_VOL_WINDOW).std(ddof=1)
    betas = rolling_beta(rets, market_rets)
    resid = residual_vol(rets, market_rets, betas)
    market_vol = market_rets.rolling(config.MN_VOL_WINDOW,
                                     min_periods=config.MN_VOL_WINDOW).std(ddof=1)
    u = universe.reindex(index=close.index, columns=close.columns).fillna(False)

    reb_days = engine.rebalance_days(close.index, start=t0)
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=close.columns)
    for t in reb_days:
        eligible = u.loc[t] & close.loc[t].notna() & signal.loc[t].notna() \
            & vol.loc[t].notna() & betas.loc[t].notna()
        if not eligible.any() or not (market_vol.loc[t] > 0):
            continue
        z = cross_sectional_zscore(signal.loc[t], eligible)
        reb_w.loc[t] = build_book_row(
            z, vol.loc[t], betas.loc[t], resid.loc[t], float(market_vol.loc[t]), **kwargs
        )

    daily = reb_w.reindex(close.index).ffill().fillna(0.0)
    is_reb = pd.Series(close.index.isin(reb_days), index=close.index)
    daily = daily.where(is_reb, daily * u.astype(float))  # mid-week exits go flat
    daily.loc[close.index < t0] = 0.0
    return daily
