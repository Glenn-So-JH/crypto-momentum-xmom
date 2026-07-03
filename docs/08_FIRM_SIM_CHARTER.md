# Project Reframe: Firm-Grade Quant Research Simulation

Date: 2026-07-03. This reframes the primary goal. The retail $10k Kraken deployment from `00_PROJECT_CHARTER.md` is dropped as the main objective and parked as a separate, lower-priority future project.

## New mission
Simulate the work of a systematic quant researcher at a crypto trading firm: discover, validate, and combine a STABLE of trend-following / momentum alphas that are (1) market-neutral (near-zero beta to the crypto market) and (2) weakly correlated with each other, then assemble them into a combined market-neutral book. The deliverable is a rigorous, well-documented research process and alpha library that demonstrates professional-grade capability to recruiters.

## Why this framing
Two properties define the quality of the work:
- **Market-neutral:** each alpha is beta-neutral (long-short, hedged against the dominant BTC market factor), so it harvests the momentum spread rather than market direction.
- **Weakly correlated:** the alphas diversify each other. Combining several weakly-correlated moderate-Sharpe alphas produces a far higher portfolio Sharpe than any single one (the fundamental law of active management: skill times breadth). The goal is a stable of diversifying signals, not one killer alpha.

## What this IS
- Alpha research: signals that predict returns, judged on risk-adjusted, regime-robust, out-of-sample, multiple-testing-aware terms.
- Market-neutral long-short construction (beta-neutral), assuming the firm-standard ability to short via perps.
- A measured correlation structure across alphas, used to select and combine a weakly-correlated subset.
- Firm-grade sizing: per-name inverse-vol, a covariance/factor risk model, a portfolio vol target, and caps.

## What this is NOT (deliberately abstracted away)
- Execution microstructure (order routing, TWAP/VWAP, venue selection): a separate execution function. Assume target positions are achievable at a modeled cost.
- Instrument structuring (perp vs future vs option, collateral/margin mechanics): financial engineering. Assume perp access; model funding as a cost/credit at the realism layer.
- Retail $10k deployment: dropped as primary.

## The researcher's abstraction level
Work in target exposures / positions in the underlying coins, plus a reasonable cost and funding model. Do not micro-optimize execution or contract choice, but stay cost- and capacity-aware, because those assumptions decide whether an alpha is real net.

## Discipline (unchanged, and the whole point)
Clean broad data, gross first then a realism layer, regime-sliced, walk-forward, deflated Sharpe, an append-only trial ledger, and an untouched OOS vault. Market-neutrality is structural (long-short), not a cost.

## Success criterion
A repo and report a crypto quant hiring manager would read and conclude: this person understands alpha discovery, market-neutral portfolio construction, alpha diversification, and the difference between a backtest and an edge.
