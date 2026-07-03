"""
discovery_build.py  -  Handoff #7 WS1: clean the discovery data and build its panels.

Pipeline (discovery flavor of phase1_build_universe.py, kept separate on purpose):
  1. Load per-coin Parquet from data/raw/discovery.
  2. Stitch documented renames (MATIC->POL, FTM->S).
  3. Split coins at trading halts (> DISCOVERY_SEGMENT_GAP_DAYS holes): a symbol
     reused across a delist/relist becomes separate assets, so no fake return can
     cross a halt (Binance's LUNAUSDT is the canonical case).
  4. Quality-check and clean each segment.
  5. Build close / dollar-volume panels, run the point-in-time screen at the
     GENEROUS discovery bar ($5M/day trailing-30d median; broad cross-section).
  6. Label regimes (BTC 200d trend + named eras) and save them alongside the panels.
  7. Write panels + append the discovery section to research/stage_a_data_report.md.

Run it (after discovery_fetch.py):
    python discovery_build.py
"""

from __future__ import annotations

import json

import pandas as pd

from xmom import config, quality, regimes, universe


def load_and_segment() -> tuple[dict[str, pd.DataFrame], dict]:
    non_signal = config.STABLECOINS | config.FIAT | config.COMMODITY_TOKENS
    frames = {}
    for path in sorted(config.DATA_RAW_DISCOVERY.glob("*.parquet")):
        # Build-time guard: skip anything the fetch filter now excludes (e.g. bare
        # BULL/BEAR leveraged tokens fetched before the filter was tightened).
        if path.stem in config.LEVERAGED_SUFFIXES or path.stem.upper() in non_signal:
            continue
        frames[path.stem] = pd.read_parquet(path)
    frames = quality.stitch_renames(frames)

    segmented: dict[str, pd.DataFrame] = {}
    split_info = {}
    for base, frame in frames.items():
        parts = quality.split_on_halts(
            frame, base, config.DISCOVERY_SEGMENT_GAP_DAYS,
            split_dates=config.DISCOVERY_SYMBOL_SPLITS.get(base),
        )
        if len(parts) > 1:
            split_info[base] = sorted(parts)
        segmented.update(parts)
    return segmented, split_info


def build():
    segmented, split_info = load_and_segment()
    if not segmented:
        print("No discovery data found. Run discovery_fetch.py first.")
        return

    cleaned, reports = {}, []
    for name, frame in segmented.items():
        c, r = quality.check_and_clean(frame, name)
        cleaned[name] = c
        reports.append(r)

    close_panel, dvol_panel = universe.build_panels(cleaned)
    members = universe.point_in_time_universe(
        dvol_panel,
        window=config.DISCOVERY_LIQUIDITY_WINDOW,
        min_usd=config.DISCOVERY_LIQUIDITY_MIN_USD,
    )
    regime_frame = pd.DataFrame({
        "trend": regimes.trend_regime(close_panel),
        "era": regimes.era_labels(close_panel.index),
    })

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    close_panel.to_parquet(config.DATA_PROCESSED / "discovery_close.parquet")
    dvol_panel.to_parquet(config.DATA_PROCESSED / "discovery_dollar_volume.parquet")
    members.to_parquet(config.DATA_PROCESSED / "discovery_universe.parquet")
    regime_frame.to_parquet(config.DATA_PROCESSED / "discovery_regimes.parquet")

    counts = universe.membership_counts(members)
    mondays = close_panel.index[close_panel.index.weekday == 0]
    vault_mask = close_panel.index >= pd.Timestamp(config.OOS_VAULT_START)
    ever = members.any()
    dead_examples = sorted(n for n in ("LUNA", "FTT", "BTT", "ANC") if n in close_panel.columns)

    _append_report_section(reports, members, close_panel, split_info, counts, mondays, vault_mask)

    print(f"Assets after rename-stitching and halt-splitting: {len(cleaned)} "
          f"({len(split_info)} coins split into segments).")
    print(f"Panel: {close_panel.index.min().date()} -> {close_panel.index.max().date()} "
          f"({len(close_panel)} days, {len(mondays)} weekly observations, "
          f"{int(vault_mask.sum())} days locked in the OOS vault).")
    print(f"Universe (>= ${config.DISCOVERY_LIQUIDITY_MIN_USD/1e6:.0f}M/day): "
          f"ever-members {int(ever.sum())}, breadth median {int(counts.median())}, "
          f"max {int(counts.max())}.")
    print(f"Dead coins present (survivorship-conscious): {', '.join(dead_examples)}")
    print("Panels written: discovery_close / discovery_dollar_volume / discovery_universe / "
          "discovery_regimes .parquet")
    return cleaned, members


