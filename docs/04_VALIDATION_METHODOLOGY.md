# Validation and Anti-Overfitting Methodology

**Purpose.** This document is the project's defense against its most likely failure mode: fooling ourselves. It explains why backtest results on our data are fragile, quantifies exactly how fragile, and gives Claude Code concrete procedures to implement in Phase 2 and beyond. Every candidate strategy must pass the checklist in Section 7 before it touches real capital.

**Our specific situation, stated once so the whole document can refer to it:**

- Data: 721 daily candles per coin (2024-07-10 to 2026-06-30), which is about 104 weekly rebalance observations. After the 200-day warmup used in Stage 1C, the common evaluation window contains only about 75 weekly rebalances.
- Universe: median ~13 eligible names; a top-3 cross-sectional portfolio is a concentrated bet, not a diversified factor.
- Costs: Kraken spot fees are 0.25% maker / 0.40% taker per side, plus spread and slippage. A taker round trip is ~0.80% before spread.
- Central hypothesis (pre-registered in the charter and progress log): cross-sectional momentum may not survive these costs at weekly turnover. Time-series momentum probably survives better. Our job is to measure this, not to rescue the strategy.

The single organizing principle: **with this little data, the backtest can reject strategies but it can almost never confirm them.** Everything below follows from that.

---

## 1. The core danger: overfitting and multiple testing

### 1.1 How false winners are manufactured

Every time we run a backtest variant (a different lookback, a different skip, a different top-N, a different rebalance day) we draw another sample from a noisy distribution. If the true edge of every variant were exactly zero, the measured Sharpe ratios would still scatter around zero with a large standard error (Section 3 quantifies it: about 0.7 in annualized units on our sample). Pick the best of K such draws and you have not found an edge, you have found the right tail of a noise distribution.

The mathematics of this is standard extreme-value theory: the expected maximum of K independent standard normal draws grows like sqrt(2 ln K). Bailey, Borwein, Lopez de Prado, and Zhu make exactly this argument in "Pseudo-Mathematics and Financial Charlatanism" (2014): given enough trials, a "significant" backtest is guaranteed even when no strategy works, and the more you search, the better the best fake looks.

Apply it to us. Our annualized Sharpe standard error is roughly 0.71 (Section 3). Then the expected best Sharpe from K trials of pure noise is approximately:

```
E[max SR over K noise trials] ~ 0.71 * sqrt(2 * ln K)

K = 10   ->  ~1.5
K = 20   ->  ~1.7
K = 50   ->  ~2.0
K = 100  ->  ~2.2
```

Read that table twice. The Stage 1C grid alone is 10 to 11 runs. **If every strategy in our grid were worthless, we should still expect the best one to show an annualized Sharpe near 1.5 on our window.** A backtested Sharpe of 1.5 on our data, selected as the best of a modest grid, is therefore approximately what zero skill looks like. This is not pessimism, it is arithmetic.

### 1.2 The trial counter

The correction for multiple testing requires knowing how many tests were run. Almost nobody records this, which is why Lopez de Prado calls selection bias under multiple testing the number one reason quantitative funds' backtests fail to materialize live (Advances in Financial Machine Learning, ch. 11 to 14). We will record it.

**Procedure (Claude Code, from Phase 2 onward):** maintain `research/TRIALS_LEDGER.csv` with one row per backtest actually executed: `date, run_id, strategy_family, full_parameter_dict, data_window, gross_or_net, sharpe, maxdd, turnover, why_run`. The ledger is append-only, like the progress log. Runs that "did not count" count. Runs on old data count. Aborted ideas count if an equity curve was produced. K, the trial count used in the deflated Sharpe ratio, is the number of rows in this file for the relevant strategy family, not the number of runs we feel like remembering.

### 1.3 The Deflated Sharpe Ratio (DSR), intuition

Bailey and Lopez de Prado (2014) formalize the fix. The Probabilistic Sharpe Ratio (PSR) asks: given the sample length and the non-normality of returns (skew, fat tails, both severe in crypto), what is the probability that the true Sharpe exceeds some benchmark? The **Deflated Sharpe Ratio** sets that benchmark not at zero but at the expected maximum Sharpe of K noise trials:

```
SR_benchmark = sqrt(V[SR]) * ( (1 - gamma) * Z_inv(1 - 1/K) + gamma * Z_inv(1 - 1/(K*e)) )
```

