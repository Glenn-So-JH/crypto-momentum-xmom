# Phase 2 Design: From Validated Baselines to Our Own Defensible Signal

**Goal of Phase 2:** take the validated engine and the classic-strategy intuition from Phase 1 and produce ONE named candidate strategy, with frozen parameters, that we would be willing to defend in front of a skeptical quant and hand to the full-cost realism pass. Not the best strategy we can imagine. The simplest strategy the evidence actually supports.

A note on numbering: the original roadmap put "signal research" in Phase 2 and "robustness and validation" in Phase 4. Experience from Phase 1 says that split is backwards: choosing a signal without walk-forward discipline is exactly how overfitting happens, so this document pulls the validation harness forward into Phase 2 itself. The full transaction-cost model remains Phase 3's job, but no decision in Phase 2 is allowed to ignore costs (Section 5). The roadmap's intent is preserved; the order of operations is corrected.

---

## 1. The earn-complexity principle, applied to signals

Phase 1's discipline was "validate the instrument before the experiment." Phase 2's discipline is the roadmap's own rule: **earn complexity.** Every candidate signal must first exist as a transparent base case that a finance-literate human can explain in two sentences. Enhancements are then admitted one at a time, each pre-registered as a hypothesis, each required to beat the thing it replaces, and each rejected by default. The burden of proof is always on the more complex version.

This matters doubly here because our dataset is thin. The Phase 1 panel is roughly two years of daily data; after the 200-day warmup the common evaluation window contains only about 75 weekly rebalance decisions. With that little data, a flexible search over many variants will find a "winner" by luck alone with near certainty. The only defenses are: a strong prior from the literature (we have one), a tiny pre-registered search space, robustness checks that punish fragile parameters, and honest multiple-testing accounting. Phase 2 is built around those four defenses.

What the evidence base (docs/RESEARCH_crypto_momentum.md, Phase 0 and 1 findings) tells us going in, stated as priors we will test rather than assume:

1. Crypto momentum lives at short lookbacks, roughly 7 to 28 days, and decays or flips to reversal beyond about a month.
2. Time-series (absolute) momentum is more robust than cross-sectional (relative) momentum, especially net of costs.
3. The two best-evidenced overlays are a BTC moving-average regime gate and volatility targeting.
4. Our universe is thin (median ~13 names), which specifically hurts cross-sectional ranking and makes top-N portfolios concentrated.
5. Real Kraken costs (roughly 40 to 50 bps per side taker, ~25 bps maker) are the main threat, and turnover is the variable that decides whether the strategy lives.

## 2. The base case: long-only TSMOM with a BTC regime gate and volatility targeting

This is the strategy we build first, and the null hypothesis every enhancement must beat. Each of its three components is the best-evidenced member of its class, and each was already exercised in some form in Stage 1C (S4 for the signal, S3 for the gate concept, and the metrics layer for vol measurement), so nothing here is exotic.

**Signal.** Per asset, time-series momentum at a short lookback: on each rebalance day, an eligible coin is a candidate holding if its own trailing L-day return is positive, with L = 21 days as the primary and L = 14 as the secondary, both inside the evidenced 7-to-28-day band. No cross-asset comparison. This is Stage 1C's S4 moved to the horizon the crypto literature says the effect actually lives at (S4 used 90 and 30 days for calibration purposes; 21 is a hypothesis choice, registered before running).

**Regime gate.** A single portfolio-level switch on BTC: when BTC's price is at or below its 200-day simple moving average, the entire book goes to cash regardless of per-coin signals. Rationale: crypto is one beta in a crash, per-coin TSMOM already de-risks but reacts coin by coin, and the literature says a market-level trend gate is the cheapest large improvement available. The gate is binary and evaluated only at rebalance, so it adds essentially no turnover of its own except at regime flips.

**Sizing and vol targeting.** Among the coins that pass both the signal and the gate, weight inversely to each coin's trailing volatility (so a 100%-vol meme coin gets less capital than 40%-vol BTC), cap any single name at 25% of the book, then scale the whole portfolio so its forecast annualized volatility is at or below a target, with 30% as the primary target. Because we are long-only and unlevered, vol targeting can only de-risk: if forecast vol is below target the portfolio simply holds its weights plus cash, never leverages up. The residual is always cash earning zero.

**Rebalance.** Weekly at the Monday close, per the Stage 1C convention, with the sacred t-to-t+1 lag unchanged. One addition, from Section 5: a no-trade band, so positions are only traded when the target weight differs from the drifted current weight by more than a threshold. This is the first time drift-aware weights enter the project, and it is deliberate: turnover control is part of the strategy design, not a Phase 3 patch.

