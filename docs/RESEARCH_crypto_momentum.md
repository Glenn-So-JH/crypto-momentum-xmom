# Momentum in Crypto: A Literature and Practitioner Synthesis for XMom

Prepared for the XMom project (long-only, spot-only, Kraken, weekly rebalance, ~$10k, roughly 13-20 liquid USD pairs). Date: July 2026.

Purpose: this is not a survey for its own sake. Every section ends in something we can test or a decision we must make. Claims are cited; where evidence is thin or contested, that is said explicitly.

---

## 0. Executive summary

The academic and practitioner evidence, read honestly, supports the project's central hypothesis. Time-series (TS) momentum in crypto is one of the most robust findings in the digital asset literature: it survives realistic transaction costs, works best long-only, and is concentrated in large, liquid coins, which is exactly our universe. Cross-sectional (XS) momentum is far shakier: headline results come from huge universes of tiny coins, shrink or vanish under realistic cost and liquidity assumptions, and several careful studies find it insignificant or negative. The most decision-relevant single paper is Han, Kang and Ryu (2024), whose conclusion is blunt: "Evidence of time-series momentum is strong, whereas evidence of cross-sectional momentum is weak."

Three practical numbers frame everything below. First, the best post-cost Sharpe Han, Kang and Ryu find for any crypto momentum strategy is about 1.5, using a 28-day lookback TS strategy, versus about 0.85 for buy-and-hold, and they explicitly call even that "an optimistic view" because it embeds lookback selection bias. Second, academic cost assumptions (15 bps per trade) are roughly 3x to 5x lower than what we will actually pay on Kraken at our size (0.25% maker / 0.40% taker base tier, plus spread). Third, Man AHL finds risk-adjusted returns of crypto trend systems peak at roughly 10-15 coins, which means our thin universe is not actually a handicap for trend approaches, though it is a real handicap for XS ranking.

The main decision the owner needs to make: treat long-only TS momentum with a BTC regime filter and volatility scaling as the base case strategy, and treat pure XS ranking as the challenger to be falsified, not the default. Also: fix the cost model at realistic Kraken numbers before any backtest is trusted, and extend history beyond 2 years as soon as practical, because 2 years of weekly rebalances (~104 observations) cannot statistically distinguish a Sharpe 1.0 strategy from luck.

---

## 1. TS vs XS momentum in crypto: what the evidence actually shows

### 1.1 The bull case for XS momentum, and why it flatters

Liu, Tsyvinski and Wu (Journal of Finance, 2022) is the canonical XS result. Sorting a broad universe of coins on 1-week to 4-week past returns produces large long-short spreads, on the order of 3% per week in some specifications, and momentum is one of only three factors (market, size, momentum) they find price the cross-section. This is the paper that put crypto momentum on the map.

But three features make it a poor template for XMom. The universe includes thousands of small coins where most of the spread lives. The strategy is long-short, and the short leg is unimplementable for us (and dangerous for anyone, see 1.3). And returns are gross of costs; weekly-rebalanced decile portfolios of illiquid coins would bleed spread. The result is real as an asset-pricing fact and largely irrelevant as a trading strategy for a $10k long-only spot account on Kraken.

### 1.2 The mixed and negative XS findings

Shen, Urquhart and Wang (2020), using 1,786 coins from 2013 to 2019 with weekly rebalancing, found an insignificant average momentum payoff of about 0.90% per week, with negative payoffs in several specifications, and the (negative) payoff growing as coins get smaller. So the two most-cited weekly XS studies flatly disagree, which is itself information: the XS effect is fragile to sample, weighting, and universe choices.

Dobrynskaya (2021), on the 2,000 largest coins 2014-2020, finds XS momentum only at short horizons, roughly 1 to 4 weeks, which then flips into significant reversal beyond about a month, strongest at 26-week lookbacks. She calls this the "faster metabolism" of crypto: the equity momentum lifecycle (12-month formation, multi-year reversal) is compressed by an order of magnitude. Critically for us, large liquid coins show short-horizon momentum while the long-horizon reversal is concentrated in small coins.

The recent "Cryptocurrency momentum has (not) its moments" (Financial Markets and Portfolio Management, 2025) adds two sobering points: crypto momentum strategies suffer severe crashes, and portfolio results can hinge on a single coin, meaning removing one name can flip significance. Momentum there too appears to be a large-cap phenomenon.

