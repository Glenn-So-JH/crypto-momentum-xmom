"""Phase 2 machinery tests: drift engine band logic, weight cap, gate, vol target."""

import numpy as np
import pandas as pd
import pytest

from xmom import engine, phase2


def flat_close(n=30, cols=("A", "B"), start="2023-01-02"):
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(100.0, index=idx, columns=list(cols))


def test_drift_band_suppresses_cosmetic_trades():
    # Prices drift apart mildly; targets identical each Monday. With a wide band,
    # only the inception trade happens; with band=0 every Monday re-trues.
    n = 60
    idx = pd.date_range("2023-01-02", periods=n, freq="D")
    close = pd.DataFrame(
        {"A": 100.0 * (1.002 ** np.arange(n)), "B": 100.0 * (0.999 ** np.arange(n))},
        index=idx,
    )
    reb = engine.rebalance_days(idx)
    targets = pd.DataFrame(0.5, index=reb, columns=["A", "B"])
    banded = engine.run_drift_backtest(close, targets, None, band=0.30, cost_per_side=0.0)
    tight = engine.run_drift_backtest(close, targets, None, band=0.0, cost_per_side=0.0)
    assert banded.turnover.sum() == 0.0            # inception excluded, drift small: no trades
    assert tight.turnover.sum() > 0.0              # zero band re-trues weekly
    # Weekly drift at ~0.3%/day never exceeds 30% of a 0.5 target.
    assert (banded.weights.iloc[-1] - 0.5).abs().max() > 0.0  # weights actually drifted


def test_drift_flip_always_trades():
    close = flat_close(n=22)
    reb = engine.rebalance_days(close.index)
    targets = pd.DataFrame(0.0, index=reb, columns=["A", "B"])
    targets.loc[reb[0], "A"] = 0.5
    targets.loc[reb[1], "A"] = 0.0   # exit A (flip)
    targets.loc[reb[1], "B"] = 0.5   # enter B (flip)
    result = engine.run_drift_backtest(close, targets, None, band=0.99, cost_per_side=0.01)
    d = reb[1]
    # Despite the huge band, both flips trade: notional = 0.5 out + 0.5 in.
    assert result.turnover.loc[d] == pytest.approx(0.5)
    assert result.costs.loc[d] == pytest.approx(1.0 * 0.01)
    assert result.weights.loc[d, "A"] == 0.0
    assert result.weights.loc[d, "B"] == 0.5


def test_drift_universe_exit_forces_sale_midweek():
    close = flat_close(n=22)
    reb = engine.rebalance_days(close.index)
    targets = pd.DataFrame(0.0, index=reb, columns=["A", "B"])
    targets.loc[reb[0]] = [0.5, 0.5]
    universe = pd.DataFrame(True, index=close.index, columns=["A", "B"])
    kick = close.index[3]  # a Thursday
    universe.loc[kick:, "B"] = False
    result = engine.run_drift_backtest(close, targets, universe, band=0.2, cost_per_side=0.0)
    assert result.weights.loc[kick, "B"] == 0.0
    assert result.weights.loc[kick, "A"] == pytest.approx(0.5)  # survivor untouched
    assert result.turnover.loc[kick] == pytest.approx(0.25)     # one-sided 0.5*|0.5|


def test_drift_matches_vectorized_when_band_zero_flat_prices():
    close = flat_close(n=30, cols=("A", "B", "C"))
    reb = engine.rebalance_days(close.index)
    rng = np.random.default_rng(3)
    targets = pd.DataFrame(rng.dirichlet([1, 1, 1], len(reb)) * 0.9, index=reb, columns=close.columns)
    drift = engine.run_drift_backtest(close, targets, None, band=0.0, cost_per_side=0.004)
    daily = engine.expand_rebalance_weights(targets, close.index[close.index >= reb[0]], None)
    vect = engine.run_backtest(close, daily, cost_per_side=0.004)
    # Flat prices: no drift, so band-0 drift engine and vectorized engine agree exactly.
    assert np.allclose(drift.turnover, vect.turnover.reindex(drift.turnover.index), atol=1e-12)
    assert np.allclose(drift.equity, vect.equity.reindex(drift.equity.index), rtol=1e-12)


def test_cap_weights_redistributes_and_caps():
    w = pd.Series({"A": 0.60, "B": 0.25, "C": 0.15})
    capped = phase2.cap_weights(w, cap=0.25)
    assert capped.max() <= 0.25 + 1e-9
    assert capped.sum() == pytest.approx(0.75)  # 3 names at most 0.25 each: rest to cash
    w2 = pd.Series({"A": 0.30, "B": 0.28, "C": 0.22, "D": 0.20})
    capped2 = phase2.cap_weights(w2, cap=0.25)
    assert capped2.max() <= 0.25 + 1e-9
    # Four names at a 25% cap have exactly 100% capacity: iteration fills them all.
    assert capped2.sum() == pytest.approx(1.0)
    assert np.allclose(capped2, 0.25)


def test_gate_zeroes_book_in_downtrend():
    n = 320
    idx = pd.date_range("2022-01-03", periods=n, freq="D")
    # BTC below its SMA (steady downtrend), alt rallying: gate must still force cash.
    close = pd.DataFrame(
        {"BTC": 100.0 * (0.998 ** np.arange(n)), "ALT": 10.0 * (1.004 ** np.arange(n))},
        index=idx,
    )
    universe = pd.DataFrame(True, index=idx, columns=close.columns)
    t0 = engine.evaluation_window(idx, warmup_days=250)
    targets = phase2.build_targets(close, universe, t0, lookback=21, mode="tsmom")
    assert (targets.sum(axis=1) == 0.0).all()


def test_vol_target_scales_down_hot_books():
    n = 400
    rng = np.random.default_rng(9)
    idx = pd.date_range("2022-01-03", periods=n, freq="D")
    # A violent uptrend keeps the gate on and momentum positive, with ~130% ann vol.
    wild = 100.0 * np.exp(np.cumsum(rng.normal(0.004, 0.07, n)))
    calm_up = 100.0 * (1.002 ** np.arange(n))
    close = pd.DataFrame({"BTC": calm_up, "WILD": wild}, index=idx)
    universe = pd.DataFrame(True, index=idx, columns=close.columns)
    t0 = engine.evaluation_window(idx, warmup_days=250)
    targets = phase2.build_targets(close, universe, t0, lookback=21, mode="tsmom",
                                   vol_target=0.30)
    exposure = targets.sum(axis=1)
    held = exposure[exposure > 0]
    assert len(held) > 0
    # De-risk only: never levered, and the hot book is scaled well below fully invested.
    assert exposure.max() <= 1.0 + 1e-9
    assert held.min() < 0.75


def test_challenger_holds_at_most_top_n():
    n = 400
    rng = np.random.default_rng(4)
    idx = pd.date_range("2022-01-03", periods=n, freq="D")
    cols = [f"C{i}" for i in range(8)] + ["BTC"]
    close = pd.DataFrame(
        {c: 50.0 * np.exp(np.cumsum(rng.normal(0.002, 0.03, n))) for c in cols}, index=idx
    )
    universe = pd.DataFrame(True, index=idx, columns=close.columns)
    t0 = engine.evaluation_window(idx, warmup_days=250)
    targets = phase2.build_targets(close, universe, t0, lookback=21, mode="xsmom", top_n=3)
    n_held = (targets > 1e-12).sum(axis=1)
    assert n_held.max() <= 3