**What success looks like.** On the common window, net of the provisional cost assumption (Section 5), the base case should: beat equal-weight (S2) and buy-and-hold BTC (S1) on Sharpe and Calmar; show materially shallower max drawdown than both; hold up across the walk-forward folds rather than earning everything in one quarter; and keep annualized one-sided turnover in the low hundreds of percent, where weekly costs are survivable. It does NOT need to beat BTC on total return in a bull window; a trend strategy giving up upside for drawdown control is behaving correctly.

**What failure looks like, stated in advance.** The base case is in trouble if: the result flips sign between L = 14 and L = 21 or between gate lengths 100 and 200 (parameter cliff, likely noise); essentially all profit comes from a single episode such as one alt rally; the vol-targeted version underperforms the untargeted version badly (suggesting our vol forecast is noise at this breadth); or net-of-cost performance falls below equal-weight. Any of these is reportable, none is hidden, and a clear failure sends us back to the signal, not forward to more complexity.

## 3. The challenger: cross-sectional top-N momentum, run to be falsified

Cross-sectional momentum is the project's founding thesis (it is in the repo name), so it gets a fair, pre-registered head-to-head rather than a quiet burial. The challenger is Stage 1C's S5 upgraded to the same overlays as the base case, so the comparison isolates the one real difference, relative versus absolute selection: rank eligible coins by trailing L-day return (same L as the base case, with a skip variant per Section 4), hold the top 3, inverse-vol weighted, same BTC gate, same vol target, same no-trade bands, same rebalance.

The prior, from both the literature and our thin-universe warning in the Stage 1C spec, is that the challenger loses: ranking 13 names gives little cross-sectional information, top-3 concentration makes the statistics noisy, and XS turnover is structurally higher, which costs more. The head-to-head is designed so that either outcome is useful. If the challenger cannot beat the base case net of provisional costs, we keep the base case and the XS thesis is honestly falsified on our venue and universe, which is a strong finding and a better story than a forced win. If the challenger wins convincingly (Section 6 defines convincingly), we take that seriously, because it would mean the thin-universe penalty is smaller than feared. The one outcome that is not allowed is a draw that we resolve by picking our favorite: ties go to the base case, because it is simpler and cheaper to trade.

## 4. The enhancement menu, ranked

Each enhancement is a hypothesis with a rationale and a fixed evaluation. Enhancements are tested one at a time, on top of whichever strategy survived Section 3, in the order below (expected value per unit of implementation cost, highest first). Every test is logged in the trial register (Section 6) whether it passes or fails, and the default outcome is rejection.

| # | Enhancement | Hypothesis | Rationale | Evaluation | Cost |
|---|---|---|---|---|---|
| E1 | Lookback ensemble | Averaging the signal across L = 7, 14, 28 beats any single L, net of costs, by reducing parameter luck | Diversifies over the one parameter we know matters most; ensembles of lookbacks are standard trend practice and cut the risk that our single L was an accident of this window | Base case vs ensemble on identical harness; must improve walk-forward Sharpe or reduce its dispersion across folds without raising turnover materially | Low |
| E2 | Asset-level vol scaling refinement | Sizing by inverse vol (already in base) with a shorter vs longer vol window changes results only mildly; if it changes them a lot, vol estimation is doing hidden work | Checks whether the sizing layer is robust machinery or a fragile fitted parameter | Sensitivity sweep of the vol estimation window (e.g. 20 vs 60 days); adopt the simplest setting inside the stable region | Low |
| E3 | Skip-day | Skipping the most recent 1 to 3 days of the formation window improves the signal by removing short-term reversal contamination | Classic Jegadeesh-Titman logic scaled to crypto horizons; S5b already piloted k = 7; crypto reversal is documented at very short horizons | Same-strategy A/B at k in {0, 1, 3}; must improve net Sharpe with no turnover penalty; if flat, keep k = 0 (simpler) | Low |
| E4 | Signal winsorizing | Capping extreme trailing returns before ranking or sign-taking reduces the impact of one-off spikes (exploit pumps, listing pops) and improves stability more than it costs in return | Thin universe means one crazy print can dominate a rank or flip a sign; winsorizing is cheap insurance | A/B with returns winsorized at fixed quantiles; judged mainly on drawdown, fold dispersion, and turnover, not raw Sharpe | Low |
| E5 | TS+XS combination | Requiring both absolute momentum (TS positive) and relative strength (top half of XS rank) beats either alone | The two signals fail differently: TS holds mediocre coins in broad rallies, XS holds least-bad losers in crashes; the intersection may keep the winners of both filters | Three-way comparison, TS vs XS vs intersection, all with identical overlays; the combo must beat BOTH parents net of costs to be adopted | Medium |
| E6 | Momentum + low-vol multi-factor | Tilting the momentum book toward lower-volatility names (beyond inverse-vol sizing) improves risk-adjusted return | A documented low-vol effect exists in crypto, and it naturally offsets momentum's taste for high-beta names | Blend rank (momentum rank plus low-vol rank) vs momentum alone; adopted only if it beats E5's winner net of costs | Medium |
| E7 | Richer regime conditioning | A second regime dimension (e.g. BTC realized-vol level, or universe breadth: fraction of coins above their own MA) improves on the binary 200-day gate | The binary gate is crude; vol regimes and breadth are the two best-evidenced refinements | Gate A/B on identical strategy; must improve Calmar and fold consistency; heavily penalized in the trial register because regime rules on ~75 weekly points are prime overfitting territory | Medium to high |

