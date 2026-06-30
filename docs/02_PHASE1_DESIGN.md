# Phase 1 Design: Data + Backtest Engine + Validation

**Goal of Phase 1:** build the machine that answers "did this strategy work?", and prove the machine is trustworthy by reproducing well-known strategies before we ever invent our own.

We are deliberately NOT chasing our own alpha yet. We are building and validating the instrument. Costs are turned OFF in this phase (set to zero) so we can see raw signal behavior; the cost layer exists but stays dormant until Phase 3.

---

## Guiding principle: validate the instrument before the experiment

A backtester is a measuring instrument. Before you measure something unknown with it, you calibrate it against things whose answer you already know. If we feed our engine "buy and hold Bitcoin" and the equity curve does not exactly match Bitcoin's price, the engine is broken and every later result is fiction. So Phase 1 ends not with a profitable strategy, but with an engine we have *earned the right to trust*, plus intuition for how classic strategies behave.

## Architecture: four layers with clean contracts

The system is four independent layers. Each has one job and a simple hand-off to the next. Keeping them separate is what lets us swap strategies without touching the engine, and swap data without touching strategies.

```
  [1] DATA          [2] STRATEGY        [3] ENGINE           [4] METRICS
  raw OHLCV   -->   target weights  -->  apply weights,  -->  Sharpe, drawdown,
  + universe        per date            compute returns      equity curve, plots
```

1. **Data layer.** Produces a clean, point-in-time table of daily prices and volumes for a defined universe. Everything downstream inherits its quality.
2. **Strategy layer.** A strategy is just a function: given data available *up to and including* date *t*, return the target portfolio weights for date *t*. Nothing more. Buy-and-hold, moving-average crossover, and cross-sectional momentum are all just different versions of this one function.
3. **Engine layer.** Takes a strategy's weights and the price data, applies the weights to the *next* period's returns (this lag is sacred, see below), tracks the portfolio value, turnover, and (later) costs. It does not know or care what the strategy is.
4. **Metrics layer.** Turns an equity curve into the numbers and charts that let us judge it: CAGR, volatility, Sharpe, max drawdown, turnover, hit rate, plus equity and drawdown plots.

## The cardinal rule: no look-ahead

The single most common way a backtest lies is **look-ahead bias**: accidentally using information from the future. The engine enforces one rule to prevent it: weights decided using data through the close of day *t* are applied to the return *from t to t+1*. You decide today using only what you knew today, and you earn tomorrow's return. The engine builds this lag in structurally so a strategy author cannot cheat by accident. We will write an explicit unit test that tries to cheat and confirms the engine refuses.

---

## Part A: The data layer

**What we collect:** daily OHLCV (open, high, low, close, volume) for a universe of liquid crypto USD pairs, stored locally as Parquet so research is fast and reproducible offline.

**Source and a known gotcha.** We pull via CCXT from Kraken (our trading venue, so research data matches what we will trade). Important limitation discovered in Phase 0 research: Kraken's REST OHLC endpoint returns at most ~720 candles per request and cannot page far into the past, so daily history via REST is roughly the last two years. That is enough to get a working, validated pipeline quickly (the 2024 to 2026 window includes real bull and bear regimes). Deeper history (back to earlier cycles) comes from Kraken's downloadable OHLCVT archives or a secondary public source, which we will add as a follow-up once the engine works. We make it work first, then make it deep.

**Universe and survivorship bias.** This is the subtle one. The naive approach, "take today's top 30 coins and download their history," secretly bakes in **survivorship bias**: you only see the winners that survived to today and never the coins that died (LUNA, FTT, and many others). That makes momentum look far better than it was. Our defense: build the universe with a **point-in-time liquidity screen**. On each date, a coin is "in the universe" only if its recent dollar volume cleared a threshold *on that date*, computed from the data itself. We also keep a written list of notable delisted/failed coins so we can talk honestly about what our dataset still misses. Stablecoins (USDT, USDC, DAI, and similar) are always excluded since they do not move.

A concrete seed universe to screen from (liquid Kraken USD majors, roughly 20 to 30 names): BTC, ETH, SOL, XRP, ADA, AVAX, DOT, LINK, LTC, BCH, ATOM, UNI, AAVE, ALGO, XLM, ETC, FIL, NEAR, DOGE, and similar. Note a data gotcha to handle: some tickers get renamed (for example MATIC became POL), which can split a history if not stitched.

