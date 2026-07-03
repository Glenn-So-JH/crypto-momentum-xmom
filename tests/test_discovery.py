"""Discovery-dataset machinery tests: halt-splitting, regime labels, base filtering."""

import numpy as np
import pandas as pd

from xmom import config, quality, regimes
from discovery_fetch import filter_bases


def make_frame(start, n, close=100.0):
    idx = pd.date_range(start, periods=n, freq="D")
    idx.name = "date"
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1000.0},
        index=idx,
    )


# --- halt splitting ---------------------------------------------------------------

def test_split_on_halts_luna_style():
    # Old asset trades 400 days, 45-day halt, new asset resumes at a wild new price.
    old = make_frame("2021-01-01", 400, close=80.0)
    new = make_frame("2022-03-22", 200, close=6.0)
    combined = pd.concat([old, new])
    parts = quality.split_on_halts(combined, "LUNA", gap_days=30)
    assert set(parts) == {"LUNA", "LUNA__R1"}
    assert len(parts["LUNA"]) == 400
    assert len(parts["LUNA__R1"]) == 200
    # No row is shared: the fake cross-halt return cannot exist.
    assert parts["LUNA"].index.max() < parts["LUNA__R1"].index.min()


def test_split_keeps_single_segment_when_no_halt():
    frame = make_frame("2021-01-01", 300)
    parts = quality.split_on_halts(frame, "BTC", gap_days=30)
    assert set(parts) == {"BTC"}
    assert len(parts["BTC"]) == 300


def test_split_tolerates_short_gaps():
    a = make_frame("2021-01-01", 100)
    b = make_frame("2021-04-21", 100)  # 10-day hole: same asset, not a halt
    parts = quality.split_on_halts(pd.concat([a, b]), "X", gap_days=30)
    assert set(parts) == {"X"}


def test_split_drops_tiny_segments():
    a = make_frame("2021-01-01", 300)
    stub = make_frame("2022-06-01", 10)  # relist stub too short to ever screen in
    parts = quality.split_on_halts(pd.concat([a, stub]), "X", gap_days=30)
    assert set(parts) == {"X"}
    assert len(parts["X"]) == 300


def test_split_at_configured_corporate_action_date():
    # Continuous data, no gap: an old token flatlines, then the symbol is reused at a
    # wildly different price (the LUNA relist / redenomination shape).
    old = make_frame("2021-01-01", 400, close=0.0001)
    new = make_frame("2022-02-05", 200, close=9.0)  # next calendar day, no hole
    combined = pd.concat([old, new])
    parts = quality.split_on_halts(combined, "LUNA", gap_days=30, split_dates=["2022-02-05"])
    assert set(parts) == {"LUNA", "LUNA__R1"}
    assert parts["LUNA"].index.max() == pd.Timestamp("2022-02-04")
    assert parts["LUNA__R1"].index.min() == pd.Timestamp("2022-02-05")
    # Without the configured date, no split happens (the seam is invisible to gaps).
    assert set(quality.split_on_halts(combined, "LUNA", gap_days=30)) == {"LUNA"}


def test_bare_leveraged_tokens_excluded():
    kept, excluded = filter_bases({b: f"{b}USDT" for b in ["BTC", "BULL", "BEAR"]})
    assert set(excluded["leveraged_token"]) == {"BULL", "BEAR"}
    assert "BTC" in kept


# --- regime labels ----------------------------------------------------------------

def test_trend_regime_labels_bull_and_bear():
    n = 500
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    up_then_down = np.concatenate([100 * 1.005 ** np.arange(350),
                                   100 * 1.005 ** 350 * 0.99 ** np.arange(n - 350)])
    close = pd.DataFrame({"BTC": up_then_down}, index=idx)
    labels = regimes.trend_regime(close)
    assert labels.iloc[:config.REGIME_TREND_SMA - 1].isna().all()  # warmup unlabeled
    assert (labels.iloc[210:340] == "bull").all()
    assert (labels.iloc[-50:] == "bear").all()


def test_era_labels_cover_panel_contiguously():
    idx = pd.date_range("2018-01-01", periods=2500, freq="D")
    labels = regimes.era_labels(idx)
    assert not labels.isna().any()
    # Named boundaries land where config says.
    assert labels.loc["2020-03-15"] == "2020 covid crash"
    assert labels.loc["2022-06-18"] == "2022 bear"


def test_per_regime_metrics_split_correctly():
    idx = pd.date_range("2021-01-01", periods=200, freq="D")
    labels = pd.Series(["up"] * 100 + ["down"] * 100, index=idx)
    r = pd.Series([0.01] * 100 + [-0.01] * 100, index=idx)
    table = regimes.per_regime_metrics(r, labels)
    assert table.loc["up", "sharpe"] > 0 or np.isnan(table.loc["up", "sharpe"])
    assert table.loc["up", "total_return"] > 0
    assert table.loc["down", "total_return"] < 0
    assert table.loc["up", "n_days"] == 100


# --- base filtering ---------------------------------------------------------------

def test_filter_bases_leveraged_and_stables():
    bases = {b: f"{b}USDT" for b in
             ["BTC", "ETH", "EOS", "BTCUP", "BTCDOWN", "EOSBULL", "JUP", "SYRUP", "USDC", "EUR", "PAXG"]}
    kept, excluded = filter_bases(bases)
    assert set(excluded["leveraged_token"]) == {"BTCUP", "BTCDOWN", "EOSBULL"}
    assert set(excluded["stablecoin_fiat_commodity"]) == {"USDC", "EUR", "PAXG"}
    assert "JUP" in kept and "SYRUP" in kept  # end in UP but stems J / SYR do not exist
    assert "BTC" in kept and "ETH" in kept