where V[SR] is the cross-trial variance of the Sharpe estimates, gamma is the Euler-Mascheroni constant (~0.5772), and Z_inv is the inverse standard normal CDF. A strategy is credible only if its observed Sharpe clears this deflated hurdle with high probability after adjusting for skewness and kurtosis. The intuition is simply: you must beat the best fake, not zero.

**Procedure:** whenever we report a "best" configuration, we also report its DSR computed with K taken from the trials ledger. If DSR < 0.95 (i.e. we cannot say with 95% confidence that the true Sharpe beats the noise-maximum benchmark), the result is labeled "indistinguishable from selection noise" in the results file. On our sample length, expect this label often. That is the honest state of knowledge.

### 1.4 Probability of Backtest Overfitting (PBO)

Bailey, Borwein, Lopez de Prado, and Zhu (2017) define PBO as the probability that the configuration chosen because it was best in-sample turns out to be below the median configuration out-of-sample. Their estimation method, Combinatorially Symmetric Cross-Validation (CSCV), is directly implementable on our data:

1. Split the return matrix of all trial configurations into S equal time blocks (for us: S = 8 blocks of about 13 weeks).
2. For every combination of S/2 blocks as "in-sample" (70 combinations for S = 8), pick the best configuration in-sample, then record its performance rank on the complementary blocks.
3. PBO is the fraction of combinations where the in-sample winner ranks in the bottom half out-of-sample.

A PBO near 0.5 means in-sample selection carries no information; the winner is as likely as not to be a loser. Lopez de Prado suggests treating PBO above roughly 0.2 to 0.3 as a serious warning. **Procedure:** Claude Code implements CSCV as a utility in `xmom/validation.py` once Phase 2 grids exist, and every parameter sweep reports PBO alongside the winner's stats. Warning: with 8 blocks of 13 weekly observations each, PBO itself is noisy on our data; we use it as a red-flag detector, not a precise estimate.

---

## 2. In-sample, out-of-sample, and walk-forward with only two years

### 2.1 What we can honestly do

The textbook prescription is a long training window, a locked-away test set, and years of walk-forward. We have 104 weekly observations covering essentially one crypto regime cycle fragment. Pretending otherwise is worse than admitting it. Our walk-forward is therefore a **process check, not a proof**: it can catch gross overfitting (a strategy whose chosen parameters flip wildly between folds, or whose out-of-sample performance collapses) but it cannot certify a fine performance ranking.

### 2.2 The structure we will use

**Anchored walk-forward, quarterly refits:**

- Initial training window: the first 52 weeks.
- Test blocks: four sequential 13-week blocks (weeks 53 to 65, 66 to 78, 79 to 91, 92 to 104).
- At each refit date, select parameters using only data up to that date (anchored, i.e. expanding window; with data this short, discarding early data via a rolling window throws away too much).
- Concatenate the four out-of-sample blocks into one stitched OOS return series of ~52 weekly observations. All headline "out-of-sample" numbers come from this stitched series only.

That is 4 folds. Not 12, not 20. Four. Anyone reviewing this project should see immediately that our OOS evidence is 52 weekly observations, with an annualized Sharpe standard error near 1.0 (Section 3). We state this in every results report.

**Rules that make it honest:**

1. The parameter grid searched at each refit is fixed in advance and written in the spec document before the first run (Section 5). No adding grid points after seeing fold results.
2. The stitched OOS series is computed once per registered experiment. Re-running walk-forward with a modified grid is a new experiment: new ledger entries, K goes up, DSR hurdle goes up.
3. If the selected parameters differ sharply across the four refits (e.g. lookback jumping from 14 to 90 days), that instability is itself a failure signal, reported explicitly.
4. Between training and test data we respect the signal lookback as an embargo: a signal computed at the end of training already contains the last L days, so no test-block information may leak into parameter selection. Our engine's t to t+1 shift handles the one-day case; the walk-forward harness must also ensure refit dates use only data strictly before the test block. (This is the small-scale version of the purging and embargoing Lopez de Prado prescribes in Advances in Financial Machine Learning, ch. 7.)

### 2.3 Extending history changes everything