### 1.3 The Han, Kang and Ryu benchmark (our central reference)

Han, Kang and Ryu (2024, SSRN 4675565) is the most careful implementable-strategy study to date and should be XMom's reference paper. Setup: CoinMarketCap data Dec 2013 to Aug 2023, survivorship-bias free (includes dead coins), filtered to coins with both $1M+ market cap and $1M+ daily volume on 30-day averages (433-784 coins in recent years), 15 bps per trade, daily mark-to-market, lookback and holding periods from 1 to 56 days.

Key findings, with numbers:

TS momentum is strong. The best pair, 28-day lookback with 5-day holding, delivers a post-cost Sharpe of 1.51 versus 0.85 for the market, with max drawdown of 62% versus 89% for buy-and-hold, while being invested only about 48% of the time. Lookbacks of 7-28 days with holding periods of 1-14 days broadly work; the strongest regression t-statistic (4.08) is at 28-day lookback. The effect is robust across all five weighting schemes tested (Sharpe 1.40-1.65) and across size and volume subgroups.

XS momentum is weak. Of 21 XS portfolios tested, 5 were fully liquidated during the sample and only 6 outperformed the market. The best (14-day lookback, 7-day holding) reached Sharpe 1.28 versus 1.01 for the market over the comparable period, a modest edge. Ten portfolios had mean-return t-stats above 2, but only 3 survived when tested on log returns, their point being that with fat tails, a significant arithmetic mean can coexist with a negative expected compound growth rate.

Long-only is the right structure. Profits come from the long leg and from large winners; short legs lose money in all but one specification because losers rebound violently ("Losers often rebound and inflict significant losses"). This is the opposite of equity momentum, where the short leg and small caps drive profits. Our long-only spot constraint is therefore not a compromise; it is where the premium actually lives.

Momentum is bull-market conditional. TS momentum evidence is strong when the market is bullish and absent when bearish, which directly motivates a regime filter (Section 4).

Their honesty caveat, worth quoting: "we test various pairs of look-back and holding periods and choose optimal combinations. This practice introduces a look-ahead bias... our findings should be regarded as an optimistic view." Also note their mechanism finding: crypto momentum looks like overreaction, not the underreaction story from equities, which is consistent with Dobrynskaya's fast reversal.

Supporting TS evidence: Liu and Tsyvinski (Review of Financial Studies, 2021) document strong TS momentum in Bitcoin and other majors at 1-4 week horizons. A long-run practitioner-style study, "A Decade of Evidence of Trend Following Investing in Cryptocurrencies" (arXiv 2020), and Rohrbach, Suremann and Osterrieder (2017) both find simple trend rules (moving average crossovers around 10-40 days) achieve Sharpes broadly in the 0.5 to 1.5 range on crypto. One caveat for balance: Rohrbach et al. actually concluded an XS variant looked better than TS in their crypto sample, so the TS-over-XS ranking is a preponderance of evidence, not unanimity.

### 1.4 Costs are the dividing line

The "Momentum and liquidity in cryptocurrencies" study (arXiv 2019) found long-only momentum-tilted portfolios of liquid coins beat the cap-weighted market even after transaction costs, while loser/illiquid portfolios do not survive spreads. Han, Kang and Ryu show cost drag is worst for short holding periods (frequent rebalance) and that even at an optimistic 15 bps, several XS portfolios flip from significant to unprofitable. Our realistic all-in cost per side on Kraken (Section 5) is 45-70 bps taker for alts. The honest prior: any strategy whose backtest edge is under roughly 10-15% annualized gross over benchmark, with weekly full rebalancing, is likely a cost donation at our fee tier.

---

## 2. Signal design choices that matter

### 2.1 Lookback windows

The literature clusters hard on short lookbacks for crypto. Han, Kang and Ryu's sweet spot is 7-28 days (28 the best); Liu-Tsyvinski momentum lives at 1-4 weeks; Dobrynskaya finds momentum at 1-4 weeks flipping to reversal past a month, worst at 26 weeks; Quantpedia's Bitcoin work also finds the shortest lookbacks tested (10-50 days) work best. Implication for our grid: 7, 14, 21, 28 and maybe 60 days are the live candidates; 90-day and longer lookbacks are expected to be flat-to-negative for XS ranking (they sit in reversal territory) though they may still be fine as slow TS trend filters (200d MA style, which is a different use: regime detection, not asset selection).

