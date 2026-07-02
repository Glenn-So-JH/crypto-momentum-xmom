"""
data.py  -  fetch daily OHLCV and store it as Parquet.

Stage A responsibilities:
  1. Enumerate the candidate universe directly from the venue (DEC-005): all active
     Kraken USD spot pairs minus stablecoins, fiat, and non-crypto token wrappers.
  2. Fetch venue-native candles from Kraken (handles the ~720-candle REST limit).
  3. Fetch deep pre-history from the documented secondary venue (Binance, USDT quote).
  4. Splice the two per coin: Kraken authoritative wherever it exists, secondary rows
     prepended strictly before Kraken's first date, accepted only if the venues agree
     on the overlap (return correlation). Every splice is recorded in a provenance row.

No cleaning or screening here: that is quality.py and universe.py. This module gets
honest raw bytes onto disk and writes down exactly where every row came from.
"""

from __future__ import annotations

import time

import ccxt
import numpy as np
import pandas as pd

from . import config

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def get_exchange(exchange_id: str = config.EXCHANGE_ID):
    """Build a public (no-keys) CCXT exchange with rate limiting on."""
    return getattr(ccxt, exchange_id)({"enableRateLimit": True})


def symbol_for(base: str, quote: str = config.QUOTE) -> str:
    """'BTC' -> 'BTC/USD'."""
    return f"{base}/{quote}"


def enumerate_bases(exchange) -> tuple[list[str], dict[str, list[str]]]:
    """
    DEC-005: enumerate all active spot bases quoted in config.QUOTE on the venue,
    then drop stablecoins, fiat, and non-crypto token wrappers.

    Returns (kept_bases_sorted, excluded) where excluded maps reason -> bases, so the
    funnel can be reported and audited.
    """
    markets = exchange.load_markets()
    bases = sorted(
        {
            m["base"]
            for m in markets.values()
            if m.get("spot") and m.get("active") and m.get("quote") == config.QUOTE
        }
    )
    excluded: dict[str, list[str]] = {"stablecoin": [], "fiat": [], "commodity_token": []}
    kept = []
    for base in bases:
        up = base.upper()
        if up in config.STABLECOINS:
            excluded["stablecoin"].append(base)
        elif up in config.FIAT:
            excluded["fiat"].append(base)
        elif up in config.COMMODITY_TOKENS:
            excluded["commodity_token"].append(base)
        else:
            kept.append(base)
    return kept, excluded


