"""
phase1_build_universe.py  -  Stage 1A, step 2: clean the raw data and build the universe.

Pipeline:
  1. Load every per-coin Parquet from data/raw.
  2. Stitch ticker renames (e.g. MATIC -> POL) into one continuous history.
  3. Run data-quality checks on each coin (gaps, duplicates, zero-volume, outliers) and
     produce cleaned daily series.
  4. Build aligned close-price and dollar-volume panels.
  5. Apply the point-in-time liquidity screen to get a per-date membership matrix.
  6. Write processed Parquet (close, dollar_volume, universe) and a data-quality report,
     then print a summary.

Run it (after phase1_fetch_data.py):
    python phase1_build_universe.py

Inputs (data/raw) and outputs (data/processed) are both gitignored.
"""

from __future__ import annotations

import pandas as pd

from xmom import config, data, quality, universe


def _load_raw_frames() -> dict[str, pd.DataFrame]:
    frames = {}
    for path in sorted(config.DATA_RAW.glob("*.parquet")):
        base = path.stem
        frames[base] = data.load_raw(base)
    return frames


def _write_quality_report(reports: list[dict], members: pd.DataFrame) -> str:
    counts = universe.membership_counts(members)
    lines = ["# Stage 1A data-quality report", ""]
    lines.append(f"- Coins after rename-stitching: **{len(reports)}**")
    if not members.empty:
        lines.append(f"- Date range: **{members.index.min().date()} -> {members.index.max().date()}**")
        lines.append(
            f"- Universe size over time (members/day): min {int(counts.min())}, "
            f"median {int(counts.median())}, max {int(counts.max())}"
        )
        lines.append(f"- Current members ({len(universe.current_members(members))}): "
                     f"{', '.join(universe.current_members(members))}")
    lines += ["", "## Per-coin quality", ""]
    lines.append("| coin | candles | first | last | dup dates | gaps filled | zero-vol days | outliers |")
    lines.append("|---|---:|---|---|---:|---:|---:|---:|")
    for r in sorted(reports, key=lambda x: x["name"]):
        lines.append(
            f"| {r['name']} | {r['n_rows_raw']} | {r['first_date']} | {r['last_date']} | "
            f"{r['n_duplicate_dates']} | {r['n_calendar_gaps_filled']} | "
            f"{r['n_zero_volume_days']} | {r['n_outliers_flagged']} |"
        )
    # List any flagged outliers explicitly so they can be eyeballed.
    flagged = [(r["name"], r["outlier_dates"]) for r in reports if r["outlier_dates"]]
    if flagged:
        lines += ["", "## Suspect prints flagged (review, not auto-removed)", ""]
        for name, dates in sorted(flagged):
            lines.append(f"- **{name}**: {', '.join(dates)}")
    return "\n".join(lines) + "\n"


def build():
    frames = _load_raw_frames()
    if not frames:
        print("No raw data found in data/raw. Run phase1_fetch_data.py first.")
        return

    frames = quality.stitch_renames(frames)

    cleaned_frames = {}
    reports = []
    for base, frame in frames.items():
        cleaned, report = quality.check_and_clean(frame, base)
        cleaned_frames[base] = cleaned
        reports.append(report)

    close_panel, dvol_panel = universe.build_panels(cleaned_frames)
    members = universe.point_in_time_universe(dvol_panel)

    # Persist processed artifacts (gitignored).
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    close_panel.to_parquet(config.DATA_PROCESSED / "close.parquet")
    dvol_panel.to_parquet(config.DATA_PROCESSED / "dollar_volume.parquet")
    members.to_parquet(config.DATA_PROCESSED / "universe.parquet")

    report_md = _write_quality_report(reports, members)
    (config.DATA_PROCESSED / "DATA_QUALITY.md").write_text(report_md)

    # Console summary.
    counts = universe.membership_counts(members)
    print(f"Cleaned {len(cleaned_frames)} coins (after rename-stitching).")
    print(f"Date range: {close_panel.index.min().date()} -> {close_panel.index.max().date()} "
          f"({len(close_panel)} daily rows).")
    print(f"Universe size per day: min {int(counts.min())}, median {int(counts.median())}, "
          f"max {int(counts.max())}.")
    print(f"Current members ({len(universe.current_members(members))}): "
          f"{', '.join(universe.current_members(members))}")

    total_dups = sum(r["n_duplicate_dates"] for r in reports)
    total_gaps = sum(r["n_calendar_gaps_filled"] for r in reports)
    total_outliers = sum(r["n_outliers_flagged"] for r in reports)
    print(f"\nQuality totals: {total_dups} duplicate dates, {total_gaps} calendar gaps filled, "
          f"{total_outliers} suspect prints flagged.")
    print(f"Full report written to {config.DATA_PROCESSED / 'DATA_QUALITY.md'}")
    return reports, members


if __name__ == "__main__":
    build()