### 2.2 The "skip most recent period" convention

In equities one skips the most recent month because of short-term reversal. In crypto the evidence says be careful transplanting this. Kozlov-style results summarized in "Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets" (2021) find daily reversal is a feature of illiquid small coins, while the largest, most tradeable coins actually exhibit short-term (daily) momentum. Standard crypto factor construction often skips only the last 1 day, not a week. For a universe of Kraken's most liquid majors, skipping the last 7 days would discard the most informative part of the signal. Expectation: skip-1-day is cheap insurance and roughly neutral; skip-7-days hurts. Test both, but the prior is against long skips.

### 2.3 Volatility scaling of the signal

Two related ideas with good support. First, define the signal itself in vol-adjusted units (return divided by realized vol, a crude t-stat), which stops the ranking from being a disguised vol ranking; this is standard practice in TS momentum (Moskowitz-Ooi-Pedersen lineage) and is what Man AHL-style systems trade. Second, scale position size by inverse vol or to a vol target (Section 4). For the ranking step specifically, evidence in crypto is thinner, but because crypto XS vol dispersion is enormous (a meme coin can have 3x BTC's vol), raw-return ranking systematically selects the highest-vol names and loads the fat tails documented by Han, Kang and Ryu (single-day coin moves from -99.6% to +9187% in their sample). Vol-scaling the signal is low-cost robustness with a sound mechanism; treat it as an A/B test, expect modest Sharpe improvement and materially better tails.

### 2.4 Winsorizing and rank transforms

Direct crypto evidence on winsorization is weak to nonexistent; it is a hygiene practice, not an alpha source. The relevant crypto fact is the extreme kurtosis (daily market kurtosis 6.81 in Han, Kang and Ryu, individual coins far worse), which makes anything mean-based fragile. Practical guidance: use ranks (or z-scores winsorized at roughly the 1st/99th percentile) rather than raw past returns for XS scoring, and evaluate performance on log returns as well as arithmetic, per Han, Kang and Ryu's demonstration that t-tests on arithmetic means overstate profitability under fat tails. Expect winsorizing to change little on a 13-coin large-cap universe but to prevent occasional absurd weights; it is cheap and keeps the backtest honest.

---

## 3. Portfolio construction

### 3.1 Top-quantile vs top-N in a thin universe

Academic papers sort hundreds of coins into deciles or quintiles. With a median of ~13 eligible names, a "decile" is one coin. This is the thin-universe problem: XS ranking derives its power from breadth (the fundamental law of active management: IR scales with the square root of the number of independent bets), and 13 highly correlated coins is very little breadth, especially since alt returns are dominated by a single BTC/market factor. Practically: use top-N with N of 3 to 5. Top-3 concentrates signal but makes results hostage to single names (the FMPM 2025 paper shows one coin can flip a momentum result); top-5 of 13 is nearly "hold the top 40%," which dilutes the signal toward the market. There is no free lunch here, which is itself a reason to expect XS on this universe to be weak and to prefer TS-style rules that do not require ranking neighbors against each other.

### 3.2 Equal vs volatility weighting

Within the chosen basket, equal weighting is the academic default; inverse-vol weighting is the practitioner default (Man AHL, and the vol-targeting literature below). Given vol dispersion across coins, inverse-vol weighting mostly means "less DOGE-class risk per name," which improves risk-adjusted returns modestly and cuts tail risk. Expect a small Sharpe improvement, not a transformation. Cap any single name (say 30-40%) so BTC/ETH dominance or a low-vol artifact cannot concentrate the book.

### 3.3 Rebalance frequency vs turnover

This is the binding constraint for XMom, more than signal choice. The cost math at our size: Kraken base tier is 0.25% maker / 0.40% taker; alt spreads add 5-30 bps; call it 50 bps all-in per side taker. A weekly top-5 portfolio that replaces one name per week trades ~40% of NAV (sell 20%, buy 20%), costing ~20 bps per week, roughly 10% per year, which is most of the plausible edge. Han, Kang and Ryu confirm cost drag rises sharply as holding periods shorten. Mitigations, in order of expected value: (a) rebalance bands / hysteresis, e.g. a coin must fall below rank 7 before being sold from a top-5 book, which cuts churn from rank noise; (b) use post-only limit orders to pay maker (0.25%) instead of taker (0.40%); (c) consider biweekly rebalance as a test arm; (d) only trade weight deviations above a threshold (e.g. 5% of NAV). Weekly is a fine cadence given crypto's fast momentum decay (monthly would sail past the 2-4 week momentum horizon into reversal territory), but weekly with turnover controls, not naive full re-sorting.

### 3.4 Benchmarks

Long-only momentum on 13 coins in a bull market will look great in absolute terms regardless of skill. The fair benchmarks are: equal-weight buy-and-hold of the same universe (rebalanced at the same cadence and costed identically), BTC buy-and-hold, and cap-weighted universe. Alpha claims should be made against those, not against zero. Han, Kang and Ryu report many "profitable" momentum portfolios that fail to beat the market; that must not happen to us silently.

---

## 4. Robustness overlays with actual evidence behind them

### 4.1 Trend/regime filter (BTC above a moving average)

Best-supported overlay for this project. Grayscale's "The Trend is Your Friend" shows a naive BTC 50-day MA rule (long above, cash below) beat buy-and-hold since 2012 on both return and volatility, mostly by sidestepping the large drawdowns (Q4 2021, Q2 2022). Han, Kang and Ryu independently show crypto momentum profits exist in bullish regimes and disappear in bearish ones. Practitioner work (e.g. Artemis Research's BTC regime-gated alt factor strategy) applies exactly the structure we would: a BTC regime gate decides whether to hold alt risk at all, then a ranking model picks names; the strategy sits in cash much of the time because "when BTC trends down, alts get crushed regardless of individual fundamentals." Expectation: a BTC > 200d (or 100d/50d, to be tested, do not optimize hard) MA gate will cut max drawdown dramatically with modest cost to CAGR, and will be the single largest risk-adjusted improvement available to us. Caveat: with only 2 years of data we may have only one or two regime transitions in-sample; this overlay must be justified by out-of-sample logic and the cited literature, not by our own backtest alone.

