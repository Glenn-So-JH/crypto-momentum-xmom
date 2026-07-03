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
    "FTM": "S",     # Fantom -> Sonic (2025-01); no-op on venues without an FTM file
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

# --- Discovery dataset (Handoff #7 WS1): broad, single-source, gross-only --------
# Signal discovery uses the cleanest broadest panel (Binance daily, full history per
# coin, includes delisted pairs from data.binance.vision), judged GROSS across
# regimes. Kraken tradability is a LATER gate applied only to survivors. This block
# never feeds the execution dataset above.
DATA_RAW_DISCOVERY = DATA_RAW / "discovery"
DISCOVERY_QUOTE = "USDT"
DISCOVERY_LIQUIDITY_WINDOW = 30
DISCOVERY_LIQUIDITY_MIN_USD = 5_000_000   # generous: ~10x looser than the Kraken
                                          # screen's Binance-equivalent (~$50M)
DISCOVERY_SEGMENT_GAP_DAYS = 30  # a data hole longer than this (delist/relist halt)
                                 # splits the coin into separate assets: no fake
                                 # return may ever cross a trading halt
# Leveraged-token suffixes excluded when the stripped stem also exists as a base
# (BTCUP -> BTC exists -> leveraged token; JUP -> J does not -> real coin). A base
# that IS one of these words (FTX-era BULL/BEAR 3x tokens) is also excluded.
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")

# Corporate-actions split list: dates where a symbol was reused for an economically
# different asset (relist after death, redenomination, token swap), so the one-day
# "return" across the date is fiction. Each date starts a NEW asset (__R1, ...).
# Built from a systematic |log return| > 2.3 scan classified case by case; the
# decisive fingerprint for most is zero trailing dollar volume (a halted market no
# one could trade across). Real crashes with real volume (LUNA 05-11/12, OM 2025-04,
# BTCST 2021-03) are deliberately NOT here. Auditable in git; extend as found.
DISCOVERY_SYMBOL_SPLITS = {
    "LUNA": ["2022-05-31"],    # Terra 2.0 relisted on the old symbol (+17.7M% fake)
    "COCOS": ["2021-01-23"],   # 1:1000 redenomination
    "DREP": ["2021-04-02"],    # 1:100 token swap
    "QUICK": ["2023-07-21"],   # 1:1000 new-token swap
    "SUN": ["2021-06-18"],     # 1:1000 redenomination
    "BNX": ["2023-02-22"],     # 1:100 redenomination after halt (pre-jump volume 0)
    "VIDT": ["2022-11-09"],    # VIDT DAO swap after halt (pre-jump volume 0)
    "STRAX": ["2024-03-28"],   # Stratis 10:1 token swap
}

# --- Regimes (Handoff #7 WS1.4 / WS3): first-class, defined once here -------------
# Two orthogonal labelings, both reported by every discovery backtest:
#   1. Trend regime, daily: BULL when BTC close > its 200d SMA, else BEAR.
#   2. Named eras, contiguous date ranges (end date inclusive).
REGIME_TREND_ASSET = "BTC"
REGIME_TREND_SMA = 200
REGIME_ERAS = [
    ("2017-18 mania and bust", None, "2018-12-31"),   # None = panel start
    ("2019 chop",              "2019-01-01", "2020-02-14"),
    ("2020 covid crash",       "2020-02-15", "2020-04-15"),
    ("2020-21 bull",           "2020-04-16", "2021-11-10"),
    ("2022 bear",              "2021-11-11", "2022-12-31"),
    ("2023-24 recovery",       "2023-01-01", "2024-12-31"),
    ("2025+ vault era",        "2025-01-01", None),    # None = panel end
]

# --- Firm-sim market-neutral construction (Handoff #8, docs/08_FIRM_SIM_CHARTER) --
# Each alpha book is long-short and hedged to near-zero beta against the market
# factor; shorting is abstracted (perps assumed), so these are research exposures.
MN_MARKET_ASSET = "BTC"        # market factor proxy and the hedge leg
MN_BETA_WINDOW = 90            # rolling beta estimation window (days)
MN_BETA_MIN_PERIODS = 60
MN_VOL_WINDOW = 30             # per-name vol for inverse-vol sizing
MN_RESID_VOL_WINDOW = 60       # residual vol window for the factor risk model
MN_VOL_TARGET = 0.15           # annualized target for a market-neutral sleeve
MN_GROSS_CAP = 2.0             # sum |w| ceiling per sleeve (200% gross)
MN_NAME_CAP = 0.10             # |w_i| ceiling per non-hedge name
MN_ZSCORE_WINSOR = 3.0         # cross-sectional z-scores clipped at +/- 3
MN_FUNDING_RATE_ANNUAL = 0.0   # dormant realism hook: perp funding charged on gross

# --- Out-of-sample vault (Handoff #7 WS3) -----------------------------------------
# Everything on/after OOS_VAULT_START is the locked one-look vault: tuning, plateau
# sweeps, and iteration use strictly pre-vault data; the vault is scored once per
# finished candidate and labeled the final exam. Discipline documented in
# docs/ALPHA_SANDBOX.md and enforced by run_alpha.py (vault off by default).
OOS_VAULT_START = "2025-01-01"
WF_INITIAL_TRAIN_WEEKS = 52    # anchored walk-forward: first training window
WF_TEST_WEEKS = 13             # out-of-sample fold length (one quarter)