def _append_report_section(reports, members, close_panel, split_info, counts, mondays, vault_mask):
    ever = members.any()
    by_year = counts.groupby(counts.index.year).median().astype(int)
    lines = ["", "---", "", "# Discovery dataset (Handoff #7 WS1): single-source, broad, regime-ready", ""]
    lines.append(f"Appended {pd.Timestamp.now(tz='UTC').date()}. This is a SECOND dataset for signal "
                 "discovery; the Kraken execution dataset above is unchanged. Kraken tradability "
                 "(thin universe, venue costs, splice constraints) is deliberately DEFERRED to a "
                 "later gate applied only to signals that survive discovery.")
    lines.append("")
    lines.append("- **Source:** Binance daily klines from the public data.binance.vision bucket, one "
                 "source across each coin's full history. No splice, no reconciliation gate, no "
                 "volume-rescaling proxy: seam-free by construction.")
    lines.append("- **Survivorship-conscious:** the bucket retains delisted pairs, so dead coins are "
                 "in the panel and can enter the point-in-time universe while they were liquid "
                 f"(e.g. {', '.join(n for n in ('LUNA', 'FTT') if n in close_panel.columns)}).")
    lines.append(f"- **Universe bar (generous, discovery-grade):** trailing-"
                 f"{config.DISCOVERY_LIQUIDITY_WINDOW}d median dollar volume >= "
                 f"${config.DISCOVERY_LIQUIDITY_MIN_USD:,} on Binance. The execution screen's $1M "
                 "Kraken bar is roughly $50M in Binance-equivalent volume, so this is ~10x looser: "
                 "a wide cross-section for XS signals, not a tradability claim.")
    lines.append(f"- **Halt- and corporate-action splitting:** data holes longer than "
                 f"{config.DISCOVERY_SEGMENT_GAP_DAYS} days AND the documented symbol-reuse events "
                 f"in `config.DISCOVERY_SYMBOL_SPLITS` (relists on a dead symbol, redenominations, "
                 f"token swaps: LUNA's Terra 2.0 relist printed a fake +17,700,000% one-day return "
                 f"before this fix) split a symbol into separate assets. {len(split_info)} coins "
                 f"split: {', '.join(sorted(split_info))}. No return can cross a halt or a swap. "
                 f"Real crash days with real volume (LUNA 2022-05-11/12, OM 2025-04-13) are kept.")
    lines.append("- **Costs:** discovery is judged GROSS (DEC-002 net columns exist but do not "
                 "decide anything here).")
    lines.append("")
    lines.append(f"**Panel:** {close_panel.index.min().date()} to {close_panel.index.max().date()}, "
                 f"{len(close_panel)} daily rows, {len(mondays)} weekly observations "
                 f"({int(vault_mask.sum())} daily rows on/after {config.OOS_VAULT_START} are locked "
                 f"in the one-look OOS vault). Assets: {len(reports)} segments from "
                 f"{len(reports) - sum(len(v) - 1 for v in split_info.values())} coins; "
                 f"{int(ever.sum())} ever pass the screen.")
    lines.append("")
    lines.append("**Universe breadth (median members/day by year):** "
                 + ", ".join(f"{y}: {n}" for y, n in by_year.items()) + ".")
    lines.append("")
    lines.append("**Regimes (defined in xmom/config.py, reported by every discovery backtest):** "
                 "daily BTC-vs-200d-SMA trend labels, plus named eras: "
                 + "; ".join(f"{name} ({start or 'panel start'} to {end or 'panel end'})"
                             for name, start, end in config.REGIME_ERAS) + ".")
    report_path = config.REPO_ROOT / "research" / "stage_a_data_report.md"
    existing = report_path.read_text()
    marker = "# Discovery dataset (Handoff #7 WS1)"
    if marker in existing:  # idempotent re-run: replace the section
        existing = existing[: existing.index("\n---\n\n" + marker) if "\n---\n\n" + marker in existing
                            else existing.index(marker)].rstrip() + "\n"
    report_path.write_text(existing + "\n".join(lines) + "\n")


if __name__ == "__main__":
    build()
