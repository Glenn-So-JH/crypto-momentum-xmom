"""WS-A tests: long-short engine, rolling beta, hedged book construction, caps."""

import numpy as np
import pandas as pd
import pytest

from xmom import config, engine, neutral


def make_close(n=400, seed=21, cols=("BTC", "AAA", "BBB", "CCC", "DDD", "EEE")):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-03", periods=n, freq="D")
    idx.name = "date"
    m = rng.normal(0.001, 0.03, n)  # market factor
    data = {}
    for j, c in enumerate(cols):
        if c == "BTC":
            r = m
        else:
            r = 0.5 * (j) / len(cols) * 2 * m + rng.normal(0.0002, 0.02, n)  # varied betas
        data[c] = 100.0 * np.exp(np.cumsum(r))
    return pd.DataFrame(data, index=idx)


# --- long-short engine --------------------------------------------------------------

def test_short_profits_when_price_falls():
    idx = pd.date_range("2023-01-02", periods=50, freq="D")
    close = pd.DataFrame({"A": 100.0 * 0.99 ** np.arange(50)}, index=idx)
    w = pd.DataFrame(-1.0, index=idx, columns=["A"])
    result = engine.run_ls_backtest(close, w)
    assert (result.gross_returns.iloc[1:] > 0).all()   # short a falling asset: earn
    assert result.equity.iloc[-1] > 1.5


def test_long_short_pair_arithmetic():
    idx = pd.date_range("2023-01-02", periods=3, freq="D")
    close = pd.DataFrame({"A": [100.0, 110.0, 121.0], "B": [100.0, 95.0, 90.25]}, index=idx)
    w = pd.DataFrame({"A": 0.5, "B": -0.5}, index=idx)
    result = engine.run_ls_backtest(close, w)
    # Day 2: 0.5*(+10%) + (-0.5)*(-5%) = 7.5%
    assert result.gross_returns.iloc[1] == pytest.approx(0.075, rel=1e-12)


def test_gross_cap_enforced():
    idx = pd.date_range("2023-01-02", periods=10, freq="D")
    close = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)
    w = pd.DataFrame({"A": 1.5, "B": -1.5}, index=idx)  # gross 3.0 > cap 2.0
    with pytest.raises(ValueError, match="Gross exposure"):
        engine.run_ls_backtest(close, w)


def test_funding_charged_on_lagged_gross():
    idx = pd.date_range("2023-01-02", periods=10, freq="D")
    close = pd.DataFrame({"A": 100.0, "B": 100.0}, index=idx)  # flat prices
    w = pd.DataFrame({"A": 0.6, "B": -0.6}, index=idx)          # gross 1.2, no trading
    result = engine.run_ls_backtest(close, w, funding_rate_annual=0.10)
    expected_daily = 1.2 * 0.10 / 365.0
    assert result.net_returns.iloc[2] == pytest.approx(-expected_daily, rel=1e-9)
    assert result.net_returns.iloc[0] == 0.0  # no lagged exposure on day one


# --- beta and construction ----------------------------------------------------------

def test_rolling_beta_recovers_known_beta():
    n = 400
    rng = np.random.default_rng(3)
    idx = pd.date_range("2022-01-03", periods=n, freq="D")
    m = pd.Series(rng.normal(0, 0.03, n), index=idx)
    rets = pd.DataFrame({"X": 2.0 * m + rng.normal(0, 0.001, n), "M": m}, index=idx)
    betas = neutral.rolling_beta(rets, rets["M"])
    assert betas["X"].iloc[-1] == pytest.approx(2.0, abs=0.05)
    assert betas["M"].iloc[-1] == pytest.approx(1.0, abs=1e-9)


def test_zscore_centered_winsorized_and_thin_guard():
    idx = [f"C{i}" for i in range(10)]
    sig = pd.Series(np.arange(10, dtype=float), index=idx)
    sig.iloc[-1] = 1000.0  # wild outlier
    eligible = pd.Series(True, index=idx)
    z = neutral.cross_sectional_zscore(sig, eligible)
    assert abs(z.mean()) < 1.0e-1          # roughly centered (winsor breaks exact zero)
    assert z.abs().max() <= config.MN_ZSCORE_WINSOR + 1e-12
    thin = neutral.cross_sectional_zscore(sig.iloc[:3], pd.Series(True, index=idx[:3]))
    assert (thin == 0).all()               # under 5 names: no z-scores


def test_book_row_is_beta_neutral_and_capped():
    close = make_close()
    rets = close.pct_change(fill_method=None)
    betas = neutral.rolling_beta(rets, rets["BTC"]).iloc[-1]
    vol = rets.rolling(30).std(ddof=1).iloc[-1]
    resid = neutral.residual_vol(rets, rets["BTC"],
                                 neutral.rolling_beta(rets, rets["BTC"])).iloc[-1]
    z = pd.Series({"BTC": 0.0, "AAA": 2.0, "BBB": 1.0, "CCC": -1.0, "DDD": -2.0, "EEE": 0.5})
    w = neutral.build_book_row(z, vol, betas, resid, float(rets["BTC"].std(ddof=1)))
    book_beta = float((w * betas).sum())
    assert abs(book_beta) < 1e-9                          # hedged to zero ex-ante
    assert w.abs().sum() <= config.MN_GROSS_CAP + 1e-9    # gross cap
    non_hedge = w.drop(index=config.MN_MARKET_ASSET).abs()
    assert non_hedge.max() <= config.MN_NAME_CAP + 1e-9   # name cap (hedge exempt)
    assert (w != 0).sum() >= 4                            # a real long-short book


def test_build_alpha_book_is_trailing_only():
    close = make_close(n=420)
    universe = pd.DataFrame(True, index=close.index, columns=close.columns)
    signal = close.pct_change(30)  # simple momentum signal
    t0 = engine.evaluation_window(close.index, warmup_days=150)
    base = neutral.build_alpha_book(close, universe, signal, t0)
    perturbed = close.copy()
    d = close.index[350]
    perturbed.loc[d:, "CCC"] *= 4.0
    bumped = neutral.build_alpha_book(perturbed, universe, perturbed.pct_change(30), t0)
    before = close.index[close.index < d]
    assert base.loc[before].round(12).equals(bumped.loc[before].round(12))
    assert (base.loc[close.index < t0] == 0).all().all()