### 4.2 Volatility targeting

Harvey, Hoyle, Korgaonkar, Rattray, Sargaison and van Hemert ("The Impact of Volatility Targeting," Man Group / JPM 2018) show scaling exposure inversely to trailing vol improves Sharpe and cuts left tails for risk assets, because volatility is persistent while expected returns do not rise proportionally with vol. Crypto-specific confirmation: "Cryptocurrency Market Risk-Managed Momentum Strategies" (Finance Research Letters, 2025) reports vol-managing a crypto momentum strategy raised weekly returns from 3.18% to 3.47% and annualized Sharpe from 1.12 to 1.42, and, interestingly, the gain came from higher returns rather than crash avoidance. The FMPM 2025 paper likewise finds vol management mitigates crypto momentum crashes. Implementation for us: target portfolio vol (e.g. 40-60% annualized, calibrate later) using 20-30 day realized vol, with the residual in cash/stables; cap leverage at 1 (spot only). Expectation: higher Sharpe, smaller drawdowns, slightly lower CAGR in relentless bull phases.

### 4.3 TS + XS hybrid

The natural synthesis given Section 1: require a coin to pass its own TS filter (e.g. positive 28-day return, or price above its own 50d MA) AND rank well cross-sectionally, holding fewer names or more cash when few qualify. This is "dual momentum" in Antonacci's sense adapted to crypto, and it is effectively what the Artemis regime-gated design does. Direct academic tests of the hybrid in crypto are scarce (flag: weak evidence, sensible mechanism), but each leg is independently supported, and the hybrid mechanically prevents the worst XS failure mode: being forced to hold the "least bad" coins in a falling market because ranking is always relative. Expectation: the hybrid beats pure XS on drawdown and Sharpe, and roughly matches pure TS, with the benefit showing up in bear/chop regimes.

---

## 5. Crypto-specific gotchas

Annualization. Crypto trades 365 days a year. Annualize daily stats with sqrt(365), not sqrt(252), and weekly with sqrt(52). Mixing conventions changes reported Sharpe by ~20% (sqrt(365/252) = 1.20) and is a common way crypto backtests get silently flattered or penalized when compared to equity numbers. Pick 365 everywhere, document it, and when comparing to papers check which convention they used.

