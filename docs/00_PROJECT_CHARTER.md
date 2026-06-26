# Project Charter: Crypto Cross-Sectional Momentum

**Codename:** XMom
**Owner:** g
**Started:** 2026-06-19
**Status:** Phase 0 (scoping complete, setup beginning)

---

## 1. One-line thesis

Build a fully automated, systematic long-only momentum strategy that ranks a universe of liquid crypto assets, holds the strongest, and rebalances on a fixed schedule. Prove it out on a paper account, then run it live with $10,000 of real capital, while documenting every step rigorously enough to defend in front of a professional quant.

## 2. Why this, why now

A few honest reasons this is the right first project:

- **The edge is real but contested.** Time-series (trend) momentum in crypto is well documented and reasonably robust. Cross-sectional momentum (ranking assets against each other) is documented too, but the strongest recent work (Han, Kang & Ryu, 2024) shows much of the cross-sectional profit disappears once realistic transaction costs and daily price moves are applied. That tension is the point. Our job is not to assume the edge, it is to measure whether it survives reality. That is exactly what professional quants do, and it makes a far more credible story than a strategy that "always wins" in backtest.
- **Crypto is the cleanest path to live automation for a $10k retail account.** Markets run 24/7, there is no Pattern Day Trader rule, assets are fractional, and exchange REST/WebSocket APIs are simple and well supported. The same strategy in US equities at $10k would be legally constrained by the PDT rule.
- **It leans on existing finance intuition.** Ranking, factor thinking, and risk budgeting are conceptual strengths to build on, while the coding and infrastructure are the deliberate growth area.

## 3. Target definition (the scope)

| Dimension | Decision |
|---|---|
| Asset class | Cryptocurrency (spot only, no derivatives or leverage to start) |
| Direction | Long-only (shorting crypto spot is impractical and expensive at retail scale) |
| Universe | The most liquid USD spot pairs on the chosen exchange, stablecoins excluded, screened by 30-day dollar volume. Target roughly 20 to 40 names. |
| Core signal | Cross-sectional momentum: rank the universe by trailing return over a lookback window (initial candidate: ~30 days, possibly skipping the most recent few days to avoid short-term reversal). |
| Comparison signal | Time-series momentum / trend filter, used both as a benchmark and as a regime overlay (e.g. only hold assets, or only deploy capital, when broad market trend is positive). |
| Portfolio construction | Hold the top quantile of ranked assets. Start equal-weight, then test volatility-weighted (risk parity style) sizing. |
| Rebalance frequency | Weekly to start (low turnover keeps costs and complexity down; daily can be tested later). |
| Capital | $10,000 of own funds, deployed only after paper validation. |
| Execution | Exchange API via the CCXT library (exchange-agnostic so we can swap venues). Candidate venue: Kraken (US-accessible, solid API, transparent fees). |
| Benchmark | Buy-and-hold BTC, and an equal-weight hold of the universe. The strategy must justify its complexity against simply holding Bitcoin. |

## 4. What "good" looks like (success criteria)

This project succeeds if, regardless of whether the strategy ends up profitable:

1. There is a reproducible research pipeline: data in, signal computed, backtest run, results explained, all version-controlled and re-runnable from scratch.
2. The backtest is honest: it models transaction costs and slippage, avoids look-ahead and survivorship bias, and is validated out-of-sample (walk-forward), not just curve-fit to history.
3. The decision to deploy or not deploy real capital is made on evidence. "The data says no, so I did not trade it" is a successful outcome and a strong story.
4. If deployed, the live system runs unattended on a schedule, logs every decision and fill, and reconciles against the exchange.
5. The whole journey is documented well enough to teach someone else and to anchor a credible LinkedIn series.

### Risk-management non-negotiables (before any real money)
- Hard cap on per-asset weight.
- Portfolio-level maximum drawdown circuit breaker that flattens to cash.
- Volatility targeting so position sizes scale down when markets get wild.
- A "kill switch": one command that cancels orders and exits to stablecoin/cash.
- API keys scoped to trading only (never withdrawal), stored as environment secrets, never committed to git.

## 5. Explicit non-goals (for now)

To keep scope honest, this project will NOT, in its first version: use leverage or margin; trade derivatives/perpetual futures; attempt high-frequency or intraday execution; use machine-learning price prediction (we earn the right to ML only after a transparent baseline exists); or chase more than one strategy family at a time.

## 6. Key risks and how we treat them

- **Overfitting.** The single biggest danger. Mitigated by out-of-sample/walk-forward testing, a small number of parameters, and pre-registering hypotheses in the progress log before testing them.
- **Transaction costs eating the edge.** Mitigated by modeling realistic fees and slippage from day one, and by keeping turnover low (weekly rebalance, top-quantile holds).
- **Survivorship and data bias.** Mitigated by sourcing point-in-time universe membership where possible and being explicit about delisted/dead coins.
- **Execution and operational risk** (failed orders, partial fills, API downtime, key leakage). Mitigated by paper trading first, reconciliation, conservative sizing, and strict secret hygiene.
- **Behavioral risk** (overriding the system, panic selling). Mitigated by writing rules down in advance and logging every manual intervention as a deviation.

## 7. Capital and risk budget

- Total at risk: $10,000, treated as fully losable risk capital. Do not deploy money needed for living expenses.
- Phase the capital in. First live tranche is intentionally small (for example $1,000 to $2,000) to validate the live pipeline before scaling to the full $10k.

---

*This charter is a living document. Material changes are logged in `PROGRESS_LOG.md` with a date and a one-line rationale.*