**Quality checks (the unglamorous, essential part):** detect and handle missing or duplicated days, zero-volume gaps, obvious bad prints (outliers), and ticker renames. The output of Part A is a dataset we have actively tried to break and trust anyway, plus a short data-quality note.

## Part B: The backtest engine

A **vectorized** engine (fast pandas/numpy math over whole price matrices at once), which is ideal for daily-frequency research. The event-driven version that places live orders comes much later in Phase 6.

What it does: takes the price panel and a strategy's target-weight matrix, applies the sacred t-to-t+1 lag, computes daily portfolio returns, and tracks the equity curve and turnover. It includes a **cost hook** wired in from day one but set to zero for Phase 1, so switching costs on in Phase 3 is a one-line parameter change, not a rewrite.

Two non-negotiable engine unit tests before we trust it:
- **Sanity test:** a 100%-BTC buy-and-hold run must produce an equity curve identical to BTC's own price path. If it does not, stop and fix the engine.
- **Look-ahead guard:** a test that confirms a strategy cannot influence returns earlier than the lag allows.

## Part C: Validation on well-known strategies

We run a ladder of classic, well-documented strategies through the engine, from "we know exactly what this should do" to "this is the family we eventually want." For each, we predict the behavior first, then check the engine agrees.

1. **Buy-and-hold BTC.** Benchmark and engine calibration. Expectation: matches BTC exactly. High return, brutal drawdowns (60%+).
2. **Equal-weight universe, rebalanced.** Benchmark basket. Expectation: smoother than any single coin, diversified.
3. **Moving-average trend (e.g. hold BTC when price > 200-day average, else cash).** Classic time-series trend filter. Expectation: smaller drawdowns than buy-and-hold, sidesteps the worst of bear markets, gives up some upside.
4. **Time-series momentum (per coin: hold it if its own trailing return is positive).** Moskowitz, Ooi & Pedersen. Expectation: trend-like, the more robust momentum variant in crypto per the literature.
5. **Cross-sectional momentum (rank the universe by trailing return, hold the top quantile).** This is our eventual target family, run here purely as a known baseline, gross of costs. Expectation: strong gross returns, high turnover (the thing that will later meet the cost wall).
6. **Optional contrast: short-term reversal/mean-reversion (buy recent losers).** To feel how a non-momentum signal behaves.

Each produces an equity curve and a metrics row in one comparison table. The deliverable is a short results report (`research/phase1_results.md`) with the table and the charts, plus your written observations.

## Metrics we compute

Total return, CAGR, annualized volatility, Sharpe, Sortino, max drawdown, Calmar (CAGR/maxDD), annual turnover, hit rate, and time-in-market. Plus equity-curve and drawdown-curve plots. You will learn to read these as a set, not one number; a high Sharpe with 90% turnover means something very different once costs return.

## Biases this phase teaches you to defeat

- **Survivorship bias** (handled in universe construction).
- **Look-ahead bias** (handled structurally in the engine, plus a test).
- **Data-snooping / overfitting** (introduced conceptually: we are reproducing, not optimizing, so we are not yet at risk, but we name the danger now).
- **Regime dependence** (our short 2-year window is itself a limitation we state out loud).

---

## The build: three staged hand-offs

We build in stages and validate each before the next, the same discipline as the whole project.

- **Stage 1A: Data layer.** Fetch + universe screen + quality checks + Parquet storage. Gate: a dataset we trust, with a data-quality note and the actual history depth per coin reported.
- **Stage 1B: Engine + metrics.** The vectorized engine, the metrics module, and the two engine unit tests (buy-and-hold sanity, look-ahead guard). Gate: both tests pass.
- **Stage 1C: Strategy library + validation.** The six strategies above, run through the engine, with the comparison table, charts, and your written observations. Gate: results are sane and roughly match what theory predicts.

## Phase 1 success gate

Phase 1 is done when: (1) we have a trustworthy, documented dataset; (2) the engine passes its sanity and look-ahead tests; (3) the classic strategies have been reproduced and behave as theory predicts; and (4) you can read the comparison table and explain *why* each strategy looks the way it does. Note: none of these require the strategy to be profitable. We are validating a machine and building intuition.

## LinkedIn angle

"Before building my own trading strategy, I built the thing that judges strategies, and proved it works by reproducing the classics. Here is the four-layer backtesting architecture and the two bugs (look-ahead and survivorship) that make most amateur backtests worthless."
