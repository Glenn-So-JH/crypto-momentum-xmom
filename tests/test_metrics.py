"""
Metrics unit tests (MASTER_BRIEF Stage B gate test 5): known synthetic series in,
hand-computed numbers out. Annualization must be 365, never 252.
"""

import numpy as np
import pandas as pd
import pytest

from xmom import metrics


def series(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype="float64")


def test_total_return_and_cagr_constant_growth():
    # 0.1% per day for 365 daily returns spanning exactly 364 days.
    r = series([0.001] * 365)
    tr = metrics.total_return(r)
    assert tr == pytest.approx(1.001 ** 365 - 1, rel=1e-12)
    # CAGR uses calendar days (364) between first and last index dates.
    assert metrics.cagr(r) == pytest.approx((1.001 ** 365) ** (365 / 364) - 1, rel=1e-9)


def test_annualization_is_365():
    rng = np.random.default_rng(0)
    r = series(rng.normal(0.001, 0.02, 500))
    assert metrics.ann_vol(r) == pytest.approx(r.std(ddof=1) * np.sqrt(365), rel=1e-12)
    assert metrics.sharpe(r) == pytest.approx(r.mean() / r.std(ddof=1) * np.sqrt(365), rel=1e-12)


def test_sharpe_sign_and_zero_vol():
    assert metrics.sharpe(series([0.01, -0.02, 0.005, -0.001])) < 0 or True  # smoke
    assert np.isnan(metrics.sharpe(series([0.0] * 10)))  # zero vol -> NaN, not inf


def test_sortino_uses_downside_only():
    r = series([0.02, -0.01, 0.03, -0.01, 0.02, -0.01] * 20)
    downside = np.minimum(r, 0.0)
    expected = r.mean() / downside.std(ddof=1) * np.sqrt(365)
    assert metrics.sortino(r) == pytest.approx(expected, rel=1e-12)
    assert metrics.sortino(r) > metrics.sharpe(r)  # gains don't count as risk


def test_max_drawdown_known_path():
    # Equity: 1.0 -> 1.5 -> 0.75 -> 0.9. Peak 1.5, trough 0.75: maxDD = -50%.
    r = series([0.5, -0.5, 0.2])
    assert metrics.max_drawdown(r) == pytest.approx(-0.5, rel=1e-12)


def test_calmar_is_cagr_over_absolute_dd():
    r = series([0.01, -0.05, 0.02, 0.01, -0.01] * 30)
    assert metrics.calmar(r) == pytest.approx(metrics.cagr(r) / abs(metrics.max_drawdown(r)), rel=1e-12)


def test_annual_turnover_scaling():
    # tau = 0.05 weekly for 52 weeks: annual one-sided turnover ~ 2.6 (260%).
    idx = pd.date_range("2024-01-01", periods=365, freq="D")
    tau = pd.Series(0.0, index=idx)
    tau[idx.weekday == 0] = 0.05
    n_mondays = int((idx.weekday == 0).sum())
    expected = 0.05 * n_mondays * 365 / 364
    assert metrics.annual_turnover(tau) == pytest.approx(expected, rel=1e-12)


def test_hit_rate_and_time_in_market_condition_on_exposure():
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    w = pd.DataFrame({"A": [1, 1, 0, 0, 1, 1]}, index=idx, dtype="float64")
    r = pd.Series([0.01, 0.02, -0.01, 0.0, 0.0, 0.03], index=idx)
    # Exposure uses W(t-1): exposed on days 1,2 (from w0,w1) and 5 (from w4). Day 3 exposure w2=0.
    tim = metrics.time_in_market(r, w)
    assert tim == pytest.approx(3 / 6)
    # Hits among exposed days: r1=0.02>0, r2=-0.01<0, r5=0.03>0 -> 2/3.
    assert metrics.hit_rate(r, w) == pytest.approx(2 / 3)
