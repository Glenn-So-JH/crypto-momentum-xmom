"""
data.py  -  fetch daily OHLCV from Kraken and store it as Parquet.

Two responsibilities only:
  1. Talk to the exchange (via CCXT) and pull candles, handling Kraken's ~720-candle
     REST limit explicitly instead of pretending it does not exist.
  2. Read/write per-coin Parquet files under data/raw.

No cleaning or screening happens here: that is quality.py and universe.py. This module
just gets honest raw bytes onto disk.
"""

from __future__ import annotations

import time

import ccxt
import pandas as pd

from . import config

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def get_exchange(exchange_id: str = config.EXCHANGE_ID):
    """Build a public (no-keys) CCXT exchange with rate limiting on."""
    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    return exchange


def symbol_for(base: str, quote: str = config.QUOTE) -> str:
    """'BTC' -> 'BTC/USD'."""
    return f"{base}/{quote}"


def fetch_ohlcv_df(
    exchange,
    symbol: str,
    timeframe: str = config.TIMEFRAME,
    history_days: int = config.HISTORY_DAYS,
    max_iters: int = 50,
) -> pd.DataFrame:
    """
    Fetch up to ~history_days of candles for one symbol.

    Kraken caps a single OHLC call at ~720 candles and will not page far into the past.
    We loop forward from `since`, de-duplicating by timestamp, and stop when we reach the
    present or the data stops advancing. For Kraken this lands the available ~2 years; the
    same code would page through a deeper-history exchange unchanged.

    Returns a DataFrame indexed by tz-naive daily UTC timestamps with columns
    [open, high, low, close, volume]. Empty DataFrame if the symbol returns nothing.
    """
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    since = exchange.milliseconds() - history_days * 24 * 60 * 60 * 1000

    rows: dict[int, list] = {}
    for _ in range(max_iters):
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=720)
        if not batch:
            break
        for row in batch:
            rows[row[0]] = row  # key by timestamp -> natural de-dup

        last_ts = batch[-1][0]
        next_since = last_ts + timeframe_ms
        # Stop if we did not advance (Kraken returning the same tail) or reached now.
        if next_since <= since:
            break
        since = next_since
        if last_ts >= exchange.milliseconds() - timeframe_ms:
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
    return frame


def raw_path(base: str):
    return config.DATA_RAW / f"{base}.parquet"


def save_raw(frame: pd.DataFrame, base: str) -> None:
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(raw_path(base))


def load_raw(base: str) -> pd.DataFrame:
    return pd.read_parquet(raw_path(base))
