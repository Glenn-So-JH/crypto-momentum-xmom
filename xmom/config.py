"""
config.py  -  the single place where Phase 1/2 parameters live.

Every number here is a decision we can defend in the progress log. Nothing magic is
buried in the scripts; if you want to change the universe or the liquidity bar, you
change it here and re-run.
"""

from pathlib import Path

# --- Paths ---------------------------------------------------------------------
# Resolve everything relative to the repo root so scripts work from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"              # spliced per-coin Parquet (gitignored)
DATA_RAW_KRAKEN = DATA_RAW / "kraken"              # venue-native Kraken candles
DATA_RAW_SECONDARY = DATA_RAW / "secondary"        # deep-history source candles
DATA_PROCESSED = REPO_ROOT / "data" / "processed"  # cleaned panels + universe (gitignored)
FIGURES = REPO_ROOT / "research" / "figures"       # committed result charts

# --- Venue / data --------------------------------------------------------------
EXCHANGE_ID = "kraken"   # our trading venue, so research data matches what we will trade
QUOTE = "USD"            # we trade USD spot pairs
TIMEFRAME = "1d"         # daily candles for daily-frequency research

# Kraken's REST OHLC endpoint returns at most ~720 candles (confirmed empirically in
# Stage 1A: every pair returned exactly 721). Kraken's downloadable OHLCVT archives are
# served only through Google Drive behind a browser, so deep history comes from a
# documented secondary venue instead (DEC-004 fallback, see MASTER_BRIEF Stage A).
HISTORY_DAYS = 740

# --- Deep history (Stage A) ------------------------------------------------------
# Secondary source for pre-Kraken-window history: Binance daily candles, USDT quote.
# Binance is the deepest-liquidity venue with a public paginating API; the USDT/USD
# basis is a few bps outside depeg episodes and is documented in the data note.
SECONDARY_EXCHANGE_ID = "binance"
SECONDARY_QUOTE = "USDT"
DEEP_HISTORY_START = "2019-01-01"   # ~7.5 years: covers 2019 chop, 2020-21 bull, 2022 bear

# Splice acceptance: Kraken is authoritative where it exists; secondary rows are
# prepended strictly before Kraken's first date, and only if the two venues agree on
# the overlap window (daily close-to-close return correlation).
RECONCILE_MIN_OVERLAP_DAYS = 60
RECONCILE_MIN_CORR = 0.98

# Pre-history symbol map for the secondary venue: Kraken lists the NEW symbol, but the
# deep history lives under the OLD Binance symbol. Values are tried oldest-last and
# merged with the newer symbol authoritative on overlaps. Only clear, well-documented
# rebrands go here; ambiguous cases (e.g. LUNA/LUNC) stay Kraken-only and are reported.
SECONDARY_PREHISTORY = {
    "POL": ["MATIC"],   # Polygon MATIC -> POL (2024-09)
    "S": ["FTM"],       # Fantom FTM -> Sonic S (2025-01)
}

# --- Universe (DEC-005: auto-enumerated, not hand-curated) -----------------------
# The candidate set is ALL active Kraken USD spot pairs at fetch time, minus the
# exclusion sets below. No hand-picked seed list; the point-in-time screen decides
# membership per date. Residual survivorship caveat: coins Kraken delisted before
# fetch time never enter the candidate set; stated in every results report.

# Stablecoins and fiat never enter the universe: pegged assets do not trend, so a
# momentum signal on them is meaningless. USTC (the failed TerraUSD peg) is excluded
# under the same intent rule even though it now floats.
STABLECOINS = {
    "USDT", "USDC", "DAI", "TUSD", "USDD", "PYUSD", "FDUSD", "USDS", "GUSD",
    "USDG", "USDR", "RLUSD", "USDQ", "USD1", "USDE", "SUSDE", "USTC", "UST",
    "EURT", "EURC", "EURQ", "EURR", "EUROP", "AUSD", "GYEN", "ZUSD", "LUSD",
    "PAX", "USDP", "BUSD", "HUSD",
}
FIAT = {"USD", "EUR", "GBP", "AUD", "CAD", "CHF", "JPY", "SGD", "NZD"}

# Non-crypto tokenized assets: commodities and equity wrappers are not in scope for a
# crypto momentum universe (different asset class wearing a token costume).
COMMODITY_TOKENS = {"PAXG", "XAUT", "KAG", "KAU"}

# Ticker renames on the KRAKEN side (old Kraken symbol -> new): auto-enumeration always
# sees the current symbol, so this map only matters if raw files from an older fetch
# are still on disk. Kept for the stitch machinery and its tests.
TICKER_RENAMES = {
    "MATIC": "POL",
}

# --- Liquidity screen ----------------------------------------------------------
# A coin is "in the universe" on date t only if its trailing dollar volume cleared a
# bar *on that date* (point-in-time, no look-ahead). Trailing-window MEDIAN of daily
# dollar volume (robust to single-day spikes) with an absolute floor.
LIQUIDITY_WINDOW = 30          # trailing days for the dollar-volume measure
LIQUIDITY_MIN_USD = 1_000_000  # require >= $1M/day trailing-median dollar volume

# --- Quality checks ------------------------------------------------------------
# Daily log-return magnitude above this is FLAGGED as a suspect print for human review.
# Crypto really can move 30-40% in a day, so this is a "look at this", not an auto-delete.
OUTLIER_LOG_RETURN = 0.75  # ~ +112% / -53% in a single day

# --- Backtest conventions (binding, from docs/03 and docs/04) --------------------
ANNUALIZATION = 365            # crypto trades every calendar day
WARMUP_DAYS = 200              # longest lookback in the Stage 1C grid (SMA 200)
COST_PER_SIDE_DECIDING = 0.0050   # DEC-002: 50 bps/side decides
COST_PER_SIDE_OPTIMISTIC = 0.0025 # DEC-002: 25 bps/side reported alongside
