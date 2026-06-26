# Resources

Curated, established references. Each is mapped to the phase where it earns its keep. Prefer primary sources (papers, official docs) over blog summaries when learning the core ideas.

## Foundational books (the canon)
- **Ernie Chan, "Algorithmic Trading: Winning Strategies and Their Rationale"** and **"Quantitative Trading."** The most practical on-ramp for a retail quant: momentum, mean reversion, backtest pitfalls, position sizing. Start here.
- **Marcos Lopez de Prado, "Advances in Financial Machine Learning."** The rigor reference. Read the chapters on backtest overfitting, cross-validation in finance, and the deflated Sharpe ratio even before touching ML. This is the antidote to fooling yourself.
- **Andreas Clenow, "Following the Trend."** Clear, honest treatment of trend/time-series momentum and the operational reality of running it. Highly relevant given the evidence that trend momentum is more robust in crypto than pure cross-sectional.

## Key papers (the edge, and the honesty)
- **Jegadeesh & Titman (1993), "Returns to Buying Winners and Selling Losers."** The original cross-sectional momentum paper. Read it to understand the foundational claim.
- **Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere."** Momentum as a cross-asset, cross-market phenomenon. Frames why we expect it in crypto at all.
- **Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum."** The trend-following counterpart to cross-sectional momentum.
- **Han, Kang & Ryu (2024), "Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market: A Comprehensive Analysis under Realistic Assumptions."** The most important paper for this project. Finds time-series momentum is strong but cross-sectional momentum is weak once realistic transaction costs and daily price moves are applied. This is the hypothesis to test. SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565
- **Drogen, Hoffstein & Otte, "Cross-sectional Momentum in Cryptocurrency Markets."** A practitioner-flavored look at the same question. SSRN PDF: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4337066_code2135545.pdf?abstractid=4322637

## Tools and libraries
- **CCXT** (exchange-agnostic trading API for Python, 100+ exchanges). Docs: https://docs.ccxt.com/ . GitHub + wiki/manual: https://github.com/ccxt/ccxt and https://github.com/ccxt/ccxt/wiki/manual . This is our data and execution layer.
- **pandas / numpy** for research and the vectorized backtest.
- **vectorbt** or a hand-rolled backtest first. Build at least one backtest by hand before trusting a library, so you understand what it hides.
- **Parquet** (via pyarrow) for fast local storage of OHLCV.

## Exchange documentation (candidate venue: Kraken)
- **Kraken REST API, Get OHLC Data:** https://docs.kraken.com/api/docs/rest-api/get-ohlc-data . Note the ~720-candle limit per call.
- **Kraken downloadable historical OHLCVT archives** (for deep history): https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data
- **Kraken Advanced API FAQ:** https://support.kraken.com/articles/advanced-api-faq
- Coinbase Advanced Trade API is a reasonable alternative; CCXT abstracts the choice so the venue is not locked in early.

## On not fooling yourself (read early, re-read often)
- Lopez de Prado's work on **backtest overfitting** and the **probability of backtest overfitting (PBO)**.
- The **multiple-testing problem**: the more strategies and parameters you try, the more false winners you will find. Keep a count of how many variants you test.

## A note on AI as teacher
You are using AI (me) as primary teacher, coder, and resource-finder. Good practice: ask for the intuition first, then the math, then the code, and always ask "how could this backtest be lying to me?" Treat any strategy result as guilty until proven innocent.
