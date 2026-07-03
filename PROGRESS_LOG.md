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

---

## 2026-06-30 | Phase 1 (Stage 1A) | Data layer: fetch, clean, point-in-time universe
**Did:** Built the data layer as a small importable library (`xmom/`: `config`, `data`, `quality`, `universe`) plus two runnable scripts (`phase1_fetch_data.py`, `phase1_build_universe.py`). Fetched daily OHLCV for the 22-coin Kraken USD seed universe (721 candles each, 2024-07-10 to 2026-06-30), ran quality checks, and built a point-in-time liquidity screen (trailing-30d median dollar volume >= $1M). Wrote 9 unit tests (synthetic data, no network) covering dedup, gap-fill, outlier flagging, rename stitching, and the screen, all green. Data-quality note committed at `research/phase1a_data_quality.md`; raw/processed data stays gitignored and regenerable.
**Learned:** A liquidity screen is a real filter here, not a rubber stamp. Kraken USD-pair volumes are far thinner than the headline global numbers: only 12 of 22 candidates currently clear a $1M/day trailing-median bar (BTC ~$137M/day at the top, ETC ~$72k at the bottom, a clean monotonic ranking). The point-in-time discipline is the whole game against survivorship bias, and it is provable: a unit test confirms membership at date t is identical whether or not future data is visible.
**Surprised / stuck:** Confirmed Kraken's REST cap dead-on: every coin returned exactly 721 candles regardless of how far back I asked, so Phase 1 is locked to one ~2-year window (deep history deferred to the archive download, by design). Two seed names did not fetch: MKR/USD is absent from this Kraken market list, and MATIC/USD is gone because Polygon now lists only as POL (so the rename-stitch had nothing to merge, but the tested machinery is ready for the next rename). One genuine quality finding: POL has 19 zero-volume days (thin book), which the screen correctly turns into "out of universe."
**Hypothesis (if testing):** Not testing a signal yet (the engine does not exist). Recorded prior for Stage 1C: with median ~13 tradable names, a top-quantile cross-sectional portfolio will hold ~3-4 coins, so turnover (and the Phase 0 fee wall of ~0.80% taker round-trip) will bite hard once costs switch on in Phase 3.
**Decisions:** Added an `xmom/` library package (not in the original folder sketch) so the engine and tests can import the same code; documented in the README. Liquidity bar set at $1M/day trailing-30d median as a transparent, tunable Phase-1 default (Phase 2 may switch to top-N or add USDT pairs). Gaps are forward-filled with volume forced to 0 (treat the unknown as illiquid, never as liquid).
**Next:** Stage 1B: the vectorized backtest engine with the sacred t->t+1 lag, the metrics module, and the two non-negotiable tests (100%-BTC buy-and-hold reproduces BTC's path; look-ahead guard refuses a cheating strategy).
**LinkedIn seed:** "Before any strategy, I built the universe. The lesson: on my actual exchange, only 12 of 22 'liquid' coins clear a $1M/day bar, and the gap between the top coin and the bottom is 2,000x. You cannot trade an average; you trade what is actually there on the day."

---

## 2026-07-02 | Phase 1 (Stage A) | Deep + wide data: 617 coins, 7.5 years, venue-honest liquidity
**Did:** Rebuilt the data layer per the master brief. Auto-enumerated all 637 active Kraken USD spot pairs (DEC-005), excluded 20 non-signal assets (15 stablecoins, 3 fiat, 2 commodity tokens), fetched all 617 candidates with zero failures. Kraken's OHLCVT archives are only served through Google Drive behind a browser, so deep history uses the documented fallback: Binance daily candles back to 2019-01-01, spliced only where overlap return correlation is at least 0.98 over at least 60 shared days (153 coins spliced, median correlation 0.9950; 80 rejected on correlation, 19 on short overlap). Kraken rows authoritative everywhere they exist. Panel: 2019-01-01 to 2026-07-01, 391 weekly observations (was 104). Full provenance table committed to the gate report.
**Learned:** The subtle killer was volume basis, not prices. Raw Binance volumes run 10 to 50x Kraken's, so the liquidity screen admitted ~120 names pre-splice and then collapsed to ~28 in three weeks when the trailing window rolled onto Kraken-native volumes: an artificial universe cliff created by the data seam, not by markets. Fixed by scaling each coin's pre-splice volumes (never prices) by its overlap venue share (median 0.019: Kraken really is ~2% of Binance). Breadth is now continuous through the boundary and tells the real story: ~4 liquid names in 2019, 36 at the 2021 peak, 21 in the 2022 bear, 23 today.
**Surprised / stuck:** How many splice candidates failed reconciliation: 80 coins had overlap return correlation below 0.98 against Binance (some as low as 0.16). Thin Kraken books genuinely print different daily closes than Binance. Those coins stay Kraken-only rather than importing questionable history.
**Hypothesis (if testing):** Not a signal test. Registered expectation for Stage C: with the 2022 bear now inside the window, trend-filtered strategies (S3, S4) should show their drawdown protection working, which the old 2024-2026 window never really tested.
**Decisions:** (1) Volume-basis harmonization as above, stated proxy assumption documented in the gate report, reversible via config. (2) $1M/day bar unchanged (DEC-005). (3) Ambiguous rebrands not stitched (only MATIC to POL and FTM to S); others stay Kraken-only and are listed. (4) USTC excluded as a stablecoin by intent even though it floats now.
**Next:** Stage B gate: run the engine smoke test (buy-and-hold BTC vs equal-weight) on the new panel.
**LinkedIn seed:** "I extended my crypto dataset from 2 to 7.5 years and the hardest bug was not in the prices. It was in the volumes: my two data sources disagreed by 50x, and the splice quietly invented a liquidity crash that never happened. Here is how a universe screen can lie to you."

---

## 2026-07-02 | Phase 1 (Stage B) | The engine earns its trust
**Did:** Built the vectorized backtest engine (sacred t to t+1 lag, dormant cost hook, target-weight turnover, long-only and no-leverage guards that raise loudly) plus the metrics module (docs/03 table verbatim, 365 annualization). Wrote the five gate tests from the master brief and passed all of them, including: buy-and-hold reproduces BTC exactly (synthetic and real panel, rtol 1e-10), a strategy that peeks at tomorrow gains nothing, future price perturbations cannot change past returns, cash weeks are exactly flat, and metrics match hand-computed values. Also built the drift-aware engine extension with no-trade bands for Phase 2. Smoke run on the real panel done.
**Learned:** The window now contains a real bear market and it shows: buy-and-hold BTC from 2019-07 carries a 76.6% max drawdown, and the equal-weight universe basket carries 83.6% with a CAGR of only 8.7% against BTC's 28.8%. Diversification across alts was not protection, it was extra beta.
**Surprised / stuck:** Equal-weight turnover came out at 462% one-sided per year against the spec's 10 to 50% guess. Cause: with 132 ever-liquid names, marginal coins oscillate around the $1M/day bar weekly, and every membership flip plus the 1/n re-scale trades the book. The accounting is unit-tested; the surprise is real behavior of an absolute-floor screen on a wide universe, worth remembering when costs switch on.
**Hypothesis (if testing):** Registered before Stage C: predicted orderings per docs/03 section 8 (S3/S4 shallowest drawdowns, S1 < S3 < S2 < S4 < S5/S6 turnover, S6 weakest).
**Decisions:** Inception funding trade excluded from turnover and costs for all strategies (compared on ongoing trading, not day-one buy-in); documented in the engine docstring.
**Next:** Stage C: run the ten-strategy validation ladder, gross and net.
**LinkedIn seed:** "My backtest engine passed the test that matters: a strategy that literally knows tomorrow's winner cannot make money in it. If your backtester does not have that test, it is not a measuring instrument, it is a wish machine."

---

## 2026-07-02 | Phase 1 (Stage C) | The classics, reproduced: costs are the story
**Did:** Ran the full ten-run validation ladder (S1 buy-and-hold, S2 equal-weight, S3a/b MA filters, S4a/b TSMOM, S5a/b/c XS momentum, S6 reversal) on the 7-year panel, gross plus net at 25 and 50 bps per side. All six gate checks passed. Results, table, charts, and observations in research/PHASE1_RESULTS.md; all 30 runs logged in research/TRIALS_LEDGER.csv.
**Learned:** The cost wall is real and it is exactly where the literature said it would be. Gross-to-net50: XS momentum Sharpe 0.37 to 0.16, reversal 0.15 to -0.26, while the low-turnover BTC trend filter barely notices (1.08 to 1.03). Turnover above 2,000% a year at 50 bps a side costs about 20% of the book annually, the size of the whole documented momentum premium. Also: only the S3 trend filters beat buy-and-hold BTC risk-adjusted; every XS variant lost money in absolute terms over 7 years even gross.
**Surprised / stuck:** One registered prediction was violated: TSMOM drawdowns (-85.7% at L=90) came out DEEPER than equal-weight (-83.6%). Investigated before crediting: equal-weighting the holders concentrates the book (15% of weeks were 100% in 1 or 2 coins), and the 2022 stair-step bear whipsawed the trailing-return brake back into dying alts on every relief rally. The engine is unit-test-pinned; the behavior is the strategy's true shape and precisely motivates the Phase 2 overlays (vol sizing, name cap, portfolio gate).
**Hypothesis (if testing):** The registered orderings from docs/03 section 8: turnover and time-in-market orderings held exactly; drawdown ordering held except S4 as above; S6 weakest as predicted.
**Decisions:** None new. Universe churn (S2 at 462%/yr turnover against a 10-50% guess) is noted as a real property of an absolute-floor screen on a wide universe, to revisit only through registered experiments.
**Next:** Stage D: the pre-registered base case (gated, vol-sized TSMOM-21) against the XS top-3 challenger, decided net of 50 bps.
**LinkedIn seed:** "I reproduced six classic crypto strategies on 7 years of data. The one that made the most money was not momentum. It was the boring 100-day trend filter on Bitcoin, and the reason is fees: at real retail costs, 2,000% turnover donates your entire edge to the exchange."

---

## 2026-07-02 | Phase 2 (Stage D) | Base case survives; challenger surprises; ties go to simple
**Did:** Ran the pre-registered head-to-head through the drift-aware engine with 20% no-trade bands: BASE_21 (TSMOM-21 + BTC 200d gate + inverse-vol with 25% cap + 30% vol target) vs CHAL_21 (XS top-3, identical overlays), plus BASE_14 and six registered robustness neighbors. 15 new ledger rows (45 total). Full report with fold table, DSR, and verdict in research/PHASE2_RESULTS.md.
**Learned:** The overlays, not the signal, drove the risk numbers: both candidates landed near 24% vol and -38 to -40% maxDD (vs BTC -76.6%), and the BTC gate held the whole book in cash through four consecutive quarters of the 2022 bear. Net-50 Sharpe: base 0.84, challenger 0.95, both far above equal-weight (0.47) and BTC (0.73).
**Surprised / stuck:** The registered prediction MISSED: the XS challenger did not lose net of costs, it nosed ahead (0.95 vs 0.84, and 11 of 18 decided folds). The gap is under a third of a Sharpe standard error on this window, so by our own rules it is a statistical tie, and the registered rule sends ties to the simpler base case. Recorded as a genuine surprise: with shared gate, vol sizing, and cap, the thin-universe XS penalty did not show up. Also: the gate=100 neighbor outperformed the chosen gate=200 (1.06 vs 0.84); left alone, because neighbors are registered as fragility probes, not a selection menu.
**Hypothesis (if testing):** Registered prediction vs outcome above. Base success criteria: 7 of 7 passed. DSR 0.962 (K=12) clears 0.95 but is labeled provisional (correlated trials, one regime cycle, kurtosis 12.5).
**Decisions:** Keep the base case as the named Phase 2 candidate with frozen parameters (L=21, gate=200, vol target 30%, cap 25%, band 20%, weekly). Challenger earns a future registered E5 experiment (TS+XS intersection), not adoption. No parameter changes from the robustness set.
**Next:** Phase 3: honest cost model (measured spreads and slippage, cost-sensitivity curve, breakeven and margin), then the docs/04 checklist toward paper trading.
**LinkedIn seed:** "My favorite strategy idea finally got its fair trial: pre-registered, costs on, walk-forward, every run counted. It fought the boring version to a statistical tie. The rule I wrote before running says ties go to boring. This is what doing it properly feels like."

---

## 2026-07-03 | Handoff 7 WS1 | Discovery dataset: broad, seam-free, and it flipped a hypothesis
**Did:** Built the second dataset, for signal discovery only: Binance single-source daily panel from the public archive bucket (which retains DELISTED pairs, so LUNA, FTT, ANC, BTT are in), 598 candidates enumerated, 593 fetched, full history per coin back to 2017-08. 3,242 days, 463 weekly observations, breadth median 64 and max 260 at the generous $5M/day point-in-time bar. Regime labels (BTC 200d trend + seven named eras) are first-class outputs. Re-ran the whole ladder and the Phase 2 head-to-head GROSS on it. Reports: discovery section in stage_a_data_report.md, results in research/DISCOVERY_BASELINES.md, 12 new ledger rows.
**Learned:** The handoff's hypothesis was that a wide cross-section would help XS momentum that the thin Kraken universe had been strangling. The data said the opposite: raw XS top-3 fell from gross Sharpe +0.37 (thin) to -0.23 (broad) with a near-total drawdown, because the top-3 of 200 liquid names is a rotating bag of freshly pumped microcaps. The quintile variant (13 to 52 holdings) stayed positive: within-basket diversification beats breadth. Meanwhile the Phase 2 overlay stack survived the harder test (+0.64 gross, maxDD -47%) and the regime tables say plainly that the edge is bull-conditional and has earned nothing net-new since 2023.
**Surprised / stuck:** Two data traps. First, symbol reuse: Binance's LUNAUSDT file is CONTINUOUS through Terra's death and rebirth, printing a fake +17,739,900% one-day return with no gap for a halt detector to catch; systematic |log return| scan plus case-by-case classification produced a documented corporate-actions split list (8 coins: relists, redenominations, token swaps), each split into separate assets. Real crash days with real volume (LUNA -94% and -99.97%, OM -84%) are deliberately kept. Second, bare BULL/BEAR (FTX 3x tokens) slipped past the leveraged-token filter and are now excluded.
**Hypothesis (if testing):** Registered hope: broad universe helps XS. Outcome: falsified for top-N concentration, partially supported for quintile construction.
**Decisions:** Two-dataset architecture is now explicit: Kraken execution panel (unchanged) for tradability, Binance discovery panel for signal research, gross-judged, with Kraken constraints deferred to a survivors-only gate. Corporate-actions list lives in config.DISCOVERY_SYMBOL_SPLITS, auditable in git.
**Next:** WS3 vault levers, then the WS2 alpha sandbox on this panel.
**LinkedIn seed:** "I widened my crypto universe from 23 coins to 260 expecting my cross-sectional momentum signal to finally breathe. It drowned instead: top-3 of a wide universe is just a pump-chasing machine. The version that held the top fifth survived. Concentration, not breadth, was the real variable."

---

## 2026-07-03 | Handoff 7 WS3 | The vault: out-of-sample data you cannot peek at
**Did:** Locked everything from 2025-01-01 onward into a one-look OOS vault, with the levers in a single config block (vault start, walk-forward train/fold lengths, regime definitions). The enforcement is structural: the alpha harness hands a signal only pre-vault data during tuning and plateau sweeps, so the vault is unseeable rather than merely off-limits. Scoring it requires an explicit flag, is labeled the final exam, and lands in the trials ledger as a declared look.
**Learned:** The playground is 2,742 daily rows and the vault is 548 (about 78 weekly observations). That vault alone has a Sharpe standard error near 0.8, so even the final exam can only catch disasters and gross overfitting, not certify an edge. Writing that down now prevents over-reading it later.
**Surprised / stuck:** Nothing; small workstream by design.
**Decisions:** Fixed reference baselines (the ladder, the frozen Phase 2 candidates) may be reported across the vault era since they are not tuned; anything editable in the sandbox never sees it.
**Next:** WS2: the alpha sandbox itself.
**LinkedIn seed:** "I put two years of my data in a vault my own tooling refuses to show me. The best out-of-sample discipline is not willpower, it is code that makes peeking impossible."

---

## 2026-07-03 | Handoff 7 WS2 | The alpha sandbox: one function, one command, no self-deception
**Did:** Built the discovery-first sandbox: research/my_alpha.py (edit one function with a documented weight contract) plus run_alpha.py / make alpha (gross headline, net-50 footnote, regime breakdown, parameter plateau sweep, walk-forward folds, BTC and equal-weight benchmarks, automatic trials-ledger logging, plain-English verdict in research/my_alpha_report.md). The harness enforces honesty structurally: it validates the weight contract, runs a look-ahead probe (hides the last ten weeks and fails the run if earlier weights change), withholds the OOS vault from tuning entirely, and counts every sweep combination in the ledger. Guide with three worked example ideas in docs/ALPHA_SANDBOX.md.
**Learned:** The out-of-the-box example (28d XS momentum, top quintile) is itself a lesson: gross Sharpe +0.68 on the playground versus BTC's +0.80, plateau stable, positive in only 11 of 23 folds, 2,173% turnover. The founding idea of this project, run on the cleanest broadest data we have, does not beat buy-and-hold before costs. The sandbox said so in one command, which is exactly what it is for.
**Surprised / stuck:** Nothing structural. K for the example family is already 13 after one command (12 sweep combos plus headline), which makes the multiple-testing cost of casual grid-widening viscerally obvious.
**Decisions:** Sandbox judges gross plus regime robustness on the discovery panel; Kraken costs and the thin universe stay a later survivors-only gate (per the revised handoff). Vault scoring only via an explicit --vault flag, logged as a declared look.
**Next:** Handoff #7 complete. Natural follow-ons: E5 (TS+XS intersection) as a registered sandbox run, and the Phase 3 cost model for the Phase 2 candidate.
**LinkedIn seed:** "I built a sandbox where testing a trading idea takes one function and one command, and where the tooling itself refuses to let me cheat: it hides the future, hides two years of out-of-sample data, and bills every parameter I try against my own significance. First finding: my founding idea does not beat buy-and-hold. Before fees."
