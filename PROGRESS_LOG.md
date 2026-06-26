# Progress Log

A dated journal of the project. This is the raw material for the LinkedIn series and the record that keeps the work honest. Append a new entry at the end of every work session. Do not edit old entries; if something was wrong, note the correction in a new entry.

**Entry template (copy this):**

```
## YYYY-MM-DD | Phase X | <short title>
**Did:** what I actually worked on.
**Learned:** the one or two things that clicked, or that surprised me.
**Surprised / stuck:** dead ends, bugs, things that did not work.
**Hypothesis (if testing):** what I predicted before running it, and the result.
**Decisions:** any scope or design change, and why.
**Next:** the single next action.
**LinkedIn seed:** a sentence I might turn into a post.
```

---

## 2026-06-19 | Phase 0 | Project kicked off and scoped
**Did:** Defined the project. Chose asset class (crypto), strategy family (cross-sectional momentum, benchmarked against time-series momentum), execution path (exchange API via CCXT, candidate venue Kraken), and capital plan ($10k of own risk capital, phased in after paper validation). Wrote the charter, the phased roadmap, and the resource list.
**Learned:** The academic picture is more interesting than "momentum works." The strongest recent paper (Han, Kang & Ryu, 2024) finds cross-sectional momentum in crypto largely dies after realistic transaction costs, while time-series/trend momentum survives. That reframes the whole project from "harvest an edge" to "test whether a textbook edge survives reality," which is both more honest and a better story.
**Surprised / stuck:** Nothing yet. Noted one practical gotcha for later: Kraken's REST OHLC endpoint only returns about 720 recent candles, so deep history needs the downloadable archives or the trades endpoint.
**Decisions:** Long-only, spot only, no leverage or derivatives to start (earn complexity later). Weekly rebalance to keep turnover and costs down. One strategy family at a time.
**Next:** Phase 0 setup: Python environment, read-only API keys, and a CCXT "hello world" that pulls live prices for ~5 assets.
**LinkedIn seed:** "I am building a real automated crypto trading system with $10k of my own money. Post 1: why my goal is not to make money fast, but to find out whether a famous edge actually survives transaction costs."

---

<!-- New entries go below this line -->

## 2026-06-26 | Phase 0 | Environment verified, public repo live
**Did:** Stood up the Python environment (`.venv`, `pip install -r requirements.txt`; ccxt 4.5.60). Ran `phase0_hello.py` against Kraken public data: connected to 1,506 markets and pulled a live bid/ask/spread/volume table plus the fee schedule. Ran the secret-hygiene check (`.gitignore` excludes `.env`, `.env.*`, `data/raw/*`, `data/processed/*`, `logs/*`; confirmed via `git check-ignore`; no key material on disk or staged). Made the clean initial commit and pushed `main` to a public GitHub repo (`crypto-momentum-xmom`). No license (per decision); added topics quant, crypto, momentum, algorithmic-trading.
**Learned:** The numbers that drive everything downstream are small but real. Live spreads on the majors are tiny (BTC 0.0002%, ETH 0.0006%) but the fees dwarf them: Kraken charges maker 0.25% / taker 0.40%. A taker round-trip is ~0.80% before spread and slippage. That fee, not the spread, is the wall a weekly-rebalanced cross-sectional signal has to clear.
**Surprised / stuck:** No venue error: Kraken responded fine from this location, so no fallback exchange was needed. Minor harness quirk: a `fatal: bad revision 'HEAD'` line appeared before the first commit existed (git bookkeeping with no HEAD yet); filtered out of the saved log and gone after the initial commit.
**Hypothesis (if testing):** Not testing a signal yet. Prior from the literature: cross-sectional crypto momentum struggles to survive ~0.80%+ round-trip costs at weekly turnover. Today's measured fees make that concrete.
**Decisions:** Lock Kraken as the Phase 0 candidate venue (transparent fees, US-accessible, responded live). No license on the public repo for now (can add later).
**Next:** Phase 0.4: create READ-ONLY Kraken API keys, store them in a local `.env` (never committed), and confirm an authenticated private call (e.g. balance) works.
**LinkedIn seed:** "Before writing a single line of strategy code, I measured what it actually costs to trade. The spread on Bitcoin was 0.0002%. The exchange fee was 2,000x larger. That gap is the whole game."

### Phase 0 live snapshot (Kraken, 2026-06-26)
```
PAIR                 BID           ASK   SPREAD %     24H VOL (USD)
-------------------------------------------------------------------
BTC/USD      59,771.8000   59,771.9000     0.0002       279,948,574
ETH/USD       1,550.6300    1,550.6400     0.0006        70,204,850
SOL/USD          67.9600       67.9800     0.0294        31,001,798
XRP/USD           1.0293        1.0298     0.0456        39,014,986
LTC/USD          41.1800       41.1900     0.0243         2,690,341

Fees: maker 0.0025 (0.250%)  |  taker 0.004 (0.400%)
```
(Live order-book snapshot; numbers move tick-to-tick. Full output saved to `logs/phase0_output.txt`, gitignored.)
