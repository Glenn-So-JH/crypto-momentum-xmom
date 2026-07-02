# Decision Log

Durable record of committed project decisions. Each has an ID, a date, the decision, and the rationale. Supersede rather than edit; note when a decision is revised.

---

**DEC-001 (2026-06-26): Base-case strategy is time-series momentum, not cross-sectional.**
The evidence-backed base case is long-only time-series (trend) momentum at a ~21-day lookback, gated by a BTC 200-day moving-average regime filter, sized by inverse volatility with a per-name cap, rebalanced weekly with no-trade bands. Cross-sectional top-N momentum (our original founding idea) becomes the *challenger*, run head to head to be falsified or kept. Rationale: the literature (Han, Kang & Ryu 2024 and others synthesized in `RESEARCH_crypto_momentum.md`) shows TS momentum is robust in crypto while XS momentum is weak after costs, and our thin universe (~13 names) further handicaps cross-sectional ranking. See `05_PHASE2_DESIGN.md`.

**DEC-002 (2026-06-26): Transaction-cost model for decisions is 50 bps per side.**
Backtests judge strategies on a deciding cost of 0.50% per side (Kraken taker 0.40% plus a slippage buffer for thin books at $10k), and report 0.25% per side (maker) as the optimistic bound, alongside gross. Rationale: costs and turnover are the make-or-break axis; academic papers assume ~15 bps and their results do not transfer to a retail Kraken account. See `04_VALIDATION_METHODOLOGY.md`.

**DEC-003 (2026-06-26): Default volatility target is 30% annualized, de-risk only.**
The base case targets ~30% annualized volatility, scaling positions down (never up, no leverage) when realized vol runs hot. Rationale: meaningfully calmer than holding crypto outright (~60 to 80% vol) while keeping real upside; encodes the owner's drawdown tolerance, not just evidence. Revisit if live drawdowns feel wrong.

**DEC-004 (2026-06-26): Extend history to 5+ years before Phase 2.**
Ingest Kraken's downloadable OHLCVT archives to extend daily history to 5+ years (adding the 2022 bear market) before starting Phase 2 signal work. Rationale: the current ~2-year window is only ~104 weekly observations, statistically too thin to confirm anything (Sharpe standard error ~0.71); more data and a bear regime is the single highest-value upgrade available. See `04_VALIDATION_METHODOLOGY.md`.

**DEC-005 (2026-06-26): Universe is auto-enumerated, not hand-curated.**
The tradable universe is built by programmatically enumerating all liquid Kraken USD spot pairs (stablecoins/fiat removed) and applying the point-in-time $1M/day liquidity screen, rather than a hand-picked seed list. USDT pairs are measured but not yet included. Rationale: removes selection bias; let the data decide. See Handoff #5.

**DEC-006 (2026-06-26): Validation discipline is mandatory before any capital.**
Every candidate strategy is subject to: an append-only trial ledger (count every variant tested), pre-registration of hypothesis and parameters before running, deflated Sharpe and walk-forward analysis, and gross-plus-net cost reporting. Given the small sample, no result under roughly 1.4 pre-deflation Sharpe is treated as distinguishable from zero. "The data says no" is a successful outcome. See `04_VALIDATION_METHODOLOGY.md`.