24/7 markets and rebalance timing. There is no close; define an explicit rebalance timestamp (e.g. Monday 16:00 UTC) and use that same timestamp for signal computation with a deliberate execution lag (compute on t, trade on t+1 bar) to avoid lookahead. Avoid weekends: weekend volume is 20-40% lower and BTC spreads roughly double (Kaiko; Phemex data), so a weekday rebalance is cheaper. Note also academic findings of day-of-week effects in crypto (Han, Kang and Ryu explicitly stagger start days to wash out a "Monday effect"); we should at minimum check that results are not an artifact of the chosen rebalance day.

Fat tails break normal-approximation statistics. Daily crypto returns have extreme kurtosis; Han, Kang and Ryu show strategies with significant arithmetic mean returns and negative expected log growth, and portfolios that get liquidated when marked daily even though weekly marks looked fine. For us: evaluate on log returns and max drawdown alongside Sharpe, mark daily even though we trade weekly, and never trust a t-stat on 104 weekly observations. On that last point: with ~2 years of weekly data, the standard error of an annualized Sharpe estimate is roughly 0.7, so we cannot statistically separate Sharpe 1.0 from Sharpe 0. Backtests on our sample are for ranking design choices and catching disasters, not for proving edge. Extending history (Kraken has BTC data back to 2013 for majors) is high value.

Costs at our fee tier. Kraken base spot fees are 0.25% maker / 0.40% taker, falling only with 30-day volume we will not have at $10k. Academic papers assume 10-15 bps (Binance-tier). Every strategy from the literature must be re-costed at roughly 30-50 bps per side (maker, plus spread/slippage) before believing it. This single adjustment is probably the difference between "XS momentum works" (literature, 15 bps) and "XS momentum does not survive" (us, 50 bps), which is the project's core hypothesis restated as a fee schedule.

Exchange and liquidity fragmentation. Prices differ across venues; signals computed from an aggregate index (CoinMarketCap-style) may not match Kraken executable prices, especially on weekends and for smaller alts. Since we trade only Kraken, compute signals from Kraken OHLCV so the backtest and live pipeline see the same world. Kraken-only volume also understates global liquidity but is the correct number for our own market-impact and screen decisions.

Survivorship of dead coins. More than half of all tokens ever listed are dead (14,000+ of ~24,000 on CoinMarketCap; see CoinAPI and Concretum), and naive backtests on today's listings inflate returns massively (Concretum's example: a top-20 altcoin strategy showed +2,800% with survivorship bias versus +680% without). Ammann, Burdorf, Liebi and Stöckl (2022) treat this formally. Our exposure is real but bounded: a 2-year window of currently-listed liquid Kraken majors excludes anything Kraken delisted in that window (and Kraken does delist: privacy coins, securities-flagged tokens, failed projects like LUNA-era assets). Mitigation: build the universe point-in-time from historical Kraken listing/volume data (planned task 1A.2), and sanity-check by listing what was delisted from Kraken over our sample and asking whether our screen would have held it.

Stablecoins and wrapped assets. Exclude stables (USDT, USDC, DAI), wrapped duplicates (WBTC vs BTC) and staked variants from the momentum universe; papers do this (Han, Kang and Ryu exclude 96 stablecoins) and leaving them in corrupts both ranking and vol estimates.

---

## 6. Prioritized, testable hypotheses for XMom

Ordered by decision value per unit of effort. Each is falsifiable in our Phase 1 backtest engine.

H1. If we run long-only TS momentum (hold coin when its own 14-28d return is positive, else cash) on our universe, we expect it to beat both buy-and-hold and the equivalent XS top-N strategy on post-cost Sharpe, with lower max drawdown (Han, Kang and Ryu 2024; Liu and Tsyvinski 2021).

H2. If we re-cost the classic weekly XS top-quantile momentum strategy at realistic Kraken fees (40-50 bps per side all-in) instead of the literature's 15 bps, we expect its edge over equal-weight buy-and-hold to shrink to roughly zero or negative, confirming the project's central hypothesis (Han, Kang and Ryu 2024 cost sensitivity; Shen, Urquhart and Wang 2020; Kraken fee schedule).

