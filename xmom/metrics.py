"""
metrics.py  -  turn a return series into the numbers we judge strategies on.

Definitions are copied verbatim from docs/03_STRATEGY_SPECS.md section 7 and are
binding. Annualization is 365 (crypto trades every calendar day, MASTER_BRIEF
guardrail), risk-free rate is 0, std uses ddof=1.

All functions take the DAILY series sliced to the common evaluation window; the
caller owns the slicing (engine.evaluation_window).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

ANN = config.ANNUALIZATION  # 365


def equity_curve(returns: pd.Series) -> pd.Series:
    """Compound daily returns into an equity curve starting at 1.0."""
    return (1.0 + returns).cumprod()


def total_return(returns: pd.Series) -> float:
    return float((1.0 + returns).prod() - 1.0)


def cagr(returns: pd.Series) -> float:
    n_days = (returns.index[-1] - returns.index[0]).days
    if n_days <= 0:
        return np.nan
    growth = float((1.0 + returns).prod())
    if growth <= 0:
        return -1.0
    return growth ** (ANN / n_days) - 1.0


def ann_vol(returns: pd.Series) -> float:
    return float(returns.std(ddof=1) * np.sqrt(ANN))


def sharpe(returns: pd.Series) -> float:
    sd = returns.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return np.nan
    return float(returns.mean() / sd * np.sqrt(ANN))


def sortino(returns: pd.Series) -> float:
    downside = np.minimum(returns, 0.0)
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd):
        return np.nan
    return float(returns.mean() / dd * np.sqrt(ANN))


def max_drawdown(returns: pd.Series) -> float:
    eq = equity_curve(returns)
    return float((eq / eq.cummax() - 1.0).min())


def calmar(returns: pd.Series) -> float:
    dd = abs(max_drawdown(returns))
    if dd == 0:
        return np.nan
    return cagr(returns) / dd


def annual_turnover(turnover: pd.Series) -> float:
    """tau summed and scaled to a year: sum_t tau(t) * 365 / n_days (one-sided)."""
    n_days = (turnover.index[-1] - turnover.index[0]).days
    if n_days <= 0:
        return np.nan
    return float(turnover.sum() * ANN / n_days)


def hit_rate(returns: pd.Series, weights: pd.DataFrame) -> float:
    """Fraction of days with r_p > 0, among days with gross exposure W(t-1) > 0."""
    exposure = weights.shift(1).fillna(0.0).sum(axis=1).reindex(returns.index)
    exposed = exposure > WEIGHT_EXPOSURE_EPS
    if exposed.sum() == 0:
        return np.nan
    return float((returns[exposed] > 0).mean())


def time_in_market(returns: pd.Series, weights: pd.DataFrame) -> float:
    """Fraction of days with gross exposure sum_i W_i(t-1) > 0."""
    exposure = weights.shift(1).fillna(0.0).sum(axis=1).reindex(returns.index)
    return float((exposure > WEIGHT_EXPOSURE_EPS).mean())


WEIGHT_EXPOSURE_EPS = 1e-9


def summarize(returns: pd.Series, turnover: pd.Series, weights: pd.DataFrame) -> dict:
    """One metrics row, per the docs/03 section 7 table."""
    return {
        "total_return": total_return(returns),
        "cagr": cagr(returns),
        "ann_vol": ann_vol(returns),
        "sharpe": sharpe(returns),
        "sortino": sortino(returns),
        "max_drawdown": max_drawdown(returns),
        "calmar": calmar(returns),
        "annual_turnover": annual_turnover(turnover),
        "hit_rate": hit_rate(returns, weights),
        "time_in_market": time_in_market(returns, weights),
        "n_days": int(len(returns)),
        "start": returns.index[0].date().isoformat(),
        "end": returns.index[-1].date().isoformat(),
    }
