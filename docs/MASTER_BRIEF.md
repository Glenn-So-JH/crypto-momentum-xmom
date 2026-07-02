# Master Build Brief (autonomous run)

This brief lets Claude Code build the project's research pipeline end to end in one autonomous run, using the reference docs in this repo. It bundles Handoffs #4, #5, #6 and Stage 1C, and optionally the Phase 2 base case. Read the referenced docs off disk as you go; do not ask the owner to paste them.

## Mission

Build and validate the XMom crypto momentum research pipeline: deep+wide data, a trustworthy backtest engine, the classic-strategy validation ladder, and (optionally) the Phase 2 base-case strategy. Produce honest results reports. The goal is a pipeline the owner can trust, not a profitable strategy. "The data says no" is a successful outcome and must be reported plainly if true.

## Hard stop (do NOT cross without the owner)

- Do NOT create, request, or use exchange API keys.
- Do NOT place orders, connect to a live or paper trading account, or move any money.
- Do NOT deploy anything that trades. Stop at backtests and reports.
- If a step seems to require any of the above, STOP and report instead.

## How to work

1. Read these first and treat them as binding: `docs/00_PROJECT_CHARTER.md`, `docs/DECISIONS.md`, `docs/03_STRATEGY_SPECS.md`, `docs/04_VALIDATION_METHODOLOGY.md`, and for the optional Phase 2 part `docs/05_PHASE2_DESIGN.md`. Supporting: `docs/01_ROADMAP.md`, `docs/02_PHASE1_DESIGN.md`, `docs/RESEARCH_crypto_momentum.md`.
2. Commit and push after each stage with a clear message. Append a dated entry to `PROGRESS_LOG.md` and a result note to `docs/HANDOFFS.md` per stage.
3. Keep the working tree clean between stages. Commit the outstanding Stage 1A tree and all my docs first.
4. At each STAGE GATE below, if the gate fails or something is ambiguous or surprising, STOP and report rather than pushing on. Otherwise continue to the next stage.

## Non-negotiable guardrails (these prevent a beautiful wrong answer)

- **No look-ahead.** Weights decided from data through close of day t apply to returns t to t+1 (explicit shift). Include a test that proves a future price cannot change a past weight.
- **No survivorship shortcut.** Universe is point-in-time liquidity-screened; never use today's membership for past dates.
- **Annualize with 365**, not 252 (crypto trades daily).
- **Costs (DEC-002).** Report gross, plus net at 50 bps/side (deciding) and 25 bps/side (optimistic). Never judge a strategy on gross alone.
- **Count every trial.** Maintain an append-only `research/TRIALS_LEDGER.csv` logging every parameter combination tested. Apply the deflated-Sharpe reasoning from `04_VALIDATION_METHODOLOGY.md`.
- **Small-sample honesty.** State the number of weekly observations and remember: nothing under roughly 1.4 pre-deflation Sharpe is distinguishable from zero here. Do not oversell any result.
- **No secrets in git.** Data and logs stay gitignored; never commit keys.
- **Long-only, no leverage.** Weights >= 0, sum <= 1.

## Build sequence and stage gates

**Stage A: Deep + wide data** (Handoffs #5 + #6).
Auto-enumerate all liquid Kraken USD spot pairs (drop stablecoins/fiat), extend history to 5+ years via Kraken's downloadable OHLCVT archives (fallback: a reputable secondary daily source, clearly labeled and reconciled over the overlap), stitch renames (MATIC to POL), re-run the point-in-time liquidity screen.
GATE: report per-coin start dates, total daily and weekly observations (before vs the old ~104 weekly), and the universe funnel. Data-quality and look-ahead tests green.

**Stage B: Engine + metrics** (Handoff #4).
Vectorized engine with the sacred t to t+1 lag, dormant cost hook (default 0), weekly rebalance, turnover tracking. Metrics module (365 annualization). Tests: buy-and-hold equals BTC, look-ahead guard, no-leverage guard, cash returns zero, metrics correctness on a synthetic series.
GATE: all engine tests pass. Smoke-run buy-and-hold BTC vs equal-weight universe and report metrics.

**Stage C: Validation ladder** (Stage 1C, per `03_STRATEGY_SPECS.md`).
Implement and run all six classic strategies exactly as specified: buy-and-hold, equal-weight, MA trend filter, time-series momentum, cross-sectional momentum, short-term reversal. Run gross, and net at both cost levels. Produce `research/PHASE1_RESULTS.md` with a comparison metrics table, equity-curve and drawdown PNGs, and written observations comparing actual behavior to the predicted ordering in the spec. Log every run in the trials ledger.
GATE: results are internally consistent (buy-and-hold matches BTC; predicted ordering roughly holds or deviations are explained). Report the table and charts.

**Stage D (optional): Phase 2 base case** (per `05_PHASE2_DESIGN.md`).
Only if Stages A to C pass cleanly. Build the base case: long-only time-series momentum (21d lookback) + BTC 200d regime gate + inverse-vol sizing, 30% vol target (DEC-003), weekly rebalance with no-trade bands. Run the cross-sectional top-N challenger head to head. Report both, net of costs, with the walk-forward and trial-count discipline. Do not tune extensively; run the pre-registered defaults and report honestly.
GATE: report the head-to-head, gross and net, with an explicit statement of whether either clears the bar or the data is inconclusive.

## Final deliverables

- Clean, committed, reproducible repo (one command rebuilds data; one runs the backtests).
- `research/PHASE1_RESULTS.md` (and a Phase 2 section if Stage D ran) with real metrics tables, equity curves, and honest conclusions including limitations.
- Updated `PROGRESS_LOG.md`, `HANDOFFS.md` result notes, and `research/TRIALS_LEDGER.csv`.
- A final report-back to the owner: what was built, the headline results net of costs, how many trials were run, the weekly-observation count, and a plain-English verdict on whether anything looks worth pursuing or whether the data says no.

## When in doubt

Prefer stopping and reporting over guessing. A partial run with an honest gate failure is more valuable than a complete run that hides a problem.