H3. If we sweep lookbacks {7, 14, 21, 28, 60, 90} days, we expect 14-28 days to dominate and 90 days to be flat or negative for XS ranking, consistent with crypto's fast momentum-to-reversal cycle (Dobrynskaya 2021; Han, Kang and Ryu 2024).

H4. If we add a BTC regime gate (only hold alt/momentum positions when BTC is above its 100-200d MA, else cash), we expect max drawdown to fall by a third or more with small CAGR cost, and most of the strategy's edge to come from bull regimes (Grayscale 2023; Han, Kang and Ryu bull-market conditionality; Artemis Research).

H5. If we apply volatility targeting (scale gross exposure by target-vol over realized 20-30d vol, capped at 100% invested), we expect annualized Sharpe to improve on the order of 0.2-0.3 and left-tail months to shrink (Harvey et al. 2018; Finance Research Letters 2025 risk-managed crypto momentum; FMPM 2025).

H6. If we vol-scale the momentum signal (rank on return/vol instead of raw return), we expect similar or slightly better Sharpe and materially less exposure to the highest-vol names, with fewer blowup weeks (Moskowitz-Ooi-Pedersen TS momentum logic; Han, Kang and Ryu tail evidence; direct crypto evidence weak, mechanism strong).

H7. If we skip the most recent 1 day in signal formation, we expect little change on our large-cap universe; if we skip a full 7 days, we expect performance to degrade, because large liquid coins show short-term momentum, not reversal (Up or down? 2021; standard crypto factor construction skips only 1 day).

H8. If we add rebalance bands (sell only when a holding drops below rank N+2) and trade-size thresholds, we expect turnover to fall by a third to a half with negligible gross signal loss, making net returns strictly better (cost math above; Han, Kang and Ryu showing cost drag concentrates at short holding periods). This is likely the highest net-return improvement available after H1.

H9. If we compare top-3 vs top-5 out of ~13 names, we expect top-3 to have higher gross return, worse tails and high sensitivity to single names; we expect neither to be robust if removing the single best coin from the sample kills the result, and we will run that leave-one-coin-out check explicitly (FMPM 2025 single-coin fragility).

H10. If we weight holdings by inverse volatility with a 30-40% single-name cap instead of equal weight, we expect a small Sharpe gain and smaller drawdowns, not a large return change (Harvey et al. 2018 vol-scaling logic; Man AHL practice).

H11. If we build the TS+XS hybrid (XS rank among coins that individually pass a TS filter, cash otherwise), we expect it to beat pure XS on Sharpe and drawdown and to roughly match pure TS, with the advantage concentrated in bear and chop regimes (synthesis of H1 and H4; direct crypto evidence for the hybrid is thin, flag as exploratory).

H12. If we rebalance on a weekday (e.g. Tuesday) instead of the weekend, we expect execution costs to be measurably lower (weekend spreads roughly 2x, volume 20-40% lower), and we expect strategy results to be broadly insensitive to rebalance day; if they are not, that is a red flag for noise-fitting (Kaiko; Phemex; Han, Kang and Ryu day-of-week staggering).

H13. If we expand the universe beyond the top ~15 liquid names, we expect no Sharpe improvement and rising cost drag, so universe expansion is not a priority (Man Group "In Crypto We Trend": trend-system Sharpe peaks around 10-15 coins, ~10 for breakout models, liquidity falls off sharply beyond the top 15).

H14. If we recompute any promising result using log returns, sqrt(365) annualization, and daily mark-to-market, we expect some strategies that look significant on arithmetic weekly means to stop looking significant, and we will only promote strategies that survive all three (Han, Kang and Ryu profitability critique).

### Decisions for the owner

1. Adopt TS-first framing: base case is long-only TS momentum with BTC regime gate and vol targeting; XS top-N is the challenger to falsify (H1, H2, H4, H5).
2. Fix the cost model now: 40-50 bps per side all-in (0.25% maker + spread/slippage) as the default, 60-70 bps as the stress case; never quote a backtest without costs.
3. Set a turnover budget (suggest max ~50% one-way per week) and implement rebalance bands before optimizing signals (H8).
4. Commit to extending price history beyond 2 years and to point-in-time universe construction before drawing statistical conclusions; with 104 weekly observations no Sharpe estimate is trustworthy on its own.

