"""
xmom  -  the reusable library for the XMom crypto cross-sectional momentum project.

The runnable scripts at the repo root (phase1_fetch_data.py, phase1_build_universe.py,
and later the backtest entry points) import from here. Keeping the logic in an
importable package is what lets the unit tests in tests/ exercise it without a network.

Stage 1A modules:
  config    - the knobs: universe, thresholds, paths, rename map.
  data      - fetch OHLCV from Kraken (handles the ~720-candle REST limit) and Parquet I/O.
  quality   - data-quality checks and cleaning (gaps, duplicates, outliers, ticker renames).
  universe  - the point-in-time liquidity screen that defeats survivorship bias.
"""

__all__ = ["config", "data", "quality", "universe"]
