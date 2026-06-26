# Roadmap: Learning + Build Plan

This is the spine of the project. Each phase has a **goal**, **what you will learn**, **what you will build (the deliverable)**, the **gate** you must pass to move on, and a **LinkedIn angle** so the narrative writes itself as you go.

Pace assumption: 10 to 20 hours per week. Rough calendar estimates are guidance, not deadlines. Quality of understanding beats speed.

A guiding principle borrowed from professional practice: **earn complexity.** Every phase produces a working, transparent baseline before anything fancier is allowed. If a simple version cannot be made to work and be understood, a complex version is just a more expensive way to be wrong.

---

## Phase 0: Foundations and setup
**~1 week.** Goal: a working environment and the vocabulary to not get lost.

- **Learn:** how spot crypto markets work (order book, maker vs taker, bid/ask spread, slippage); what an exchange API does; the difference between time-series and cross-sectional momentum; what a backtest is and the main ways they lie to you.
- **Build:** Python environment (venv or conda), git repository (this folder), an exchange account with read-only API keys first, and a "hello world" script that pulls live prices via CCXT and prints them.
- **Gate:** you can fetch live and historical prices for 5 assets and explain, in your own words, what bid, ask, spread, maker fee and taker fee mean for your $10k.
- **LinkedIn angle:** "Day 1 of building a real quant trading system. Here is the project I am committing to and why I chose crypto momentum." Post the charter's thesis.

## Phase 1: Data pipeline
**~1 to 2 weeks.** Goal: clean, trustworthy historical data, because everything downstream inherits its flaws.

- **Learn:** OHLCV data, candle intervals, the difference between an API that returns only recent candles versus full history, look-ahead bias, survivorship bias (delisted coins), and why point-in-time universe membership matters.
- **Build:** a script that downloads multi-year daily OHLCV for your candidate universe, stores it locally (Parquet/CSV), handles the exchange's history limits, and a second script that builds the tradable universe (liquidity screen by dollar volume, stablecoins removed). Note: some exchanges (Kraken included) only return ~720 recent candles per REST OHLC call, so deep history comes from downloadable archives or the trades endpoint. Solve this explicitly.
- **Gate:** you have a reproducible dataset you trust, you can plot any asset's price history, and you can list which assets were liquid enough to trade at each point in time.
- **LinkedIn angle:** "The unglamorous truth about quant: I spent a week on data, not strategy. Here is why survivorship bias would have made my backtest lie to me."

## Phase 2: Signal research and a vectorized backtest
**~2 to 3 weeks.** Goal: a first honest backtest of cross-sectional momentum.

- **Learn:** how to compute trailing returns and rank cross-sectionally, how to form a long-only top-quantile portfolio, vectorized backtesting in pandas, and the core performance metrics (CAGR, volatility, Sharpe, max drawdown, turnover, hit rate).
- **Build:** a vectorized backtest that ranks the universe each week, holds the top quantile, and produces an equity curve plus a metrics table, benchmarked against buy-and-hold BTC and equal-weight universe. Pre-register your hypothesis and parameters in the log BEFORE you run it.
- **Gate:** you can produce and read an equity curve and a metrics table, and explain what each number means and where the strategy made or lost money.
- **LinkedIn angle:** "My first backtest. Here is what cross-sectional momentum looked like on paper, and the three reasons I do not believe it yet."

## Phase 3: Realism: costs, slippage, and the honesty pass
**~1 to 2 weeks.** Goal: find out whether the edge survives contact with reality. This is the make-or-break phase.

- **Learn:** transaction cost modeling (maker/taker fees), slippage assumptions, how turnover compounds costs, and why the literature finds crypto cross-sectional momentum often dies here.
- **Build:** add a realistic cost-and-slippage layer to the backtest. Re-run. Compare gross versus net. Test sensitivity to the rebalance frequency and lookback window.
- **Gate:** you can state, with evidence, whether net-of-cost performance beats simply holding BTC. A clear "no" is a passing grade and a great story.
- **LinkedIn angle:** "I added realistic costs to my crypto momentum backtest and watched the edge shrink. Here is exactly how much, and what the academic papers got right."