Kraken's REST endpoint capped us at 721 candles, but Kraken publishes full downloadable historical archives, and several coins have 8+ years of daily data on major venues. Going from 104 to 400+ weekly observations halves the Sharpe standard error and multiplies the number of honest walk-forward folds by four, including folds that contain the 2021 to 2022 regime change, which is precisely the kind of environment a long-only momentum book must survive. **Priority statement: acquiring deeper history (Kraken archives, or a carefully documented splice with another venue's data for signal formation only) is the single highest-value validation investment available to this project, worth more than any amount of additional testing on the current window.** Splices must be logged in the data-quality note with exact sources and join dates.

---

## 3. The small-sample problem: what 104 weekly observations can and cannot say

### 3.1 The standard error of a Sharpe ratio

For approximately iid returns, the standard error of an estimated per-period Sharpe ratio sr from N observations is (Lo, 2002):

```
SE(sr) ~ sqrt( (1 + sr^2 / 2) / N )
```

Annualizing weekly numbers multiplies both the Sharpe and its standard error by sqrt(52). For small sr the annualized standard error is approximately:

```
SE(SR_annual) ~ sqrt( 52 / N )

N = 104 weeks (full window)      ->  SE ~ 0.71
N = 75 weeks (post-warmup)       ->  SE ~ 0.83
N = 52 weeks (stitched OOS)      ->  SE ~ 1.00
```

And this is the optimistic iid case. Crypto returns are fat-tailed and negatively skewed, and momentum strategies have serially dependent exposures, all of which inflate the true standard error further (Lo 2002; Bailey and Lopez de Prado 2012 give the non-normal correction used inside PSR/DSR).

### 3.2 Concrete consequences, written as rules

Using the full window (SE ~ 0.71), a 95% two-sided confidence interval on any measured annualized Sharpe is roughly plus or minus 1.4. Therefore:

- **We cannot conclude a strategy has positive expected returns unless its full-window annualized Sharpe exceeds roughly 1.4, before any multiple-testing deflation.** After deflating for even 10 trials, the effective hurdle is above 2.
- **We cannot conclude strategy A beats strategy B unless their annualized Sharpe difference exceeds roughly 1.4 to 2.0** (the difference of two correlated estimates; correlation between our variants helps, but a gap under ~1 is uninterpretable). Ranking S5a vs S5b vs S5c on this window is reading tea leaves, exactly as the thin-universe warning in the Stage 1C spec says.
- **Minimum track record intuition** (Bailey and Lopez de Prado 2012): to establish at 95% one-sided confidence that a strategy with a TRUE annualized Sharpe of 1.0 is better than zero, we need N > 52 * 1.645^2, about 141 weeks, or 2.7 years, and more once non-normality is accounted for. Our paper-trading phase should be understood the same way: three months of paper results (13 weekly observations, SE ~ 2.0) can validate the plumbing and the cost model, and can catch a disaster, but it cannot validate the edge. Only the pre-agreed go/no-go criteria plus the backtest evidence can do that.

The correct posture on this sample: use the backtest to **reject** (a strategy that cannot even beat costs or the 1/N baseline gross is dead) and to **verify mechanics** (the engine tests, the cost accounting), and treat any positive result as provisional until history is extended.

---

## 4. Transaction costs and turnover as a validation axis

### 4.1 Gross and net are both mandatory

Every results table from Phase 3 onward reports each run twice: gross (cost hook at zero, comparable to Stage 1C) and net (full cost model). The gap between them is the cost drag, and for our central hypothesis the drag IS the result. A report showing only net hides how close the call was; a report showing only gross is fiction.

The arithmetic that makes this the main event: with one-sided annual turnover tau (the Stage 1C definition, 0.5 * sum |dW|), total traded notional per year is 2 * tau, and annual cost drag is approximately:

```
drag ~ 2 * tau * (fee_per_side + half_spread + slippage)

XSMOM at tau = 10 (1000% one-sided, mid-range of the S5 forecast):
  taker (0.40% + ~0.05%) ->  drag ~ 9.0% per year
  maker (0.25% + ~0.05%) ->  drag ~ 6.0% per year
TSMOM at tau = 4:
  taker  ->  drag ~ 3.6% per year
```

A drag of 6 to 9 points per year is the size of the entire documented crypto momentum premium in much of the literature. This is why Han, Kang and Ryu (2024) style results find cross-sectional profits evaporating net of costs, and it is why the project charter treats "does it survive costs" as the thesis rather than a checkbox.

### 4.2 Cost sensitivity curves

A single cost number is a point estimate of something we do not fully control (maker vs taker fills, spread at execution time, our own impact). So costs are a sensitivity axis, not a constant.

