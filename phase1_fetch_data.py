"""
phase1_fetch_data.py  -  Stage 1A, step 1: pull raw daily OHLCV for the seed universe.

What it does: for each candidate coin, fetch as much daily history as Kraken's REST API
will give (~720 candles, see config.HISTORY_DAYS), save it verbatim to data/raw/<COIN>.parquet,
and print a table of the actual history depth achieved per coin. No cleaning or screening here.

Run it (from the repo root, with the venv active):
    python phase1_fetch_data.py

Public data only: no API keys needed. data/raw is gitignored.
"""

from __future__ import annotations

from xmom import config, data


def fetch_universe():
    exchange = data.get_exchange()
    markets = exchange.load_markets()
    print(f"Connected to {config.EXCHANGE_ID}: {len(markets)} markets available.\n")

    # Fetch the seed universe plus any pre-rename symbols (e.g. MATIC) so the build step
    # can stitch them into their new canonical coin.
    bases = list(dict.fromkeys(config.SEED_UNIVERSE + list(config.TICKER_RENAMES.keys())))

    results = []
    missing = []
    for base in bases:
        symbol = data.symbol_for(base)
        if symbol not in markets:
            missing.append(symbol)
            print(f"  skip {symbol:<12} not listed on {config.EXCHANGE_ID}")
            continue
        try:
            frame = data.fetch_ohlcv_df(exchange, symbol)
        except Exception as exc:  # network / rate-limit / venue error: report, keep going
            missing.append(f"{symbol} (error: {str(exc)[:50]})")
            print(f"  error {symbol:<12} {str(exc)[:60]}")
            continue
        if frame.empty:
            missing.append(f"{symbol} (no data)")
            print(f"  empty {symbol:<12} returned no candles")
            continue
        data.save_raw(frame, base)
        results.append(
            {
                "base": base,
                "rows": len(frame),
                "first": frame.index.min().date().isoformat(),
                "last": frame.index.max().date().isoformat(),
            }
        )

    # History-depth report: the actual coverage we got, per coin.
    print("\nFetched history depth (saved to data/raw/):\n")
    header = f"{'COIN':<8}{'CANDLES':>9}{'FIRST':>14}{'LAST':>14}"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda x: x["base"]):
        print(f"{r['base']:<8}{r['rows']:>9}{r['first']:>14}{r['last']:>14}")

    print(f"\nFetched {len(results)} coins. Missing/failed: {len(missing)}.")
    if missing:
        print("Not fetched: " + ", ".join(missing))
    return results, missing


if __name__ == "__main__":
    fetch_universe()
