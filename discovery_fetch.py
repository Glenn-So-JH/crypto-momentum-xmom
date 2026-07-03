"""
discovery_fetch.py  -  Handoff #7 WS1: fetch the broad discovery panel.

Single source: Binance daily klines from the public data.binance.vision bucket, which
retains DELISTED pairs (LUNA, FTT, ...), so the discovery universe is survivorship-
conscious in a way the live exchange API cannot be. Full available history per coin
(monthly files, complete months only). USDT-quoted spot pairs.

Exclusions (documented, auditable in the manifest): stablecoin/fiat/commodity bases
(same sets as the execution dataset) and Binance leveraged tokens, identified as a
base ending in UP/DOWN/BULL/BEAR whose stripped stem also exists as a base (BTCUP is
a token because BTC exists; JUP and SYRUP are real coins because J and SYR do not).

Run it:
    python discovery_fetch.py

Writes data/raw/discovery/{BASE}.parquet + data/processed/discovery_manifest.json.
No keys, public data only, everything gitignored and regenerable.
"""

from __future__ import annotations

import io
import json
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.etree import ElementTree

import pandas as pd
import requests

from xmom import config, data

S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CDN = "https://data.binance.vision"
KLINE_PREFIX = "data/spot/monthly/klines/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
KLINE_COLUMNS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
                 "quote_volume", "trades", "taker_base", "taker_quote", "ignore"]

_local = threading.local()


def _session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def _list_prefixes(prefix: str, delimiter: str = "/") -> list[str]:
    """Paginated S3 listing; returns CommonPrefixes (or Keys when delimiter='')."""
    out, marker = [], ""
    while True:
        r = _session().get(S3_LIST, params={"delimiter": delimiter, "prefix": prefix,
                                            "marker": marker}, timeout=30)
        r.raise_for_status()
        root = ElementTree.fromstring(r.content)
        for cp in root.findall(f"{NS}CommonPrefixes/{NS}Prefix"):
            out.append(cp.text)
        for key in root.findall(f"{NS}Contents/{NS}Key"):
            out.append(key.text)
        if root.findtext(f"{NS}IsTruncated") != "true":
            return out
        marker = root.findtext(f"{NS}NextMarker") or out[-1]


