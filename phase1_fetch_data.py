"""
phase1_fetch_data.py  -  Stage A: pull raw daily OHLCV for the auto-enumerated universe.

Flow (see docs/MASTER_BRIEF.md Stage A and DEC-004/DEC-005):
  1. Enumerate ALL active Kraken USD spot pairs; drop stablecoins/fiat/token wrappers.
     No hand-picked seed list, and no pre-filtering by today's volume (that would
     re-introduce survivorship bias inside the window).
  2. Fetch Kraken daily candles per coin (venue-native, ~720-candle REST cap).
  3. Fetch deep pre-history from Binance (USDT quote) back to DEEP_HISTORY_START,
     following documented rebrands (MATIC->POL, FTM->S).
  4. Splice: Kraken authoritative; Binance rows strictly before Kraken's start are
     prepended only if overlap return-correlation >= 0.98 over >= 60 shared days.
  5. Write spliced Parquet to data/raw/, venue-native copies to data/raw/{kraken,secondary}/,
     and a full per-coin provenance table to data/processed/provenance.csv.

Run it (from the repo root, with the venv active):
    python phase1_fetch_data.py               # full network fetch
    python phase1_fetch_data.py --resplice    # re-splice from saved venue files, no network

Public data only: no API keys. Everything under data/ is gitignored and regenerable.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from xmom import config, data


def fetch_all():
    kraken = data.get_exchange(config.EXCHANGE_ID)
    bases, excluded = data.enumerate_bases(kraken)
    n_all = len(bases) + sum(len(v) for v in excluded.values())
    print(f"Enumerated {n_all} active Kraken {config.QUOTE} spot pairs.")
    for reason, names in excluded.items():
        print(f"  excluded {len(names):>3} {reason}: {', '.join(names) if names else '-'}")
    print(f"Candidate bases after exclusions: {len(bases)}\n")

    secondary = data.get_exchange(config.SECONDARY_EXCHANGE_ID)
    secondary.load_markets()

    provenance = []
    failures = []
    for i, base in enumerate(bases, 1):
        symbol = data.symbol_for(base)
        try:
            k_frame = data.fetch_ohlcv_df(kraken, symbol)
        except Exception as exc:
            failures.append({"base": base, "step": "kraken", "error": str(exc)[:120]})
            print(f"[{i:>3}/{len(bases)}] {base:<10} KRAKEN FETCH FAILED: {str(exc)[:60]}")
            continue
        if k_frame.empty:
            failures.append({"base": base, "step": "kraken", "error": "no candles"})
            print(f"[{i:>3}/{len(bases)}] {base:<10} no Kraken candles, skipped")
            continue
        data.save_raw(k_frame, base, config.DATA_RAW_KRAKEN)

        try:
            s_frame = data.fetch_secondary_history(secondary, base)
        except Exception as exc:
            s_frame = pd.DataFrame(columns=data.OHLCV_COLUMNS)
            failures.append({"base": base, "step": "secondary", "error": str(exc)[:120]})
        if not s_frame.empty:
            data.save_raw(s_frame, base, config.DATA_RAW_SECONDARY)

        spliced, prov = data.splice_history(k_frame, s_frame, base)
        data.save_raw(spliced, base)
        provenance.append(prov)

        if i % 25 == 0 or i == len(bases):
            n_spliced = sum(1 for p in provenance if p["spliced"])
            print(f"[{i:>3}/{len(bases)}] fetched, {n_spliced} spliced so far")

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    prov_df = pd.DataFrame(provenance)
    prov_df.to_csv(config.DATA_PROCESSED / "provenance.csv", index=False)
    manifest = {
        "enumerated": n_all,
        "excluded": {k: len(v) for k, v in excluded.items()},
        "excluded_names": excluded,
        "candidates": len(bases),
        "fetched": len(provenance),
        "spliced": int(prov_df["spliced"].sum()) if not prov_df.empty else 0,
        "failures": failures,
    }
    (config.DATA_PROCESSED / "fetch_manifest.json").write_text(json.dumps(manifest, indent=2))

    # Summary
    print(f"\nFetched {len(provenance)} coins ({len(failures)} failures/skips).")
    if not prov_df.empty:
        spliced = prov_df[prov_df["spliced"]]
        print(f"Deep-spliced {len(spliced)} coins with {config.SECONDARY_EXCHANGE_ID} pre-history "
              f"(median overlap corr {spliced['ret_corr'].median():.4f}).")
        rejects = prov_df[~prov_df["spliced"]]
        reasons = rejects["reject_reason"].value_counts()
        print("Kraken-only coins by reason:")
        for reason, n in reasons.items():
            print(f"  {n:>3}  {reason}")
    print(f"\nProvenance written to {config.DATA_PROCESSED / 'provenance.csv'}")
    print(f"Manifest written to {config.DATA_PROCESSED / 'fetch_manifest.json'}")
    return manifest


def resplice_only():
    """Re-run the splice step from saved venue-native files. No network calls."""
    kraken_files = sorted(config.DATA_RAW_KRAKEN.glob("*.parquet"))
    if not kraken_files:
        print("No venue-native files under data/raw/kraken; run the full fetch first.")
        return
    provenance = []
    for path in kraken_files:
        base = path.stem
        k_frame = data.load_raw(base, config.DATA_RAW_KRAKEN)
        sec_path = data.raw_path(base, config.DATA_RAW_SECONDARY)
        s_frame = (data.load_raw(base, config.DATA_RAW_SECONDARY)
                   if sec_path.exists() else pd.DataFrame(columns=data.OHLCV_COLUMNS))
        spliced, prov = data.splice_history(k_frame, s_frame, base)
        data.save_raw(spliced, base)
        provenance.append(prov)
    prov_df = pd.DataFrame(provenance)
    prov_df.to_csv(config.DATA_PROCESSED / "provenance.csv", index=False)
    spliced_df = prov_df[prov_df["spliced"]]
    print(f"Re-spliced {len(prov_df)} coins ({len(spliced_df)} with deep pre-history).")
    if len(spliced_df):
        print(f"Volume-basis ratio (Kraken/secondary): median {spliced_df['vol_ratio'].median():.4f}, "
              f"25th {spliced_df['vol_ratio'].quantile(0.25):.4f}, "
              f"75th {spliced_df['vol_ratio'].quantile(0.75):.4f}")


if __name__ == "__main__":
    if "--resplice" in sys.argv:
        resplice_only()
    else:
        fetch_all()
