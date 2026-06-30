# Stage 1A: Data-quality note and history-depth report

**Date:** 2026-06-30 · **Venue:** Kraken (USD spot) · **Pipeline:** `phase1_fetch_data.py` → `phase1_build_universe.py`

This is the committed, version-controlled evidence for the Stage 1A gate. The raw and
processed data themselves are gitignored (regenerable by re-running the two scripts); this
note records what the data looked like and what we found wrong with it. A machine-generated
copy of the per-coin table is written to `data/processed/DATA_QUALITY.md` on every run.

## What we collected

- **Daily OHLCV** for 22 liquid Kraken USD pairs, the seed universe in `xmom/config.py`.
- **Coverage:** 721 daily candles each, **2024-07-10 → 2026-06-30** (about 2.0 years), identical
  across all coins.
- **Two candidates not fetched:** `MKR/USD` and `MATIC/USD` are not in this Kraken market list.
  MATIC's absence is expected: Kraken now serves Polygon only as **POL**, which has full history,
  so the MATIC→POL rename stitch had nothing to merge (the machinery is in place and unit-tested
  for the next rename that does need it).

## The Kraken history limit, confirmed

Phase 0 research predicted Kraken's REST OHLC endpoint caps at ~720 candles and cannot page
deep into the past. **Confirmed exactly:** every coin returned 721 candles and no more, despite
requesting 740 days. This bounds Phase 1 to a single ~2-year window. Deeper history (Kraken's
downloadable OHLCVT archives) is a deliberate later follow-up: make it work first, then make it
deep. The fetcher's pagination loop is venue-generic, so a deeper-history source needs no rewrite.

## Quality findings

The data is clean. Across 22 coins × 721 days: **0 duplicate dates, 0 calendar gaps, 0 suspect
prints** (no daily move past the |log-return| > 0.75 flag). One real finding:

- **POL: 19 zero-volume days.** Polygon's Kraken USD book is thin and had genuine no-trade days.
  This is not corrupted data, it is a liquidity fact, and the screen below uses it correctly: zero
  volume drags POL's trailing median down, which is exactly why POL is *out* of the current universe.

Cleaning applied (all transparent, none destructive): sort by date, drop duplicate dates, reindex
to a gap-free daily calendar, forward-fill price across any gap and set that day's volume to 0
(treat an unobserved day as illiquid, never as liquid). Suspect prints are flagged for review, never
auto-deleted.

## Point-in-time liquidity screen (survivorship-bias defense)

Membership is decided **as of each date** using only trailing data: a coin is in the universe on
date *t* iff its **trailing-30-day median daily dollar volume ≥ $1,000,000** at *t* (a coin needs a
full 30-day window before it can qualify). Median, not mean, so a single spike day cannot buy a coin
in. A unit test (`test_universe_is_point_in_time`) proves membership at *t* is unchanged when all
future data is hidden, i.e. the screen cannot look ahead.

**Universe size per day:** min 0 (the first ~30 days are a warm-up with no full window), 25th pct 11,
median 13, 75th pct 14, max 21.

**Current universe (12 of 22), trailing-30d median $volume as of 2026-06-30:**

| in? | coin | median daily $vol |
|---|---|---:|
| ✅ | BTC | 137,223,162 |
| ✅ | ETH | 42,570,842 |
| ✅ | SOL | 23,984,272 |
| ✅ | XRP | 22,624,345 |
| ✅ | ADA | 7,955,826 |
| ✅ | XLM | 5,682,473 |
| ✅ | NEAR | 4,924,312 |
| ✅ | DOGE | 4,617,465 |
| ✅ | LINK | 2,338,041 |
| ✅ | AVAX | 2,332,656 |
| ✅ | LTC | 2,297,285 |
| ✅ | TRX | 1,269,122 |
| — | BCH | 938,578 |
| — | UNI | 664,220 |
| — | ALGO | 662,694 |
| — | AAVE | 638,509 |
| — | DOT | 601,429 |
| — | ATOM | 333,465 |
| — | POL | 272,108 |
| — | FIL | 219,731 |
| — | GRT | 128,783 |
| — | ETC | 71,688 |

The ranking is clean and monotonic with a sharp cutoff: BCH ($939k) and DOT ($601k) sit just under
the bar. These are **Kraken USD-pair** volumes, which are thinner than the global market or USDT
pairs, so the $1M floor is doing real work here, not rubber-stamping everything.

## Known limitations (stated out loud)

- **History depth:** ~2 years only (REST cap). One bull-and-bear window, but not multi-cycle. A
  regime-dependence caveat for every result that follows.
- **Threshold is a tunable default.** $1M/day is a transparent Phase-1 choice, not a law. Phase 2 can
  lower it, switch to a relative top-N rule, or add USDT pairs for more depth. The screen is
  parameterized so this is a one-line change.
- **Residual survivorship risk.** We screen point-in-time on coins Kraken lists *today*, so truly
  dead coins delisted before the window (LUNA, FTT, …) are absent from the candidate set entirely.
  Within the window the screen is honest; across delistings it still cannot see what was already gone.
- **Single venue.** Kraken only, by design (research data matches the trade venue).

## Gate status

Met. We have a reproducible, documented dataset we have actively tried to break and trust anyway, the
actual per-coin history depth is reported, and we can list which assets were liquid enough to trade at
each point in time. Next: Stage 1B (the vectorized engine + metrics + the buy-and-hold sanity and
look-ahead-guard tests).
