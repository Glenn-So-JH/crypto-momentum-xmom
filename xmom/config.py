"""
config.py  -  the single place where Phase 1 parameters live.

Every number here is a decision we can defend in the progress log. Nothing magic is
buried in the scripts; if you want to change the universe or the liquidity bar, you
change it here and re-run.
"""

from pathlib import Path

# --- Paths ---------------------------------------------------------------------
# Resolve everything relative to the repo root so scripts work from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"            # one Parquet per coin, as fetched (gitignored)
DATA_PROCESSED = REPO_ROOT / "data" / "processed"  # cleaned panels + universe (gitignored)

# --- Venue / data --------------------------------------------------------------
EXCHANGE_ID = "kraken"   # our trading venue, so research data matches what we will trade
QUOTE = "USD"            # we trade USD spot pairs
TIMEFRAME = "1d"         # daily candles for daily-frequency research

# Kraken's REST OHLC endpoint returns at most ~720 candles and cannot page deep into
# the past, so daily history via REST is roughly the last two years. We request a
# little more than 720 days and accept whatever Kraken returns, reporting the actual
# depth per coin. Deeper history (Kraken's downloadable OHLCVT archives) is a
# deliberate later follow-up: make it work first, then make it deep.
HISTORY_DAYS = 740

# --- Universe ------------------------------------------------------------------
# Seed universe: liquid Kraken USD majors to screen from (charter target: ~20-40 names).
# These are *candidates*; the point-in-time liquidity screen decides membership per date.
SEED_UNIVERSE = [
    "BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC", "BCH",
    "ATOM", "UNI", "AAVE", "ALGO", "XLM", "ETC", "FIL", "NEAR", "DOGE",
    "TRX", "MKR", "GRT", "POL",
]

# Stablecoins and fiat never enter the universe: they do not move, so a momentum
# signal on them is meaningless. The screen excludes any base in this set.
STABLECOINS = {
    "USDT", "USDC", "DAI", "TUSD", "USDD", "PYUSD", "FDUSD", "USDS", "GUSD",
    "USD", "EUR", "GBP", "AUD", "CAD", "CHF", "JPY",
}

# Ticker renames: some coins were rebranded and Kraken lists them under the new
# symbol, which silently splits a price history if not stitched. Map OLD -> NEW; the
# build step merges any old-symbol history into the new canonical symbol.
# Most prominent case: Polygon's MATIC migrated to POL.
TICKER_RENAMES = {
    "MATIC": "POL",
}

# --- Liquidity screen ----------------------------------------------------------
# A coin is "in the universe" on date t only if its trailing dollar volume cleared a
# bar *on that date* (point-in-time, no look-ahead). We use the trailing-window MEDIAN
# of daily dollar volume (median is robust to a single spike day) and an absolute
# floor. The floor is a transparent Phase-1 default; Phase 2 can switch to a relative
# rule (e.g. top-N each date) without touching the engine.
LIQUIDITY_WINDOW = 30          # trailing days for the dollar-volume measure
LIQUIDITY_MIN_USD = 1_000_000  # require >= $1M/day trailing-median dollar volume

# --- Quality checks ------------------------------------------------------------
# Daily log-return magnitude above this is FLAGGED as a suspect print for human review.
# Crypto really can move 30-40% in a day, so this is a "look at this", not an auto-delete.
OUTLIER_LOG_RETURN = 0.75  # ~ +112% / -53% in a single day