## Phase 4: Robustness and validation
**~2 to 3 weeks.** Goal: separate a real pattern from a lucky fit.

- **Learn:** in-sample versus out-of-sample, walk-forward analysis, parameter sensitivity / heatmaps, the multiple-testing problem (the more you try, the more false winners you find), and the deflated Sharpe ratio idea.
- **Build:** a walk-forward harness, parameter sensitivity maps, and a comparison of cross-sectional momentum versus a time-series/trend-following variant and a trend regime overlay (the latter is what the literature suggests is more robust).
- **Gate:** you can defend whether the strategy is robust or overfit, and you have chosen the variant (cross-sectional, time-series, or hybrid with a trend filter) that the evidence supports.
- **LinkedIn angle:** "How I tried to fool myself, and failed: walk-forward testing my crypto strategy. The version that survived was not the one I started with."

## Phase 5: Portfolio construction and risk management
**~1 to 2 weeks.** Goal: turn a signal into a sized, risk-controlled portfolio.

- **Learn:** position sizing, volatility targeting, risk parity intuition, per-asset caps, drawdown circuit breakers, and rebalancing logic.
- **Build:** a portfolio layer that converts ranks into target weights with volatility targeting and per-asset caps, plus the drawdown kill switch from the charter's non-negotiables.
- **Gate:** the backtest now reflects sized, risk-managed positions, and the risk rules demonstrably reduce worst-case drawdown.
- **LinkedIn angle:** "A signal is not a strategy. Here is the risk management layer that decides how much, not just what."

## Phase 6: Paper trading deployment
**~2 to 3 weeks (then runs in background).** Goal: the full live machine, trading fake money on real prices.

- **Learn:** event-driven (versus vectorized) execution, scheduling/automation, order types, idempotency (not double-trading on a restart), logging, monitoring, and reconciliation.
- **Build:** the live engine running against the exchange's paper/sandbox or a simulated-fills mode: on schedule it pulls data, computes target weights, diffs against current holdings, places orders, logs everything, and reconciles. Add a daily status report and the kill switch as a single command.
- **Gate:** the system runs unattended for at least 2 to 4 weeks on paper with no manual help, and paper results are consistent with backtest expectations.
- **LinkedIn angle:** "It is alive (on paper). My strategy now trades itself every week. Here is the architecture and the bugs that nearly broke it."

## Phase 7: Live deployment with real capital
**Gradual.** Goal: real money, conservatively, with full control.

- **Learn:** the psychology and operational discipline of live trading, the gap between paper and live (real slippage, partial fills), and incident response.
- **Build:** swap paper keys for trade-only live keys, deploy a small first tranche ($1,000 to $2,000), monitor, reconcile, and scale toward $10k only once the live pipeline matches expectations.
- **Gate:** real fills reconcile against the system's intended trades, and you can sleep at night because the kill switch and drawdown breaker are tested.
- **LinkedIn angle:** "I put real money behind it. Here is what live trading taught me that no backtest could."

## Phase 8: Operate, journal, and iterate
**Ongoing.** Goal: run it like a professional, and keep the story going.

- Monitor performance versus backtest expectations, log every deviation and decision, run a monthly review, and only then consider a second strategy family or ML enhancements (the earned-complexity rule).
- **LinkedIn angle:** monthly "what the system did and what I learned" updates, plus a capstone write-up of the whole journey.

---

## How the LinkedIn narrative is built
Every phase above already names the post. The discipline is simple: at the end of each work session, add a dated entry to `PROGRESS_LOG.md` capturing what you did, what surprised you, and one thing you learned. Those raw entries are the feedstock; the per-phase angles are the headlines. Honesty (including dead ends and the costs that killed the edge) is what will make the series credible to actual quants, who have seen a thousand "I built a bot that prints money" posts and trust none of them.
