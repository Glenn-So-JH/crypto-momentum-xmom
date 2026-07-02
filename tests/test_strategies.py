"""
Strategy unit tests: the per-strategy engine-test properties from docs/03 (f) sections,
plus the pipeline-level look-ahead probe. Synthetic data only.
"""

import numpy as np
import pandas as pd

from xmom import engine, strategies


def make_panel(n=320, n_assets=8, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="D")  # Monday start
    idx.name = "date"
    cols = [f"C{i:02d}" for i in range(n_assets)]
    close = pd.DataFrame(
        {c: 50.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.04, n))) for c in cols},
        index=idx,
    )
    universe = pd.DataFrame(True, index=idx, columns=cols)
    return close, universe


T0_WARMUP = 100  # tests use a shorter warmup than production's 200 to keep panels small


def get_t0(close):
    return engine.evaluation_window(close.index, warmup_days=T0_WARMUP)


def test_s2_weights_sum_to_one_and_respect_universe():
    close, universe = make_panel()
    universe.iloc[:, -1] = False  # last asset never in universe
    t0 = get_t0(close)
    w = strategies.s2_equal_weight(close, universe, t0)
    reb = engine.rebalance_days(close.index, start=t0)
    sums = w.loc[reb].sum(axis=1)
    assert np.allclose(sums, 1.0)
    # (f)(ii): positive weight implies in-universe, on every date.
    held = w > 1e-12
    assert not (held & ~universe).any().any()
    # (f)(iii): weight changes only happen on Mondays (between them targets are held).
    active = w.loc[w.index >= t0]
    changes = active.diff().abs().sum(axis=1).iloc[1:]
    non_monday_changes = changes[changes.index.weekday != 0]
    assert non_monday_changes.max() < 1e-12  # universe is static here, so no mid-week exits


def test_s3_flat_when_out_and_lag_matters():
    close, universe = make_panel(n_assets=2)
    close.columns = ["BTC", "ETH"]
    t0 = get_t0(close)
    w = strategies.s3_ma_filter(close, t0, asset="BTC", n=50)
    result = engine.run_backtest(close, w)
    # (f): equity exactly flat on days where the prior target was cash.
    exposure = w.shift(1).fillna(0.0).sum(axis=1)
    flat_days = result.net_returns[(exposure == 0.0) & (result.net_returns.index >= t0)]
    assert (flat_days == 0.0).all()
    # Natural look-ahead probe: shifting the signal one day earlier changes the curve.
    w_early = w.shift(-1).fillna(0.0)
    r_early = engine.run_backtest(close, w_early)
    assert not np.allclose(result.equity.iloc[-50:], r_early.equity.iloc[-50:])


def test_s4_all_cash_when_everything_negative():
    n = 300
    idx = pd.date_range("2023-01-02", periods=n, freq="D")
    # Two assets in a relentless downtrend: TSMOM must hold cash the whole window.
    close = pd.DataFrame(
        {"A": 100.0 * 0.995 ** np.arange(n), "B": 80.0 * 0.99 ** np.arange(n)},
        index=idx,
    )
    universe = pd.DataFrame(True, index=idx, columns=close.columns)
    t0 = get_t0(close)
    w = strategies.s4_tsmom(close, universe, t0, lookback=30)
    result = engine.run_backtest(close, w)
    active = result.net_returns[result.net_returns.index >= t0]
    assert (w.loc[w.index >= t0].sum(axis=1) == 0.0).all()
    assert (active == 0.0).all()  # no NaNs, exactly flat through an all-cash stretch
    assert result.equity.iloc[-1] == 1.0


def test_s4_signals_are_per_asset_independent():
    close, universe = make_panel()
    t0 = get_t0(close)
    w_full = strategies.s4_tsmom(close, universe, t0, lookback=30)
    # Remove one asset from the universe: other assets' hold/drop must not change.
    universe2 = universe.copy()
    universe2["C03"] = False
    w_less = strategies.s4_tsmom(close, universe2, t0, lookback=30)
    others = [c for c in close.columns if c != "C03"]
    held_full = (w_full[others] > 1e-12)
    held_less = (w_less[others] > 1e-12)
    assert held_full.equals(held_less)  # membership identical (weights differ via 1/h)


def test_s5_s6_disjoint_selections():
    close, universe = make_panel(n_assets=10)
    t0 = get_t0(close)
    w5 = strategies.s5_xsmom(close, universe, t0, lookback=7, skip=0, top_n=3)
    w6 = strategies.s6_reversal(close, universe, t0, lookback=7, bottom_n=3)
    reb = engine.rebalance_days(close.index, start=t0)
    for t in reb:
        top = set(w5.loc[t][w5.loc[t] > 1e-12].index)
        bottom = set(w6.loc[t][w6.loc[t] > 1e-12].index)
        if len(top) == 3 and len(bottom) == 3:  # n_eligible >= 6 here always
            assert not (top & bottom), f"overlap on {t}"


def test_s5_quantile_adapts_to_breadth():
    close, universe = make_panel(n_assets=10)
    t0 = get_t0(close)
    # With 10 eligible, ceil(0.2 * 10) = 2 held names.
    w = strategies.s5_xsmom(close, universe, t0, lookback=30, skip=0, top_n=None, quantile=0.20)
    reb = engine.rebalance_days(close.index, start=t0)
    n_held = (w.loc[reb] > 1e-12).sum(axis=1)
    assert (n_held == 2).all()


def test_s5_tie_break_is_alphabetical():
    n = 300
    idx = pd.date_range("2023-01-02", periods=n, freq="D")
    # Three identical price paths: momentum ties everywhere; top-2 must pick A then B.
    path = 100.0 * np.exp(np.cumsum(np.full(n, 0.001)))
    close = pd.DataFrame({"B": path.copy(), "A": path.copy(), "C": path.copy()}, index=idx)
    universe = pd.DataFrame(True, index=idx, columns=close.columns)
    t0 = get_t0(close)
    w = strategies.s5_xsmom(close, universe, t0, lookback=30, skip=0, top_n=2)
    reb = engine.rebalance_days(close.index, start=t0)
    held = w.loc[reb] > 1e-12
    assert held["A"].all() and held["B"].all() and not held["C"].any()


def test_pipeline_no_look_ahead_probe():
    """Perturbing a future price must not change any weight before that date."""
    close, universe = make_panel()
    t0 = get_t0(close)
    w_base = strategies.s5_xsmom(close, universe, t0, lookback=30, skip=0, top_n=3)
    perturbed = close.copy()
    d = close.index[250]
    perturbed.loc[d:, "C05"] *= 5.0
    w_bump = strategies.s5_xsmom(perturbed, universe, t0, lookback=30, skip=0, top_n=3)
    before = close.index[close.index < d]
    assert w_base.loc[before].equals(w_bump.loc[before])
