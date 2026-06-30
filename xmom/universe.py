"""
universe.py  -  the point-in-time liquidity screen that defeats survivorship bias.

The naive universe ("today's top coins, backfilled") secretly only contains winners that
survived to today, which makes momentum look far better than it was. Our defense: decide
membership *as of each date* using only trailing data. A coin is in the universe on date t
iff its trailing-window dollar volume cleared the bar using information available at t.

The screen is intentionally backward-looking by construction (pandas .rolling is trailing),
so a strategy reading this membership matrix cannot accidentally see the future. A unit test
in tests/ asserts exactly that point-in-time property.
"""

from __future__ import annotations

import pandas as pd

from . import config


def dollar_volume(frame: pd.DataFrame) -> pd.Series:
    """Daily dollar volume = close price * base-asset volume (a standard liquidity proxy)."""
    return (frame["close"].astype("float64") * frame["volume"].astype("float64")).rename("dollar_volume")


def build_panels(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Turn per-coin frames into two aligned wide panels: close price and dollar volume,
    indexed by the union of all dates (coins list later simply have NaN before they exist).
    """
    closes = {base: f["close"].astype("float64") for base, f in frames.items() if not f.empty}
    dvols = {base: dollar_volume(f) for base, f in frames.items() if not f.empty}
    close_panel = pd.DataFrame(closes).sort_index()
    dvol_panel = pd.DataFrame(dvols).sort_index()
    close_panel.index.name = dvol_panel.index.name = "date"
    return close_panel, dvol_panel


def point_in_time_universe(
    dvol_panel: pd.DataFrame,
    window: int = config.LIQUIDITY_WINDOW,
    min_usd: float = config.LIQUIDITY_MIN_USD,
    stablecoins: set[str] | None = None,
) -> pd.DataFrame:
    """
    Boolean membership matrix (dates x coins): True where a coin is tradable on that date.

    Rule: trailing `window`-day MEDIAN dollar volume >= `min_usd`, using only data up to and
    including the date (no look-ahead). A coin needs a full `window` of history before it can
    qualify (min_periods=window), so partial early data never sneaks a coin in. Stablecoins
    are forced out: they do not move, so momentum on them is meaningless.
    """
    stablecoins = config.STABLECOINS if stablecoins is None else stablecoins

    trailing_median = dvol_panel.rolling(window=window, min_periods=window).median()
    members = trailing_median >= min_usd          # NaN (too little history) compares False
    members = members.fillna(False).astype(bool)

    for col in members.columns:
        if col.upper() in stablecoins:
            members[col] = False
    return members


def current_members(members: pd.DataFrame) -> list[str]:
    """The coins that are in the universe on the most recent date."""
    if members.empty:
        return []
    last = members.iloc[-1]
    return sorted(last[last].index.tolist())


def membership_counts(members: pd.DataFrame) -> pd.Series:
    """How many coins were tradable on each date (a liquidity-breadth time series)."""
    return members.sum(axis=1).rename("n_members")
