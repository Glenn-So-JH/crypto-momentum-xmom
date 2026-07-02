"""
Engine unit tests: the five gate tests from MASTER_BRIEF Stage B, plus contract edges.

These are the tests that let us trust every later result. Synthetic data only.
"""

import numpy as np
import pandas as pd
import pytest

from xmom import engine


def make_close(n=400, seed=7, cols=("BTC", "ETH", "SOL")):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="D")  # starts on a Monday
    idx.name = "date"
    data = {}
    for j, c in enumerate(cols):
        rets = rng.normal(0.0005, 0.03, n)
        data[c] = 100.0 * (j + 1) * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=idx)


def weights_like(close, value=0.0):
    return pd.DataFrame(value, index=close.index, columns=close.columns)


# --- GATE TEST 1: buy-and-hold reproduces the asset exactly ----------------------

def test_buy_and_hold_btc_equals_btc_path():
    close = make_close()
    w = weights_like(close)
    w["BTC"] = 1.0
    result = engine.run_backtest(close, w)
    expected = close["BTC"] / close["BTC"].iloc[0]
    # equity(t) compounds returns from the second day; day one has no prior weight.
    assert np.allclose(result.equity.iloc[1:], expected.iloc[1:], rtol=1e-10)
    # Never-trading portfolio: zero turnover everywhere (inception excluded).
    assert result.turnover.abs().max() == 0.0


# --- GATE TEST 2: look-ahead guard ------------------------------------------------

def test_future_price_cannot_change_past_returns():
    close = make_close()
    w = weights_like(close, 1.0 / 3.0)
    base = engine.run_backtest(close, w)

    perturbed = close.copy()
    d = close.index[300]
    perturbed.loc[d:, "ETH"] *= 3.0  # violent future move
    bumped = engine.run_backtest(perturbed, w)

    # Everything strictly before the perturbation date is bit-identical.
    before = close.index[close.index < d]
    assert (base.net_returns.loc[before] == bumped.net_returns.loc[before]).all()
    assert (base.equity.loc[before] == bumped.equity.loc[before]).all()


def test_cheating_strategy_gains_nothing_from_peeking():
    """A strategy that 'knows' tomorrow's winner must still earn it one day late."""
    close = make_close(n=200)
    rets = close.pct_change()
    # Cheat: on day t, put 100% in the asset with the best return from t to t+1.
    tomorrow = rets.shift(-1).iloc[1:-1]  # first row: no prior return; last row: no tomorrow
    winner = tomorrow.idxmax(axis=1)
    w = weights_like(close)
    for t, c in winner.items():
        w.loc[t, c] = 1.0
    result = engine.run_backtest(close, w)
    # If the engine failed to lag, the portfolio would earn the daily MAX return.
    max_possible = rets.max(axis=1).iloc[1:]
    realized = result.gross_returns.iloc[1:]
    assert not np.allclose(realized, max_possible)  # peeking must NOT pay
    # And the realized return must be exactly the lagged application of the weights.
    manual = (w.shift(1).fillna(0.0) * rets).sum(axis=1).iloc[1:]
    assert np.allclose(realized, manual, rtol=1e-12)


# --- GATE TEST 3: no-leverage / long-only guard -----------------------------------

def test_leverage_rejected():
    close = make_close(n=50)
    w = weights_like(close, 0.5)  # sums to 1.5
    with pytest.raises(ValueError, match="sum > 1"):
        engine.run_backtest(close, w)


def test_negative_weights_rejected():
    close = make_close(n=50)
    w = weights_like(close)
    w.iloc[10, 0] = -0.1
    with pytest.raises(ValueError, match="Negative"):
        engine.run_backtest(close, w)


def test_ghost_position_rejected():
    close = make_close(n=50)
    close.iloc[:10, close.columns.get_loc("SOL")] = np.nan  # SOL not listed yet
    w = weights_like(close)
    w["SOL"] = 0.5  # positive weight while price is NaN
    with pytest.raises(ValueError, match="ghost"):
        engine.run_backtest(close, w)


# --- GATE TEST 4: cash earns exactly zero -----------------------------------------

def test_all_cash_is_flat():
    close = make_close(n=100)
    w = weights_like(close, 0.0)
    result = engine.run_backtest(close, w)
    assert (result.net_returns == 0.0).all()
    assert (result.equity == 1.0).all()


def test_partial_cash_dilutes_returns():
    close = make_close(n=100)
    w_full = weights_like(close)
    w_full["BTC"] = 1.0
    w_half = weights_like(close)
    w_half["BTC"] = 0.5
    r_full = engine.run_backtest(close, w_full).gross_returns
    r_half = engine.run_backtest(close, w_half).gross_returns
    assert np.allclose(r_half.iloc[1:], 0.5 * r_full.iloc[1:], rtol=1e-12)


# --- Cost hook --------------------------------------------------------------------

def test_costs_charge_traded_notional():
    close = make_close(n=10)
    close[:] = 100.0  # flat prices isolate the cost effect
    w = weights_like(close)
    w["BTC"] = 1.0
    w.loc[close.index[5]:, "BTC"] = 0.0  # sell the whole book once
    w.loc[close.index[5]:, "ETH"] = 1.0  # and buy another (traded notional = 2.0)
    result = engine.run_backtest(close, w, cost_per_side=0.005)
    d = close.index[5]
    assert result.turnover.loc[d] == pytest.approx(1.0)   # one-sided
    assert result.costs.loc[d] == pytest.approx(2.0 * 1.0 * 0.005)
    assert result.net_returns.loc[d] == pytest.approx(-0.01)
    # No other day is charged.
    assert result.costs.drop(d).abs().max() == 0.0


def test_zero_cost_hook_is_identity():
    close = make_close()
    w = weights_like(close, 1.0 / 3.0)
    r = engine.run_backtest(close, w, cost_per_side=0.0)
    assert np.allclose(r.gross_returns, r.net_returns, rtol=1e-15)


# --- Rebalance helpers --------------------------------------------------------------

def test_evaluation_window_is_first_monday_after_warmup():
    idx = pd.date_range("2023-01-02", periods=400, freq="D")
    start = engine.evaluation_window(idx, warmup_days=200)
    assert start.weekday() == 0
    assert start >= idx[0] + pd.Timedelta(days=200)
    assert (start - (idx[0] + pd.Timedelta(days=200))).days < 7


def test_expand_rebalance_weights_holds_and_exits():
    idx = pd.date_range("2023-01-02", periods=15, freq="D")  # Mon 02, Mon 09, Mon 16
    cols = ["A", "B"]
    reb_days = idx[idx.weekday == 0]
    reb_w = pd.DataFrame(0.0, index=reb_days, columns=cols)
    reb_w.loc[reb_days[0]] = [0.6, 0.4]
    reb_w.loc[reb_days[1]] = [0.0, 0.5]
    universe = pd.DataFrame(True, index=idx, columns=cols)
    universe.loc[idx[3]:, "B"] = False  # B drops out mid-week after the first Monday
    universe.loc[idx[7]:, "B"] = True   # and returns before the second Monday

    daily = engine.expand_rebalance_weights(reb_w, idx, universe)
    assert daily.loc[idx[1], "A"] == 0.6            # held constant between Mondays
    assert daily.loc[idx[3], "B"] == 0.0            # forced out mid-week
    assert daily.loc[idx[4], "A"] == 0.6            # survivor NOT renormalized
    assert daily.loc[idx[8], "B"] == 0.5            # new Monday target applies (idx[7] is Mon 09)
