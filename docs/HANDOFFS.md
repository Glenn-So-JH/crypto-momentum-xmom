# Handoffs to Claude Code

This file is the durable record of work handed from the architect/planner (Claude, in Cowork) to the execution agent (Claude Code), which writes/runs code and owns the GitHub repo.

**Convention.** Each handoff has: an ID and date, a goal, the context Claude Code needs, a numbered task list, explicit acceptance criteria, and a "report back" section. Claude Code should append a short result note under each handoff when done, and add a dated entry to `PROGRESS_LOG.md`.

**Repo:** public from day one. **Auth:** GitHub already configured. **Golden rule:** no secret ever enters git. Keys live only in `.env` (gitignored). Verify before every push.

---

## Handoff #1  -  2026-06-26  -  Initialize public repo + verify Phase 0 environment

### Goal
Turn the existing `crypto-momentum/` scaffolding into a public GitHub repo, prove the Phase 0 environment works by running the live-price script, and commit the result. Do NOT write new strategy code yet.

### Context
- Working dir: `/Users/glennso/Documents/Claude/Projects/Quant Projects/crypto-momentum`
- The folder may already contain a local `.git` (init'd during scoping). Reuse it or re-init as needed.
- Scaffolding already present: `README.md`, `requirements.txt`, `.gitignore`, `.env.example`, `phase0_hello.py`, and `docs/` (charter, roadmap, resources, setup, this file), plus a `PROGRESS_LOG.md`.
- Target exchange: Kraken. The script uses public data only (no keys required).

### Tasks
1. **Secret-hygiene check FIRST (blocking).** Confirm `.gitignore` excludes `.env`, `.env.*`, `data/raw/*`, `data/processed/*`, and `logs/*`. Run `git status` and confirm no `.env` or key material is staged or tracked. If any secret is tracked, stop and fix before continuing. The repo is public.
2. **Python environment.** Create `.venv`, activate it, `pip install -r requirements.txt`. Report the installed `ccxt` version.
3. **Run the Phase 0 script.** Execute `python phase0_hello.py`. Capture the full output. Save a copy to `logs/phase0_output.txt` (gitignored, fine). If Kraken returns a network/geolocation error, note it and report back; do not silently switch exchanges.
4. **Create the public GitHub repo.** Name suggestion: `crypto-momentum-xmom` (user may override). Set a one-line description: "Systematic crypto cross-sectional momentum: a rigorously documented personal quant project." Add remote, push `main`.
5. **Optional but recommended.** Add an MIT `LICENSE` and a short repo description/topics (quant, crypto, momentum, algorithmic-trading). Ask the user before adding a license if unsure.
6. **Commit + log.** Make a clean initial commit ("Phase 0: project scaffolding, charter, roadmap, hello-world data script"). Append a dated entry to `PROGRESS_LOG.md` summarizing what was set up and pasting the key Phase 0 output numbers (spreads + fees).

### Acceptance criteria
- Public GitHub repo exists and contains the scaffolding, with NO `.env` or secrets in history.
- `phase0_hello.py` ran and produced a live bid/ask/spread/fee table (or a clearly-reported venue error).
- `PROGRESS_LOG.md` has a new dated Phase 0 entry.

### Report back (paste to the architect / into Cowork)
- The live output table from `phase0_hello.py` (the actual bid/ask/spread/volume numbers and Kraken's maker/taker fees).
- The public repo URL.
- Any errors hit and how they were resolved.

These numbers matter: the architect will use your real spreads and fees to set the transaction-cost assumptions for the Phase 3 backtest.

<!-- Claude Code: append your result note here -->

### Result note (Claude Code, 2026-06-26)
**Status: DONE.** All acceptance criteria met.
- **Secret hygiene:** `.gitignore` excludes `.env`, `.env.*`, `data/raw/*`, `data/processed/*`, `logs/*` (verified with `git check-ignore`). No `.env` on disk, no key material staged or tracked. Repo is safe to be public.
- **Environment:** `.venv` created; `pip install -r requirements.txt` succeeded on Python 3.14.5. **ccxt version: 4.5.60.**
- **Phase 0 run:** `phase0_hello.py` connected to Kraken (1,506 markets), printed a live bid/ask/spread/volume table and the fee schedule. **No venue/geo error** (Kraken responded; no fallback needed). Full output saved to `logs/phase0_output.txt`. Live fees: **maker 0.25% / taker 0.40%** (taker round-trip ~0.80% pre-spread/slippage). Snapshot pasted into `PROGRESS_LOG.md`.
- **Repo:** public GitHub repo `crypto-momentum-xmom` created, `main` pushed. Topics: quant, crypto, momentum, algorithmic-trading. **No license** (per user decision).
- **Commit:** clean initial commit `Phase 0: project scaffolding, charter, roadmap, hello-world data script`.

---

## Master brief run  -  2026-07-02  -  Stages A to D (autonomous)

### Stage A result note (Claude Code, 2026-07-02)
**Status: GATE PASSED.**
- Funnel: 637 enumerated Kraken USD spot pairs, 20 excluded (stablecoins/fiat/commodity tokens), 617 fetched with 0 failures, 132 ever pass the $1M/day point-in-time screen, 23 current members.
- Depth: panel 2019-01-01 to 2026-07-01; 391 weekly observations (previously ~104), 363 post-warmup (previously ~75). Sharpe SE improves from ~0.83 to ~0.38.
- Kraken OHLCVT archives are Google-Drive-only (not scriptable), so the authorized fallback was used: Binance deep history, spliced per coin only when overlap return correlation >= 0.98 over >= 60 days (153 spliced, median corr 0.9950; all rejections recorded in provenance.csv).
- Material issue found and fixed: raw Binance volumes (10-50x Kraken) inflated pre-splice universe breadth and created an artificial ~120 to ~28 membership cliff at the splice boundary. Pre-splice volumes are now scaled per coin by the overlap venue share (median 0.019). Prices never touched. Stated as a documented proxy assumption in research/stage_a_data_report.md.
- Tests: 55 passed, including point-in-time screen invariance and splice acceptance/rejection/scaling.
- Full gate report: research/stage_a_data_report.md.

### Stage B result note (Claude Code, 2026-07-02)
**Status: GATE PASSED.**
- Engine: vectorized, sacred t to t+1 shift, dormant cost hook (multiplicative, charged on traded notional), turnover on target weights, inception funding excluded by convention. Drift-aware extension with no-trade bands included for Phase 2 (exercised by Stage D tests).
- Metrics: the docs/03 section 7 table verbatim, annualization 365, ddof=1, hit rate and time-in-market conditioned on lagged gross exposure.
- Gate tests all pass: BTC buy-and-hold reproduction (rtol 1e-10, real panel AND synthetic), look-ahead guard (future perturbation cannot change past returns; a peeking strategy earns nothing extra), no-leverage and long-only and ghost-position guards, cash-returns-zero, metrics on hand-computed synthetic series.
- Smoke run on the real panel (2019-07-22 to 2026-07-01): S1 BTC CAGR 28.8%, Sharpe 0.72, maxDD -76.6%, turnover 0; S2 equal-weight CAGR 8.7%, Sharpe 0.53, maxDD -83.6%, turnover 462%/yr. S1 matches the real BTC path elementwise. S2 turnover is far above the spec's 10-50% guess: real membership churn around the $1M bar (marginal names flip weekly), not an accounting bug; carried into Stage C observations.

### Stage C result note (Claude Code, 2026-07-02)
**Status: GATE PASSED.** All ten required runs executed gross plus net at 25/50 bps; 30 ledger rows appended; all six programmatic gate checks green (S1 reproduces BTC elementwise; turnover ordering S5 > S4 > S2 > S1; time-in-market split; S6 not best).
- Headline: the cost wall. Net-50 Sharpe: S3b 1.03, S3a 0.78, S1 0.73, S2 0.47, S4a 0.45, S5b 0.32, S5c 0.25, S5a 0.16, S4b 0.07, S6 -0.26. Every XS variant lost absolute money over 7 years even gross; only the S3 BTC trend filters beat buy-and-hold risk-adjusted.
- One predicted ordering violated and explained after investigation: S4 TSMOM drawdowns are DEEPER than equal-weight (equal-weighted holder concentration, 15% of weeks in 1-2 coins, plus the 2022 stair-step bear whipsawing the trailing brake). Motivates the Phase 2 overlays directly.
- Deliverables: research/PHASE1_RESULTS.md (tables, gate checks, observations, thin-universe warning, power statement), research/figures/phase1_equity.png and phase1_drawdown.png, research/TRIALS_LEDGER.csv.

### Stage D result note (Claude Code, 2026-07-02)
**Status: GATE PASSED, with a recorded surprise.**
- Head-to-head net of 50 bps: BASE_21 Sharpe 0.84 / CAGR 18.9% / maxDD -40.0%; CHAL_21 Sharpe 0.95 / CAGR 21.4% / maxDD -37.9%. Both far above the S1 (0.73) and S2 (0.47) benchmarks. Vol target and gate worked: ~24% realized vol, book fully in cash through the four 2022 bear quarters.
- Verdict by the registered rule: BASE CASE kept. The 0.11 Sharpe gap is a statistical tie on this window (SE ~0.38) and ties go to the simpler book; under the strict fold-clause reading the challenger also falls short (11 of 23 including both-flat folds). The registered PREDICTION missed: XS with shared overlays did not lose. Recorded prominently; challenger queued for a registered E5 experiment.
- Base success criteria 7/7. Neighbor plateau 0.83 to 1.06 net-50 Sharpe, no sign flips (gate=100 neighbor outperformed and was deliberately NOT selected). Single-name dependence healthy: top coin 12% of positive P&L. DSR 0.962 at K=12, labeled provisional with caveats.
- Deliverables: research/PHASE2_RESULTS.md, research/figures/phase2_head_to_head.png, 15 ledger rows (45 total in the ledger).
- Hard-stop compliance: no keys created or used, no orders, nothing deployed. Backtests and reports only.

---

## Handoff #7 run  -  2026-07-03  -  Discovery data + alpha sandbox + regime/OOS levers

### WS1 result note (Claude Code, 2026-07-03)
**Status: DONE.** Discovery panel: Binance single-source daily closes from the public archive bucket (delisted pairs retained: LUNA, FTT, ANC, BTT in-panel), 593 coins, 2017-08-17 to 2026-07-02, 463 weekly observations, breadth median 64 / max 260 at the generous $5M/day point-in-time bar. No splice, no reconciliation, no volume proxy: seam-free single source. Kraken tradability explicitly deferred to a later survivors-only gate.
- Data integrity work the seam-free claim required: a corporate-actions split list (config.DISCOVERY_SYMBOL_SPLITS, 8 coins) severing symbol-reuse seams (LUNA's Terra 2.0 relist printed a fake +17.7M% day; COCOS/DREP/QUICK/SUN/BNX/VIDT/STRAX redenominations and swaps), plus halt-splitting for >30d holes and exclusion of bare BULL/BEAR leveraged tokens. Post-fix scan: the only remaining >|2.3| log-return events are LUNA's REAL May 2022 crash days, kept on purpose.
- Ladder + Phase 2 re-run GROSS on the broad panel (research/DISCOVERY_BASELINES.md): the wide cross-section HURT cross-sectional momentum (S5a top-3 +0.37 thin -> -0.23 broad; S5c quintile stays +0.25); trend filters unchanged (S3b +1.12); Phase 2 overlays survive (+0.64 both, maxDD ~-50%); base-vs-challenger is a dead heat on this panel, so the Stage D tie-to-base verdict stands. Regime tables: edge is bull-conditional; 2025+ era negative for both candidates.
- Tests 66 green. Reproducible via `make discovery`.

### WS3 result note (Claude Code, 2026-07-03)
**Status: DONE.** Config levers in one block (xmom/config.py): OOS_VAULT_START = 2025-01-01, walk-forward settings (52-week initial train, 13-week folds), regime definitions (trend asset/SMA + named eras). Enforcement is structural, not honor-system: validation.playground_index / vault_index split the calendar, and run_alpha.py hands alphas ONLY pre-vault data during tuning (the vault is unseeable, not merely off-limits); scoring it requires an explicit --vault flag, is labeled a one-look final exam, and is ledger-logged as such. Tests: vault split exhaustive/disjoint, fold no-leak, plus the earlier walk-forward suite. Playground = 2,742 daily rows (2017-08-17 to 2024-12-31); vault = 548 daily rows (~78 weekly observations).