Hard cap for Phase 2: E1 through E4 are in scope by default; E5 and E6 run only if the earlier stages finish cleanly and the trial budget (Section 6) allows; E7 is explicitly last and may be deferred to a later phase entirely. Anything not on this menu is out of scope for Phase 2, full stop. New ideas go to the research backlog, not the harness.

## 5. Turnover and cost-awareness as first-class design constraints

Phase 0 measured the wall precisely: Kraken taker 40 bps, maker 25 bps per side, spreads on majors negligible by comparison, and the Phase 1A prior says a weekly top-3 XS book can turn over 500 to 1500% a year. At 40 to 50 bps per side, 1000% one-sided annual turnover costs roughly 8 to 10% of the book per year. That is the entire expected edge. So cost-awareness cannot wait for Phase 3; it shapes what we build now, in three ways.

**A provisional cost lens on every result.** The engine's cost hook, dormant in Phase 1, is switched on for all Phase 2 decision tables at a flat provisional assumption: 50 bps per side (conservative taker-plus-slippage) as the headline, with 25 bps (maker fill) reported alongside. This is deliberately crude; the honest, calibrated cost model with slippage and partial-fill assumptions remains Phase 3's deliverable. But every keep/kill decision in Phase 2 is made on the 50 bps column, never on gross numbers. Gross results are still reported (they connect to Phase 1 and the literature), they just do not decide anything.

**Rebalance bands / no-trade zones as part of the strategy.** The engine gains drift-aware target weights and a no-trade band: at rebalance, a position is only traded if the target differs from the current drifted weight by more than a threshold (initial setting: 20% of the target in relative terms, tested against 10% and 30%). Signal flips (a coin entering or leaving the holder set, or the gate flipping) always trade; the band only suppresses cosmetic re-truing. Expected effect, to be measured: a large turnover reduction for a small tracking cost. The band setting is chosen on turnover-versus-Sharpe grounds inside the harness and then frozen with the rest of the candidate.

**Maker-order awareness, without pretending.** A weekly-rebalanced strategy is not latency-sensitive, so in live trading we can plausibly work limit orders and pay maker fees (25 bps) rather than crossing the spread. Phase 2 assumes this only as the optimistic bound (the 25 bps column) and never as the base case, because maker fills are uncertain: an unfilled limit order on a moving coin is its own cost. Quantifying fill rates is a Phase 6 paper-trading question. What Phase 2 does record is each candidate's cost sensitivity: the per-side cost level at which its net Sharpe drops to equal-weight's. If a candidate only works below 30 bps per side, it is a maker-or-nothing strategy and we say so out loud.

## 6. Validation methodology and decision gates

**Pre-registration.** Before any run, the hypothesis, exact parameters, and predicted outcome go into `PROGRESS_LOG.md`, exactly as Stage 1C did with its predicted orderings. Results are compared to the prediction, and surprises are investigated as possible bugs before being celebrated as findings.

**Walk-forward.** All headline comparisons run through a walk-forward harness: anchored expanding training windows with quarterly test folds across the common window. With ~2 years of data this yields only 4 to 6 out-of-sample folds, which is thin, and we say so in every results table. The harness reports per-fold performance, and fold consistency (does the strategy earn in most folds, or one?) carries as much weight as the aggregate Sharpe. Parameter choices, where any are made, are made inside training folds only.

**Parameter neighborhoods, not points.** No parameter is accepted on its own; we always run its neighbors (L = 14/21/28, gate = 100/200, vol target = 20/30/40, band = 10/20/30) and require the chosen point to sit inside a plateau, not on a cliff. A result that dies one notch away is treated as noise.

**Deflated Sharpe and the trial register.** Every configuration ever run in Phase 2 is logged in a single trial register (a table in the results doc: run ID, date, hypothesis, parameters, outcome). The register's count feeds a deflated Sharpe ratio calculation for the final candidate: the observed Sharpe is judged against the distribution of the best of N tries, using the true N, not the flattering one. Honesty clause: with roughly 75 weekly decisions, the deflated Sharpe on this window will almost certainly NOT reach conventional significance for any realistic strategy. We compute it anyway, as a guardrail and a habit, and we rest the actual decision on the tripod of literature prior plus fold consistency plus parameter plateau, stated explicitly in the final memo. Anyone claiming statistical proof from two years of crypto data is lying; we will not.