def filter_bases(bases: dict[str, str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Pure exclusion filter over {base: symbol}; returns (kept, excluded_by_reason)."""
    excluded: dict[str, list[str]] = {"stablecoin_fiat_commodity": [], "leveraged_token": []}
    kept: dict[str, str] = {}
    non_signal = config.STABLECOINS | config.FIAT | config.COMMODITY_TOKENS
    all_bases = set(bases)
    for base, symbol in bases.items():
        if base.upper() in non_signal:
            excluded["stablecoin_fiat_commodity"].append(base)
            continue
        if base in config.LEVERAGED_SUFFIXES or any(
            base.endswith(suf) and base[: -len(suf)] in all_bases
            for suf in config.LEVERAGED_SUFFIXES
        ):
            excluded["leveraged_token"].append(base)
            continue
        kept[base] = symbol
    return kept, excluded


def enumerate_discovery_bases() -> tuple[dict[str, str], dict[str, list[str]]]:
    """
    All USDT-quoted spot symbols ever hosted in the bucket, filtered.
    Returns ({base: symbol}, excluded_by_reason).
    """
    symbols = [p.split("/")[-2] for p in _list_prefixes(KLINE_PREFIX)]
    usdt = sorted(s for s in symbols if s.endswith(config.DISCOVERY_QUOTE))
    bases = {s[: -len(config.DISCOVERY_QUOTE)]: s for s in usdt}
    return filter_bases(bases)


def fetch_symbol(base: str, symbol: str) -> dict:
    """Download every monthly 1d zip for `symbol`, save one parquet per base."""
    keys = [k for k in _list_prefixes(f"{KLINE_PREFIX}{symbol}/1d/", delimiter="")
            if k.endswith(".zip")]
    frames = []
    for key in sorted(keys):
        r = _session().get(f"{CDN}/{key}", timeout=60)
        if r.status_code != 200:
            continue
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            with zf.open(zf.namelist()[0]) as fh:
                frame = pd.read_csv(fh, header=None, names=KLINE_COLUMNS)
        # Newer files sometimes carry a header row; drop non-numeric rows defensively.
        frame = frame[pd.to_numeric(frame["open_time"], errors="coerce").notna()]
        frames.append(frame)
    if not frames:
        return {"base": base, "symbol": symbol, "rows": 0}

    raw = pd.concat(frames, ignore_index=True)
    ts = pd.to_numeric(raw["open_time"], errors="coerce").astype("int64")
    # 2025+ files switched open_time from milliseconds to microseconds; normalize to ms.
    ts = ts.where(ts < 10**14, ts // 1000)
    idx = pd.to_datetime(ts, unit="ms").dt.normalize()
    out = raw[["open", "high", "low", "close", "volume"]].astype("float64")
    out.index = pd.DatetimeIndex(idx, name="date")
    out = out[~out.index.duplicated(keep="last")].sort_index()
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    out = out[out.index < today]

    config.DATA_RAW_DISCOVERY.mkdir(parents=True, exist_ok=True)
    out.to_parquet(config.DATA_RAW_DISCOVERY / f"{base}.parquet")
    return {"base": base, "symbol": symbol, "rows": int(len(out)),
            "first": out.index.min().date().isoformat(),
            "last": out.index.max().date().isoformat()}


def top_up_recent(results: list[dict]) -> int:
    """
    Monthly bucket files lag by up to ~5 weeks (the current month's zip appears a few
    days into the next month). Extend still-trading coins to the present via the
    Binance API; dead coins need no top-up. Returns the number of coins extended.
    """
    import ccxt

    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    exchange = ccxt.binance({"enableRateLimit": True})
    exchange.load_markets()
    extended = 0
    for r in results:
        if r["rows"] == 0:
            continue
        last = pd.Timestamp(r["last"])
        if (today - last).days > 45:
            continue  # long-dead: nothing recent to add
        symbol = f"{r['base']}/{config.DISCOVERY_QUOTE}"
        if symbol not in exchange.markets:
            continue
        try:
            since_ms = int((last + pd.Timedelta(days=1)).timestamp() * 1000)
            fresh = data.fetch_ohlcv_df(exchange, symbol, since_ms=since_ms, limit=1000)
        except Exception:
            continue
        if fresh.empty:
            continue
        path = config.DATA_RAW_DISCOVERY / f"{r['base']}.parquet"
        old = pd.read_parquet(path)
        merged = pd.concat([old, fresh])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        merged.to_parquet(path)
        r["last"] = merged.index.max().date().isoformat()
        r["rows"] = int(len(merged))
        extended += 1
    return extended


def main():
    kept, excluded = enumerate_discovery_bases()
    print(f"Bucket symbols quoted in {config.DISCOVERY_QUOTE}: "
          f"{len(kept) + sum(len(v) for v in excluded.values())}")
    for reason, names in excluded.items():
        print(f"  excluded {len(names):>3} {reason}")
    print(f"Fetching {len(kept)} bases with up to 16 threads...\n")

    results, errors = [], []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(fetch_symbol, b, s): b for b, s in kept.items()}
        for i, fut in enumerate(as_completed(futures), 1):
            base = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                errors.append({"base": base, "error": str(exc)[:120]})
            if i % 100 == 0 or i == len(futures):
                print(f"  [{i}/{len(futures)}] done ({len(errors)} errors)", flush=True)

    extended = top_up_recent(results)
    print(f"Topped up {extended} still-trading coins to the present via the API.")

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest = {
        "quote": config.DISCOVERY_QUOTE,
        "enumerated": len(kept) + sum(len(v) for v in excluded.values()),
        "excluded": {k: sorted(v) for k, v in excluded.items()},
        "fetched": len([r for r in results if r["rows"] > 0]),
        "empty": len([r for r in results if r["rows"] == 0]),
        "errors": errors,
        "coins": sorted(results, key=lambda r: r["base"]),
    }
    (config.DATA_PROCESSED / "discovery_manifest.json").write_text(json.dumps(manifest, indent=2))
    nonzero = [r for r in results if r["rows"] > 0]
    print(f"\nFetched {len(nonzero)} coins with data ({len(errors)} errors).")
    if nonzero:
        firsts = sorted(r["first"] for r in nonzero)
        print(f"Earliest history: {firsts[0]}; median first date: {firsts[len(firsts)//2]}")
    print(f"Manifest: {config.DATA_PROCESSED / 'discovery_manifest.json'}")


if __name__ == "__main__":
    main()
