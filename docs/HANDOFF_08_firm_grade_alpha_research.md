# Handoff #8: Firm-grade market-neutral alpha research

Context: the project is reframed as a quant-researcher firm simulation (see `docs/08_FIRM_SIM_CHARTER.md`). Goal of this handoff: build the research stack to discover a STABLE of market-neutral, weakly-correlated trend/momentum alphas and combine them. Builds on the long-short engine and the clean broad Binance discovery dataset from Handoff #7.

Hard stop unchanged: research and reports only. No keys, no orders, nothing deployed. Shorting is ASSUMED available (abstracted perps); execution and instrument choice are out of scope (abstracted to a cost/funding model). Commit each workstream separately with a `PROGRESS_LOG.md` entry and a `docs/HANDOFFS.md` result note.

Read first: `docs/08_FIRM_SIM_CHARTER.md`, `docs/04_VALIDATION_METHODOLOGY.md`, `research/DISCOVERY_BASELINES.md`.

## Workstream A: Market-neutral construction + sizing engine
1. **Beta-neutral long-short.** Construct each alpha's book to be neutral to the crypto market factor (BTC), not merely dollar-neutral. Estimate each coin's beta to a market proxy (BTC or an equal-weight index) on a rolling, look-ahead-safe window, and build long-short weights so net market beta is approximately zero.
2. **Sizing (chosen approach):** per-name inverse-volatility sizing, a covariance/factor risk model so correlations are respected (a simple market + optional sector factor model is fine), a portfolio volatility target (config default 15% annualized for a market-neutral book, tunable), and per-name plus gross-exposure caps. No full convex optimizer yet; an inverse-vol / equal-risk construction is the target.
3. **Costs and funding OFF for discovery** (gross), with a dormant realism-layer hook to charge fees + a funding rate on positions later. Keep it a one-line switch.

## Workstream B: The alpha stable
Implement a set of DISTINCT trend/momentum alphas, each producing a market-neutral target book via Workstream A. Aim for signals that are economically different, not the same idea reparametrized:
- time-series trend at multiple horizons (e.g. 10, 30, 90 day),
- cross-sectional momentum (rank) at a couple of horizons,
- risk-adjusted / Sharpe momentum (return divided by vol),
- breakout / Donchian channel,
- moving-average distance or MACD-style,
- momentum acceleration (change in the momentum signal),
- (optional, separate sleeve) funding/term-structure momentum, clearly labeled as needing perp data.
Each alpha: raw signal, cross-sectional z-score, beta-neutral long-short weights.

## Workstream C: Alpha analytics (the core deliverable)
1. **Standalone performance** per alpha: gross risk-adjusted metrics (Sharpe, vol, maxDD, turnover), regime-sliced (bull/bear/chop), plus a cost/funding sensitivity note.
2. **Market-neutrality check:** realized beta to BTC for each alpha and the combined book, confirm ~0.
3. **Correlation matrix** of the alpha daily return streams (a heatmap). This is central: identify which alphas are weakly correlated (say |rho| < 0.5) and therefore diversifying.
4. **Selection:** pick a weakly-correlated subset, with the reasoning recorded.

## Workstream D: Combination
1. Combine the selected alphas into one market-neutral book (equal-risk / inverse-vol blend to start; note an optimizer as future work).
2. Report combined Sharpe versus each standalone alpha, quantifying the diversification benefit (this is the money shot: combined Sharpe should exceed the best individual).
3. Full validation: walk-forward, deflated Sharpe using the TOTAL trial count from the ledger, OOS vault untouched until a final single evaluation, regime tables.

## Deliverable
`research/ALPHA_RESEARCH_REPORT.md`, recruiter-facing quality: the alpha stable and what each is, the correlation heatmap, per-alpha and combined risk-adjusted performance, market-neutrality evidence, the diversification result, and an honest limitations section (small-sample caveat, bull-conditionality, gross-only). Figures committed under `research/figures/`.

## Report back to the owner
- The per-alpha table (Sharpe, beta-to-BTC, turnover), gross and regime-sliced.
- The alpha correlation matrix and which subset was selected as weakly correlated.
- Combined-book Sharpe vs best individual (the diversification gain).
- Confirmation the book is market-neutral (beta ~0) and all validation discipline held.