**The thin-data mitigation worth paying for.** The single best statistical upgrade available is more history: Kraken's downloadable OHLCVT archives (flagged since Phase 0) can extend the panel from ~2 years to 5+ for the majors, multiplying our weekly observations and adding the 2022 bear market, a regime our current window lacks entirely. This is proposed as an optional but strongly recommended part of Stage 2A. It is the difference between "the gate never really got tested" and "the gate was tested by the worst drawdown in the sample."

**Decision gates.**

- Gate 2A: the harness is trusted. Walk-forward splitter, cost lens, no-trade bands, and deflated Sharpe calculator exist, are unit-tested (including a test that the walk-forward folds cannot leak future data), and reproduce a Stage 1C result exactly when run in degenerate single-fold mode.
- Gate 2B: the base case has a verdict. Pre-registered predictions compared against results, success/failure criteria from Section 2 applied, written up. If the base case fails outright, Phase 2 pauses for a rethink rather than proceeding to decorate a corpse.
- Gate 2C: the head-to-head has a winner. The challenger is kept only if it beats the base case on net Sharpe AND fold consistency at the 50 bps cost lens; ties and ambiguity go to the base case. Written justification either way.
- Gate 2D (Phase 2 exit): one named candidate with frozen parameters, its full trial register, its cost-sensitivity curve, and a results memo that a skeptic could audit. That bundle is the input to Phase 3's honest cost pass.

## 7. Explicit non-goals for Phase 2

No machine-learned price prediction of any kind (no gradient boosting, no neural nets, no regression stacks); the earned-complexity bar for ML is a validated simple strategy plus a demonstrated failure mode ML would fix, and we have neither yet. No leverage, no shorting, no derivatives, no stablecoin-pair arbitrage. No new venues and no universe expansion beyond possibly deepening history for the existing names. No intraday signals or sub-weekly rebalancing. No portfolio of strategies; one base case at a time, per the charter. No perfecting the cost model (Phase 3) and no execution engineering (Phase 6). And no unregistered experiments: a run that is not in the trial register does not exist, and its results may not be used.

## 8. Staged handoffs to Claude Code

Same discipline as Phase 1: each stage is a self-contained handoff in `docs/HANDOFFS.md` with acceptance criteria, and each gate must pass before the next stage starts.

- **Stage 2A: Research harness (plus optional data deepening).** Build the walk-forward splitter, the drift-aware engine extension with no-trade bands, the provisional cost lens (25/50 bps columns), the trial-register template, and the deflated Sharpe calculator. Unit tests: fold-leak guard, band logic on synthetic drift, cost accounting on a known trade sequence, and exact reproduction of one Stage 1C run in degenerate mode. Optional task, owner to decide before the handoff: ingest Kraken OHLCVT archives to extend the panel for the majors. Gate: 2A above.
- **Stage 2B: Base case.** Implement and pre-register the Section 2 strategy (TSMOM L = 21/14, BTC 200-day gate, inverse-vol sizing with 25% cap, 30% vol target, weekly with bands). Run it and its parameter neighbors through the harness, produce the verdict against the Section 2 success/failure criteria. Gate: 2B above.
- **Stage 2C: Challenger head-to-head.** Implement the Section 3 XS challenger with identical overlays, run the pre-registered comparison, apply the keep/kill rule. Deliverable: a short written decision with the evidence table. Gate: 2C above.
- **Stage 2D: Enhancement ladder and freeze.** Run E1 through E4 (and E5/E6 only if budget allows) one at a time on the surviving strategy, updating the trial register each time. Freeze the final candidate's parameters, compute its deflated Sharpe with the true trial count, produce the cost-sensitivity curve and the Phase 2 results memo (`research/phase2_results.md`). Gate: 2D above, which is the Phase 2 exit.

## Phase 2 success gate (restated)

Phase 2 is done when one candidate strategy exists with frozen parameters, an auditable trial register, walk-forward evidence of fold-consistent behavior, a stated cost-sensitivity threshold, and a written memo that is honest about what two years of data cannot prove. Profitability net of the provisional cost lens is expected but not the gate; an honestly documented failure of the whole momentum family on this venue would also pass, and would redirect the project rather than end it.

## LinkedIn angle

"I gave my own favorite strategy a fair trial and a presumption of guilt. Here is the base case it had to beat, the trial register that counted every experiment against me, and why with two years of data the most important number in my backtest is the one I refuse to claim."