**Procedure (Claude Code, Phase 3):** for every candidate strategy, sweep effective one-way cost c over {0, 5, 10, 15, 20, 25, 30, 40, 60, 80} basis points and plot net annualized Sharpe and net CAGR against c. Report two derived numbers in the results table:

1. **Breakeven cost c\*:** the c at which net CAGR crosses the benchmark (equal-weight universe, and separately buy-and-hold BTC). If c\* is below our realistic cost estimate, the strategy is dead on this evidence.
2. **Cost margin:** c\* divided by the realistic cost estimate. We require margin >= 2 for any live deployment: the strategy must remain viable if trading turns out twice as expensive as modeled. Anything with margin between 1 and 2 is "survives on paper, too fragile to fund."

Realistic per-side cost estimate for us, to be refined with live paper fills: maker 0.25% plus half-spread (~0.01% majors, ~0.05 to 0.15% thin alts) if we accept fill risk on limit orders; taker 0.40% plus half-spread if we demand immediacy. Model taker as the base case and maker as the improvement scenario, never the reverse, until paper trading measures our actual fill mix.

Turnover itself is also a design lever to validate, not just measure: bands (trade only when the target weight moves more than x%), slower rebalance, and holding-period overlap all reduce tau. But each such variant is a new trial in the ledger.

---

## 5. Pre-registration discipline

The cheapest and most powerful anti-overfitting tool available to a two-person project is writing the hypothesis down before running the code. It converts "search until something works" into "test a stated prediction," and it makes the trial count auditable. This project already has the habit in embryo: the PROGRESS_LOG entry template has a "Hypothesis (if testing)" field, and the Stage 1C spec wrote predicted orderings before any run. We now make it a rule.

**The rule:** no backtest of a new strategy variant or parameter grid is run until a registration block exists. For small experiments this is a PROGRESS_LOG entry; for a named experiment (e.g. "Phase 3 cost study") it is a short section at the top of the results file, committed to git BEFORE results are generated (the git timestamp is the proof). The block contains:

1. The question, in one sentence.
2. The exact configurations to be run (the full grid, enumerated, which fixes K in advance).
3. The prediction: what we expect and why, including the ordering we would bet on.
4. The decision rule: what result would make us drop the idea, and what would make us continue. Written so that a hostile reader could apply it without us in the room.
5. The data window and whether costs are on.

After the run: results go in the same file below the registration, every executed configuration is appended to `research/TRIALS_LEDGER.csv` (Section 1.2), and the PROGRESS_LOG entry records prediction vs outcome. If we deviate from the registered grid mid-experiment (it happens), the deviation is logged as such, and the extra runs still count toward K. The one unforgivable move is the quiet one: running twenty variants, reporting three, and remembering none.

This also protects against the subtler leak: the researcher's own memory. Every look at the data informs the next idea, so even "new" hypotheses formed after Stage 1C are partially trained on our only dataset. We cannot eliminate that on a fixed window (one more reason extending history matters, since fresh data restores a genuine test set), but the ledger at least makes the total search visible so DSR can price it.

---

## 6. What validation cannot do

One paragraph of humility, so the checklist below is read correctly. Passing every procedure in this document does not prove the strategy works. It proves the strategy was not obviously manufactured by search, survives its own cost assumptions with margin, and behaved consistently across the few folds we have. On 104 weekly observations spanning a fragment of one crypto cycle, that is the ceiling. The real test is phased live capital with pre-agreed kill criteria, which is exactly why the charter phases in $1,000 to $2,000 before the full $10k, and why "the data says no" is a stated success outcome.

---

## 7. The validation checklist

A candidate strategy earns real capital only when every box is checked. Claude Code implements the automatable checks in `xmom/validation.py` and the results template; the owner signs off on the judgment calls. Any unchecked box means paper only.

**Mechanics and data integrity**
- [ ] Engine sanity tests pass on the exact code version used (BTC buy-and-hold reproduction, look-ahead guard, turnover ordering).
- [ ] Universe is point-in-time; no asset enters a backtest before its screen admission date; delisted/renamed assets handled and documented.
- [ ] Signal uses only data with timestamps <= t; walk-forward refits use only data strictly before each test block.