def fetch_ohlcv_df(
    exchange,
    symbol: str,
    timeframe: str = config.TIMEFRAME,
    since_ms: int | None = None,
    history_days: int = config.HISTORY_DAYS,
    limit: int = 720,
    max_iters: int = 50,
) -> pd.DataFrame:
    """
    Fetch daily candles for one symbol, paging forward from `since` until now.

    Works for both venues: Kraken ignores deep `since` values (returns its ~720-candle
    tail, confirmed empirically), while Binance pages honestly through years. Rows are
    keyed by timestamp so overlapping pages de-duplicate naturally.

    Returns a DataFrame indexed by tz-naive daily UTC timestamps with columns
    [open, high, low, close, volume]. Empty DataFrame if the symbol returns nothing.
    """
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    since = since_ms if since_ms is not None else (
        exchange.milliseconds() - history_days * 24 * 60 * 60 * 1000
    )

    rows: dict[int, list] = {}
    for _ in range(max_iters):
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not batch:
            break
        for row in batch:
            rows[row[0]] = row

        last_ts = batch[-1][0]
        next_since = last_ts + timeframe_ms
        if next_since <= since:  # not advancing (venue returned the same tail)
            break
        since = next_since
        if last_ts >= exchange.milliseconds() - timeframe_ms:  # reached the present
            break
        time.sleep(exchange.rateLimit / 1000.0)

    if not rows:
        return pd.DataFrame(columns=OHLCV_COLUMNS)

    ordered = [rows[ts] for ts in sorted(rows)]
    frame = pd.DataFrame(ordered, columns=["ts"] + OHLCV_COLUMNS)
    # ms epoch -> daily UTC date, tz-naive (simpler joins; everything is daily UTC).
    frame.index = pd.to_datetime(frame["ts"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame.index.name = "date"
    frame = frame[OHLCV_COLUMNS].astype("float64")
    # Drop a possibly-partial today candle: daily research data must be closed candles.
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    return frame[frame.index < today]


def fetch_secondary_history(exchange, base: str) -> pd.DataFrame:
    """
    Deep daily history for `base` from the secondary venue, including any documented
    pre-rebrand symbol (config.SECONDARY_PREHISTORY). Newer symbol wins on overlaps.
    """
    since_ms = exchange.parse8601(f"{config.DEEP_HISTORY_START}T00:00:00Z")
    symbols = [f"{old}/{config.SECONDARY_QUOTE}" for old in config.SECONDARY_PREHISTORY.get(base, [])]
    symbols.append(f"{base}/{config.SECONDARY_QUOTE}")  # current symbol last = authoritative

    merged: pd.DataFrame | None = None
    for symbol in symbols:
        if symbol not in exchange.markets:
            continue
        try:
            frame = fetch_ohlcv_df(exchange, symbol, since_ms=since_ms, limit=1000)
        except Exception:
            continue
        if frame.empty:
            continue
        if merged is None:
            merged = frame
        else:
            merged = pd.concat([merged, frame])
            merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    return merged if merged is not None else pd.DataFrame(columns=OHLCV_COLUMNS)


def reconcile_overlap(kraken: pd.DataFrame, secondary: pd.DataFrame) -> dict:
    """
    Compare the two venues on their common dates: correlation of daily close-to-close
    returns plus mean absolute close difference (as a fraction of Kraken close).
    """
    common = kraken.index.intersection(secondary.index)
    out = {"overlap_days": int(len(common)), "ret_corr": np.nan, "mean_abs_close_diff": np.nan}
    if len(common) < 3:
        return out
    k_close = kraken.loc[common, "close"]
    s_close = secondary.loc[common, "close"]
    k_ret = k_close.pct_change().dropna()
    s_ret = s_close.pct_change().dropna()
    joined = pd.concat([k_ret, s_ret], axis=1, keys=["k", "s"]).dropna()
    if len(joined) >= 3 and joined["k"].std() > 0 and joined["s"].std() > 0:
        out["ret_corr"] = float(joined["k"].corr(joined["s"]))
    out["mean_abs_close_diff"] = float(((s_close - k_close).abs() / k_close).mean())
    return out


def volume_ratio(kraken: pd.DataFrame, secondary: pd.DataFrame) -> float:
    """
    Venue liquidity share on the overlap: median Kraken dollar volume divided by median
    secondary dollar volume. Used to scale pre-splice volumes to a Kraken-equivalent
    basis so the liquidity screen measures OUR venue throughout (the raw secondary
    volumes are 10-50x Kraken's and would inflate historical universe breadth, then
    cliff at the splice date). Clipped to [1e-4, 10]; NaN when not computable.
    """
    common = kraken.index.intersection(secondary.index)
    if len(common) < 3:
        return float("nan")
    k = (kraken.loc[common, "close"] * kraken.loc[common, "volume"]).median()
    s = (secondary.loc[common, "close"] * secondary.loc[common, "volume"]).median()
    if not (k > 0 and s > 0):
        return float("nan")
    return float(np.clip(k / s, 1e-4, 10.0))


def splice_history(kraken: pd.DataFrame, secondary: pd.DataFrame, base: str) -> tuple[pd.DataFrame, dict]:
    """
    Kraken rows are authoritative. Secondary rows strictly BEFORE Kraken's first date
    are prepended, but only when the overlap reconciliation clears the acceptance bar
    (config.RECONCILE_MIN_CORR over >= RECONCILE_MIN_OVERLAP_DAYS). Otherwise the coin
    stays Kraken-only and the rejection is recorded.

    Prepended volumes are scaled to a Kraken-equivalent basis by the overlap volume
    ratio (see volume_ratio); prices are NEVER modified. Stated proxy assumption: the
    venue share is treated as constant back in time, estimated on the overlap window.

    Returns (spliced_frame, provenance_row).
    """
    prov = {
        "base": base,
        "kraken_rows": int(len(kraken)),
        "secondary_rows": int(len(secondary)),
        "spliced": False,
        "splice_date": None,           # first Kraken date = first venue-native row
        "prepended_rows": 0,
        "overlap_days": 0,
        "ret_corr": np.nan,
        "mean_abs_close_diff": np.nan,
        "vol_ratio": np.nan,           # Kraken/secondary dollar-volume share on overlap
        "reject_reason": "",
    }
    if kraken.empty:
        prov["reject_reason"] = "no kraken data"
        return kraken, prov
    prov["splice_date"] = kraken.index.min().date().isoformat()
    if secondary.empty:
        prov["reject_reason"] = "no secondary data"
        return kraken, prov

    rec = reconcile_overlap(kraken, secondary)
    prov.update({k: rec[k] for k in ("overlap_days", "ret_corr", "mean_abs_close_diff")})

    pre = secondary[secondary.index < kraken.index.min()]
    if pre.empty:
        prov["reject_reason"] = "secondary adds no earlier history"
        return kraken, prov
    if rec["overlap_days"] < config.RECONCILE_MIN_OVERLAP_DAYS:
        prov["reject_reason"] = f"overlap {rec['overlap_days']}d < {config.RECONCILE_MIN_OVERLAP_DAYS}d"
        return kraken, prov
    if not (rec["ret_corr"] >= config.RECONCILE_MIN_CORR):  # NaN corr fails too
        prov["reject_reason"] = f"ret corr {rec['ret_corr']:.4f} < {config.RECONCILE_MIN_CORR}"
        return kraken, prov

    ratio = volume_ratio(kraken, secondary)
    pre = pre.copy()
    if np.isfinite(ratio):
        pre["volume"] = pre["volume"] * ratio  # Kraken-equivalent liquidity basis
        prov["vol_ratio"] = ratio
    spliced = pd.concat([pre, kraken]).sort_index()
    spliced = spliced[~spliced.index.duplicated(keep="last")]
    prov["spliced"] = True
    prov["prepended_rows"] = int(len(pre))
    return spliced, prov


def raw_path(base: str, folder=None):
    folder = config.DATA_RAW if folder is None else folder
    return folder / f"{base}.parquet"


def save_raw(frame: pd.DataFrame, base: str, folder=None) -> None:
    folder = config.DATA_RAW if folder is None else folder
    folder.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(raw_path(base, folder))


def load_raw(base: str, folder=None) -> pd.DataFrame:
    return pd.read_parquet(raw_path(base, folder))
