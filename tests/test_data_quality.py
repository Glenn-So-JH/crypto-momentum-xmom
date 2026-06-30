"""
Unit tests for the Stage 1A data layer.

These run on hand-built synthetic data with NO network, so they are fast and deterministic.
The headline test is `test_universe_is_point_in_time`: it proves the liquidity screen cannot
see the future, which is the whole reason the screen exists.
"""

import numpy as np
import pandas as pd

from xmom import quality, universe


def make_frame(start="2024-01-01", n=10, close=100.0, volume=1_000.0):
    idx = pd.date_range(start, periods=n, freq="D")
    idx.name = "date"
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": volume},
        index=idx,
    )


# --- quality checks ------------------------------------------------------------

def test_duplicate_dates_removed():
    frame = make_frame(n=5)
    dupe = pd.concat([frame, frame.iloc[[2]]])  # date index 2 appears twice
    cleaned, report = quality.check_and_clean(dupe, "X")
    assert report["n_duplicate_dates"] == 1
    assert cleaned.index.is_unique


def test_calendar_gap_filled():
    frame = make_frame(n=6, close=100.0)
    gapped = frame.drop(frame.index[3])  # punch a one-day hole
    cleaned, report = quality.check_and_clean(gapped, "X")
    assert report["n_calendar_gaps_filled"] == 1
    # Continuous daily calendar restored, price forward-filled, filled volume == 0.
    assert (cleaned.index == pd.date_range(cleaned.index.min(), cleaned.index.max(), freq="D")).all()
    assert cleaned.loc[frame.index[3], "close"] == 100.0
    assert cleaned.loc[frame.index[3], "volume"] == 0.0


def test_zero_volume_day_reported():
    frame = make_frame(n=5)
    frame.iloc[2, frame.columns.get_loc("volume")] = 0.0
    _, report = quality.check_and_clean(frame, "X")
    assert report["n_zero_volume_days"] == 1


def test_outlier_flagged_not_deleted():
    frame = make_frame(n=6, close=100.0)
    frame.iloc[3, frame.columns.get_loc("close")] = 400.0  # +300% spike, well past threshold
    flagged = quality.flag_outliers(frame)
    assert len(flagged) >= 1
    cleaned, report = quality.check_and_clean(frame, "X")
    assert report["n_outliers_flagged"] >= 1
    # Flagged, but the value is still present (we never silently delete real-looking moves).
    assert cleaned.loc[frame.index[3], "close"] == 400.0


def test_stitch_renames_merges_history():
    matic = make_frame(start="2024-01-01", n=5, close=1.0)
    pol = make_frame(start="2024-01-06", n=5, close=2.0)
    out = quality.stitch_renames({"MATIC": matic, "POL": pol}, {"MATIC": "POL"})
    assert "MATIC" not in out
    assert "POL" in out
    assert len(out["POL"]) == 10
    assert out["POL"].index.is_monotonic_increasing
    assert out["POL"].index.is_unique


# --- universe screen -----------------------------------------------------------

def make_dvol(values_by_coin, start="2024-01-01", n=10):
    idx = pd.date_range(start, periods=n, freq="D")
    idx.name = "date"
    return pd.DataFrame({c: np.full(n, v, dtype="float64") for c, v in values_by_coin.items()}, index=idx)


def test_membership_threshold_and_min_periods():
    dvol = make_dvol({"A": 2_000.0, "B": 500.0}, n=10)
    members = universe.point_in_time_universe(dvol, window=3, min_usd=1_000)
    # B never clears the bar.
    assert not members["B"].any()
    # A needs a full 3-day window first: days 0,1 are False, day 2 onward True.
    assert not members["A"].iloc[0]
    assert not members["A"].iloc[1]
    assert members["A"].iloc[2:].all()


def test_stablecoins_excluded():
    dvol = make_dvol({"BTC": 5_000.0, "USDT": 1_000_000.0}, n=10)
    members = universe.point_in_time_universe(dvol, window=3, min_usd=1_000)
    assert not members["USDT"].any()  # huge volume, still forced out
    assert members["BTC"].iloc[3:].all()


def test_universe_is_point_in_time():
    """Membership at date t must not change when future data is hidden: no look-ahead."""
    rng = np.random.default_rng(0)
    dvol = make_dvol({"A": 1_000.0, "B": 1_000.0, "C": 1_000.0}, n=20)
    # Inject arbitrary future variation so a leak would actually change the answer.
    dvol = dvol * (1 + rng.uniform(-0.5, 1.5, size=dvol.shape))
    full = universe.point_in_time_universe(dvol, window=4, min_usd=1_000)
    for t in dvol.index:
        truncated = universe.point_in_time_universe(dvol.loc[:t], window=4, min_usd=1_000)
        assert (full.loc[t] == truncated.loc[t]).all(), f"look-ahead leak at {t}"


def test_build_panels_aligns_and_computes_dollar_volume():
    a = make_frame(start="2024-01-01", n=5, close=10.0, volume=100.0)   # dvol 1000
    b = make_frame(start="2024-01-03", n=5, close=2.0, volume=50.0)     # dvol 100, starts later
    close_panel, dvol_panel = universe.build_panels({"A": a, "B": b})
    assert list(close_panel.columns) == ["A", "B"]
    assert np.isnan(dvol_panel.loc["2024-01-01", "B"])  # B not listed yet
    assert dvol_panel.loc["2024-01-03", "A"] == 1000.0
    assert dvol_panel.loc["2024-01-03", "B"] == 100.0
