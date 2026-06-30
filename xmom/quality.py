"""
quality.py  -  the unglamorous, essential part: try to break the data, then trust it.

Every function here is pure (DataFrame in, DataFrame/dict out) so the unit tests can feed
it hand-built pathological data and confirm the checks actually fire. The philosophy:
FLAG and REPORT generously, but only auto-fix what is unambiguous (sort, de-duplicate,
fill calendar gaps). We never silently delete a big-but-real price move.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import OHLCV_COLUMNS

PRICE_COLUMNS = ["open", "high", "low", "close"]


def daily_reindex(frame: pd.DataFrame) -> pd.DataFrame:
    """Reindex to a gap-free daily calendar between the first and last observed dates."""
    if frame.empty:
        return frame
    full = pd.date_range(frame.index.min(), frame.index.max(), freq="D")
    full.name = frame.index.name
    return frame.reindex(full)


def flag_outliers(frame: pd.DataFrame, threshold: float = config.OUTLIER_LOG_RETURN) -> list:
    """
    Return the dates whose close-to-close log return exceeds `threshold` in magnitude.
    These are suspect prints to eyeball, not automatic deletions: crypto genuinely moves.
    """
    if frame.empty or "close" not in frame:
        return []
    close = frame["close"].astype("float64")
    log_ret = np.log(close / close.shift(1))
    flagged = log_ret[log_ret.abs() > threshold]
    return list(flagged.index)


def check_and_clean(frame: pd.DataFrame, name: str) -> tuple[pd.DataFrame, dict]:
    """
    Run all data-quality checks on one coin and return (cleaned_frame, report).

    Auto-fixes (safe, reversible-in-spirit):
      - sort by date, drop duplicate dates (keep the last occurrence),
      - reindex to a gap-free daily calendar,
      - forward-fill prices across calendar gaps, set the filled days' volume to 0
        (we did not observe trading, so treat the gap as illiquid: a conservative choice
        that makes a gappy coin LESS likely to pass the liquidity screen, never more).

    Reports (never silently acted on):
      - duplicate dates removed, calendar gaps filled, native zero-volume days,
      - outlier (suspect-print) dates.
    """
    report = {
        "name": name,
        "n_rows_raw": int(len(frame)),
        "first_date": None,
        "last_date": None,
        "span_days": 0,
        "n_duplicate_dates": 0,
        "n_calendar_gaps_filled": 0,
        "n_zero_volume_days": 0,
        "n_outliers_flagged": 0,
        "outlier_dates": [],
        "coverage_pct": 0.0,
    }
    if frame.empty:
        return frame, report

    frame = frame.sort_index()

    # Duplicate dates (e.g. a paginated fetch overlapping itself or an exchange hiccup).
    dup_mask = frame.index.duplicated(keep="last")
    report["n_duplicate_dates"] = int(dup_mask.sum())
    frame = frame[~dup_mask]

    report["first_date"] = frame.index.min().date().isoformat()
    report["last_date"] = frame.index.max().date().isoformat()
    report["span_days"] = int((frame.index.max() - frame.index.min()).days) + 1

    # Native zero-volume days (genuine no-trade days, before any gap filling).
    if "volume" in frame:
        report["n_zero_volume_days"] = int((frame["volume"].fillna(0) == 0).sum())

    # Outliers: flag on the de-duplicated, observed data (before gap fill adds flat days).
    outliers = flag_outliers(frame)
    report["n_outliers_flagged"] = len(outliers)
    report["outlier_dates"] = [d.date().isoformat() for d in outliers]

    # Calendar gaps: reindex to daily, count and fill.
    observed = len(frame)
    cleaned = daily_reindex(frame)
    gaps = int(cleaned["close"].isna().sum())
    report["n_calendar_gaps_filled"] = gaps
    report["coverage_pct"] = round(100.0 * observed / len(cleaned), 2) if len(cleaned) else 0.0

    cleaned[PRICE_COLUMNS] = cleaned[PRICE_COLUMNS].ffill()
    cleaned["volume"] = cleaned["volume"].fillna(0.0)
    cleaned = cleaned[OHLCV_COLUMNS]

    return cleaned, report


def stitch_renames(frames: dict[str, pd.DataFrame], renames: dict[str, str] | None = None) -> dict[str, pd.DataFrame]:
    """
    Merge a rebranded coin's old-symbol history into its new canonical symbol.

    For OLD -> NEW: the post-rename (NEW) rows are authoritative; any earlier dates that
    exist only under OLD are prepended. The OLD key is removed from the result so the
    coin appears once, with one continuous history. Symbols not involved pass through.
    """
    renames = renames or config.TICKER_RENAMES
    out = dict(frames)
    for old, new in renames.items():
        if old not in out:
            continue
        old_frame = out.pop(old)
        if new in out and not out[new].empty:
            combined = pd.concat([old_frame, out[new]])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            out[new] = combined
        else:
            out[new] = old_frame.sort_index()
    return out