**Multiple-testing accounting**
- [ ] Experiment was pre-registered (grid, prediction, decision rule) before execution, verifiable by git history.
- [ ] Every executed run appears in `research/TRIALS_LEDGER.csv`; K for this strategy family is stated in the report.
- [ ] Deflated Sharpe Ratio computed with that K and with sample skew/kurtosis; DSR >= 0.95, or the result is explicitly labeled provisional and does not proceed to capital.
- [ ] PBO estimated via CSCV on the trial grid; PBO <= 0.25, and the number is reported with its own caveat about block count.

**Out-of-sample behavior**
- [ ] Anchored walk-forward run per Section 2.2; headline OOS stats computed only on the stitched ~52-week OOS series.
- [ ] Selected parameters are stable across refits (no regime-chasing jumps), and OOS Sharpe retains at least half of in-sample Sharpe.
- [ ] Strategy beats BOTH benchmarks (equal-weight universe and buy-and-hold BTC) net of costs on the OOS series, on risk-adjusted terms.

**Costs and capacity**
- [ ] Gross and net results both reported; cost sensitivity curve produced over 0 to 80 bps per side.
- [ ] Breakeven cost c\* and cost margin reported; margin >= 2 versus the taker-based realistic cost estimate.
- [ ] Modeled turnover is consistent with what the live order plan can actually achieve (order types, rebalance timing, thin-book alts flagged).

**Robustness and honesty**
- [ ] Results survive small perturbations: rebalance on a different weekday, lookback plus or minus ~20%, top-N plus or minus 1, with no sign flip in net excess return. (These perturbation runs are registered as such and go in the ledger, but are excluded from selection: they exist to test fragility, not to pick a better variant.)
- [ ] Single-name dependence checked: no more than half of total OOS profit attributable to one coin; report profit with the best coin removed.
- [ ] Statistical power statement included verbatim in the report: sample size, Sharpe standard error, and what the result therefore cannot claim (Section 3.2 language).
- [ ] The thin-universe concentration caveat from the Stage 1C spec is restated in the report.

**Deployment gate**
- [ ] Paper trading for a pre-agreed period reconciles live fills against modeled costs; realized cost per unit turnover within 1.5x of the model, and any excess triggers a cost-model revision before capital.
- [ ] Kill criteria written before deployment: max drawdown level that flattens to cash, maximum tolerated tracking gap between live and backtest behavior, and review dates.
- [ ] First tranche limited to $1,000 to $2,000 per the charter, scaling only after live reconciliation is clean.

---

## Sources

- Bailey, D. H. and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality." Journal of Portfolio Management 40(5). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, D. H., Borwein, J., Lopez de Prado, M., and Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." Notices of the American Mathematical Society 61(5). https://www.ams.org/notices/201405/rnoti-p458.pdf
- Bailey, D. H., Borwein, J., Lopez de Prado, M., and Zhu, Q. J. (2017). "The Probability of Backtest Overfitting." Journal of Computational Finance 20(4). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Bailey, D. H. and Lopez de Prado, M. (2012). "The Sharpe Ratio Efficient Frontier." Journal of Risk 15(2). Includes the Probabilistic Sharpe Ratio and Minimum Track Record Length. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643
- Lopez de Prado, M. (2018). Advances in Financial Machine Learning. Wiley. Especially ch. 7 (cross-validation, purging, embargo), ch. 11 to 14 (backtesting dangers, backtest statistics). https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086
- Lo, A. W. (2002). "The Statistics of Sharpe Ratios." Financial Analysts Journal 58(4). https://www.tandfonline.com/doi/abs/10.2469/faj.v58.n4.2453
- Harvey, C. R. and Liu, Y. (2015). "Backtesting." Journal of Portfolio Management 42(1). Multiple-testing haircuts for Sharpe ratios. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489
- Harvey, C. R., Liu, Y., and Zhu, H. (2016). "... and the Cross-Section of Expected Returns." Review of Financial Studies 29(1). Why published factor discoveries need a t-stat hurdle near 3. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314
- Kraken fee schedule (maker 0.25% / taker 0.40% at our tier). https://www.kraken.com/features/fee-schedule
- Kraken historical data archives (path to extending history past the 720-candle REST cap). https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data

Related internal documents: `docs/00_PROJECT_CHARTER.md` (risk non-negotiables, phased capital), `docs/03_STRATEGY_SPECS.md` (engine contract, thin-universe warning, predicted orderings), `PROGRESS_LOG.md` (pre-registration habit), `research/phase1a_data_quality.md` (data provenance).

---

*Living document. Material changes are logged in PROGRESS_LOG.md with a date and rationale, per project convention.*