---

## Sources

Academic papers:

- Han, Kang and Ryu (2024), "Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market: A Comprehensive Analysis under Realistic Assumptions." SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565 ; full PDF: https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf
- Liu, Tsyvinski and Wu (2022), "Common Risk Factors in Cryptocurrency," Journal of Finance 77(2): https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119 ; SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3379131
- Liu and Tsyvinski (2021), "Risks and Returns of Cryptocurrency," Review of Financial Studies 34(6): https://academic.oup.com/rfs/article-abstract/34/6/2689/5912024
- Shen, Urquhart and Wang (2020), weekly crypto momentum findings, as summarized in "Cryptocurrency momentum has (not) its moments," FMPM (2025): https://link.springer.com/article/10.1007/s11408-025-00474-9
- Dobrynskaya (2021), "Cryptocurrency Momentum and Reversal." SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3913263
- Kozlov et al. (2021), "Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets," International Review of Financial Analysis: https://www.sciencedirect.com/science/article/pii/S1057521921002349
- "Cryptocurrency Market Risk-Managed Momentum Strategies" (2025), Finance Research Letters: https://www.sciencedirect.com/science/article/abs/pii/S1544612325011377
- Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, van Hemert (2018), "The Impact of Volatility Targeting": https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf
- "Momentum and Liquidity in Cryptocurrencies" (2019), arXiv: https://arxiv.org/pdf/1904.00890
- "A Decade of Evidence of Trend Following Investing in Cryptocurrencies" (2020), arXiv: https://arxiv.org/pdf/2009.12155
- Rohrbach, Suremann and Osterrieder (2017), "Momentum and Trend Following Trading Strategies for Currencies Revisited": https://papers.ssrn.com/Sol3/Delivery.cfm/SSRN_ID2949379_code2672176.pdf?abstractid=2949379
- Ammann, Burdorf, Liebi and Stöckl (2022), "Survivorship and Delisting Bias in Cryptocurrency Markets." SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4287573
- Fičura (2023), "Impact of size and volume on cryptocurrency momentum and reversal," FFA Working Papers: https://wp.ffu.vse.cz/pdfs/wps/2023/01/03.pdf

Practitioner and data sources:

- Man Group / Man AHL, "In Crypto We Trend": https://www.man.com/insights/in-crypto-we-trend (PDF: https://www.man.com/documents/download/18369-7a1d4-c4d42-3bc42/Man_AHL_Analysis_In_Crypto_We_Trend_English_(United_States)_19-12-2024.pdf)
- Grayscale Research, "The Trend is Your Friend: Managing Bitcoin's Volatility with Momentum Signals": https://www.grayscale.com/research/reports/the-trend-is-your-friend-managing-bitcoins-volatility-with-momentum-signals
- Artemis Research, "BTC Regime-Gated Alt Factor Strategy": https://research.artemis.ai/p/btc-regime-gated-alt-factor-strategy
- Kraken fee schedule: https://www.kraken.com/features/fee-schedule
- Man Group, "The Impact of Volatility Targeting" (summary page): https://www.man.com/insights/the-impact-of-volatility-targeting
- Quantpedia, "Trend-following and Mean-reversion in Bitcoin": https://quantpedia.com/trend-following-and-mean-reversion-in-bitcoin/
- Quantpedia, "An Introduction to Volatility Targeting": https://quantpedia.com/an-introduction-to-volatility-targeting/
- Concretum Group, "Building a Survivorship Bias-Free Crypto Dataset": https://concretumgroup.com/building-a-survivorship-bias-free-crypto-dataset-with-coinmarketcap-api/
- CoinAPI, "How to Eliminate Survivorship Bias in Crypto Backtesting": https://www.coinapi.io/blog/how-to-eliminate-survivorship-bias-in-crypto-backtesting
- Kaiko Research, "Where Did Weekend Crypto Traders Go?": https://research.kaiko.com/insights/where-did-weekend-crypto-traders-go
- Phemex, "Weekend Crypto Trading Explained": https://phemex.com/blogs/weekend-crypto-trading-explained
- Altrady, "Sharpe Ratio and Sortino Ratio for Crypto" (365-day convention): https://www.altrady.com/blog/risk-management/sharpe-ratio-sortino-ratio-crypto
