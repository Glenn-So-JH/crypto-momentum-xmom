# Stage 1C Strategy Specification Library

**Purpose.** This document specifies, unambiguously, the six classic strategies we run through the Phase 1 backtest engine to (a) validate the engine against known behavior and (b) build intuition for how each signal family behaves in crypto. Claude Code implements directly from this document. Every parameter has a named default; the full run list is in the Parameter Grid at the end.

Costs are OFF (cost hook set to zero) for all Stage 1C runs. We are measuring raw signal behavior, not net profitability.

---

## 0. Shared conventions (read first, applies to every strategy)

### 0.1 Notation

- `P_i(t)`: daily close of asset `i` on date `t` (UTC daily candles from the cleaned panel).
- `r_i(t)`: simple daily return, `r_i(t) = P_i(t) / P_i(t-1) - 1`.
- `U_i(t)`: point-in-time universe mask, 1 if asset `i` passes the liquidity screen on date `t`, else 0. Produced by `xmom.universe`. Median breadth is ~13 names.
- `W_i(t)`: target weight for asset `i` decided at the close of date `t`, using only data with timestamps `<= t`.
- Cash is the implicit residual: `cash(t) = 1 - sum_i W_i(t)`. Cash earns exactly 0.
- Trailing return with lookback `L` and skip `k` (both in calendar days, since crypto trades daily):

```
R_i(t; L, k) = P_i(t - k) / P_i(t - L) - 1        with 0 <= k < L
```

  `k = 0` gives the plain trailing L-day return `P_i(t) / P_i(t - L) - 1`.
- N-day simple moving average, inclusive of day `t`:

```
SMA_i(t; N) = (1 / N) * sum_{j=0}^{N-1} P_i(t - j)
```

### 0.2 Engine contract (restated, binding)

A strategy is a function that maps the data available up to and including date `t` to a target weight vector `W(t)` with `W_i(t) >= 0` for all `i` and `sum_i W_i(t) <= 1`. The engine applies `W(t)` to the returns from `t` to `t+1` (the built-in `.shift(1)`), so the portfolio return credited on date `t+1` is:

```
r_p(t+1) = sum_i W_i(t) * r_i(t+1)
```

Strategies never apply the shift themselves. A strategy that peeks past `t` is a bug; the look-ahead guard test exists to catch exactly that.

### 0.3 Rebalance convention

- **Rebalance days:** every Monday present in the date index (crypto trades every calendar day, so this is every Monday). Formally: `t` is a rebalance day iff `t.weekday() == 0`. Signals are computed at the Monday close and, per the engine contract, first earn the Monday-close to Tuesday-close return.
- **Between rebalances:** the target weight vector is held constant at the last rebalance value. Because the engine is vectorized and applies target weights daily, this implies costless daily re-truing back to the target between rebalances. That is a stated Stage 1C simplification; drift-aware weights arrive with the cost layer in Phase 3.
- **Mid-week universe exit:** if asset `i` drops out of the universe between rebalances (`U_i(t) = 0` while its held target is positive), force `W_i(t) = 0` immediately and do NOT renormalize; the freed weight sits in cash until the next rebalance. Implemented as `W(t) = W(last rebalance) * U(t)` elementwise on non-rebalance days.
- **Buy-and-hold BTC is the one exception:** it sets weights once at inception and never rebalances (Section 1).

### 0.4 Eligibility rule

On a rebalance day `t`, asset `i` is **eligible** for a signal with lookback `L` and skip `k` iff all of:

1. `U_i(t) = 1` (in universe on `t`, point in time),
2. `P_i(t - L)` and `P_i(t - k)` are both non-NaN (enough clean history for the signal),
3. `P_i(t)` is non-NaN (tradeable today).

Assets failing eligibility get weight 0. No forward-filling of prices to fake eligibility.

### 0.5 Warmup and common evaluation window

The longest lookback in the grid is `N = 200` (SMA filter). To make the comparison table apples-to-apples, ALL strategies are evaluated on one common window: from the first rebalance day at least 200 days after the start of the cleaned panel, to the last date in the panel. Signals may use data before the window start (that is what the warmup is for); equity curves all start at 1.0 on the same date.

### 0.6 Tie-breaking

Whenever a rank cutoff must split tied signal values, break ties by ticker symbol in ascending alphabetical order (deterministic, reproducible). Ties in float momentum values are rare but must not make runs non-deterministic.

---

## 1. S1: Buy-and-hold BTC (engine calibration baseline)

**(a) Description and intuition.** Put 100% into BTC on day one and never touch it. This is not a strategy, it is a calibration target: the engine's equity curve must reproduce BTC's own price path exactly (up to the normalization to 1.0 at the window start). It also serves as the performance benchmark every other strategy is compared against.

**(b) Signal and weights.** For every date `t` in the evaluation window:

```
W_BTC(t) = 1.0
W_i(t)   = 0.0   for all i != BTC
```

Parameters: `asset = "BTC"` (named so the same code can calibrate on ETH later).

**(c) Rebalance rule.** None. Weights fixed at inception. (With a single asset there is no drift, so "hold targets constant" and "never trade" coincide.)

**(d) Expected behavior.** Equity curve identical to `P_BTC(t) / P_BTC(t_0)`. Over the 2024 to 2026 panel: high total return, high volatility (roughly 40 to 60% annualized), brutal drawdowns (historically 60%+ peak to trough across cycles; expect at least 25 to 35% inside our short window). Turnover ~0 after inception. Time-in-market 100%. Hit rate near 50 to 55% of days.

**(e) Reference.** No paper needed; it is the market benchmark. Conceptually it plays the role of the buy-and-hold benchmark in Faber (2007).

**(f) Engine unit-test property.** THE sanity test: assert `equity_curve == P_BTC / P_BTC[start]` elementwise within floating tolerance (e.g. `np.allclose` with `rtol=1e-10`). Any deviation means the engine (compounding, alignment, or the shift) is broken. Also confirms turnover accounting reports ~0 for a never-trading portfolio.

---

## 2. S2: Equal-weight in-universe, weekly rebalance (diversification baseline)

**(a) Description and intuition.** Own everything the liquidity screen admits, in equal parts, refreshed weekly. This is the "1/N" portfolio: the no-skill diversified basket. Every signal strategy must justify itself against this, not just against BTC, because in crypto a rising tide lifts all coins and a naive basket can look deceptively smart.

**(b) Signal and weights.** On each rebalance day `t`, let `E(t)` be the set of eligible assets (Section 0.4 with `L = 1`, `k = 0`, i.e. in universe with a valid close today and yesterday) and `n(t) = |E(t)|`:

```
W_i(t) = 1 / n(t)   if i in E(t)
W_i(t) = 0          otherwise
```

If `n(t) = 0` (should never happen with this universe), hold 100% cash. Parameters: none beyond the shared rebalance convention.

**(c) Rebalance rule.** Weekly per Section 0.3. Weights held constant between Mondays, universe-exit rule applies.

**(d) Expected behavior.** Return character between BTC and the average altcoin: more volatile than BTC alone in most regimes (alts have higher beta), but smoother than any single altcoin. Drawdowns similar to or worse than BTC's because alt correlations go to ~1 in selloffs; diversification in crypto is weaker than in equities. Turnover low but nonzero (weights shuffle as `n(t)` and relative prices change): expect roughly 10 to 50% annualized one-sided turnover. Time-in-market 100%.

**(e) Reference.** DeMiguel, Garlappi, and Uppal (2009), "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?", Review of Financial Studies.

**(f) Engine unit-test property.** Confirms (i) weights sum to exactly 1.0 on every rebalance day (budget constraint respected), (ii) the point-in-time universe mask is actually consumed (assert `W_i(t) > 0` implies `U_i(t) = 1` for all `t`), and (iii) the weekly rebalance schedule fires on Mondays only.

---

## 3. S3: Moving-average trend filter on BTC

**(a) Description and intuition.** Hold BTC when its price is above its own N-day average, otherwise sit in cash. The oldest trend rule there is: an asset above its long moving average is in an uptrend and worth holding; below it, the risk of a deep bear leg outweighs the upside. The point is not to beat buy-and-hold on return but to cut the catastrophic drawdowns while keeping most of the upside.

**(b) Signal and weights.** On each rebalance day `t`:

```
signal(t) = 1  if P_BTC(t) > SMA_BTC(t; N)
signal(t) = 0  otherwise

W_BTC(t) = signal(t)
W_i(t)   = 0            for all i != BTC
```

Strict inequality; `P = SMA` exactly means cash (arbitrary but fixed). Parameters and defaults: `asset = "BTC"`, `N = 200` (primary), `N = 100` (secondary run). BTC must have `N` non-NaN closes through `t`, guaranteed by the 200-day warmup.

**(c) Rebalance rule.** Weekly per Section 0.3: the filter is only evaluated at Monday closes, so an intra-week cross does not trade until the next Monday. Binary in/out, so each flip is a 100% one-sided trade.

**(d) Expected behavior.** Lower total return than buy-and-hold BTC in a mostly-up window (whipsaw cost plus lag re-entering), but materially smaller max drawdown, higher Calmar, and often comparable or better Sharpe. Time-in-market well below 100% (expect roughly 60 to 80%). Turnover low in absolute terms: a handful of flips per year, each worth 200% round-trip; expect roughly 2 to 8 flips/year, more for `N = 100` than `N = 200`. `N = 100` reacts faster: exits bears earlier, but whipsaws more in chop.

**(e) Reference.** Faber (2007), "A Quantitative Approach to Tactical Asset Allocation", Journal of Wealth Management (the 10-month SMA rule, of which the 200-day is the daily-frequency classic).

**(f) Engine unit-test property.** Exercises the cash asset and the time-in-market metric: assert equity is exactly flat on every day where the prior rebalance set `W = 0`. Also a natural look-ahead probe: shifting the signal one day early must change the equity curve; if it does not, the engine's lag is broken.

---

## 4. S4: Time-series momentum, per asset (TSMOM)

**(a) Description and intuition.** Each asset is judged against its own past only: hold it if its own trailing L-day return is positive, drop it if negative. No cross-asset comparison. This is the "absolute momentum" or trend-following family, documented across every asset class, and per the crypto literature the more robust momentum variant. Crucially, it has a built-in bear-market brake: when everything is down, everything fails the filter and the book goes to cash.

**(b) Signal and weights.** On each rebalance day `t`, over the eligible set (Section 0.4 with lookback `L`, `k = 0`), define the holder set:

```
H(t) = { i eligible : R_i(t; L, 0) > 0 }
h(t) = |H(t)|

W_i(t) = 1 / h(t)   if i in H(t)
W_i(t) = 0          otherwise
```

If `h(t) = 0`, hold 100% cash. Strict inequality: a coin exactly flat over the lookback is not held. Parameters and defaults: `L = 90` (primary), `L = 30` (secondary run); `k = 0` fixed.

Note one deliberate simplification versus the literature: Moskowitz, Ooi, and Pedersen scale each position by inverse volatility; we equal-weight the holders to keep Stage 1C minimal. Consequence to be aware of: when only one coin has positive momentum, the book is 100% that coin. A cash-buffered variant (`W_i = 1/n_eligible` per holder, remainder in cash) exists as a later robustness check but is NOT a Stage 1C run.

**(c) Rebalance rule.** Weekly per Section 0.3.

**(d) Expected behavior.** Trend-like: participates in broad up-moves, de-risks into cash in broad down-moves, so drawdowns should be visibly shallower than S2 equal-weight. Time-in-market meaningfully below 100% and clustered (all-in during bulls, all-out during bears, since crypto coins trend together). Turnover moderate: expect roughly 200 to 600% annualized one-sided, higher for `L = 30` than `L = 90` because the shorter lookback flips signs more often. Sharpe should beat S2 on this window if the engine and data are healthy; if TSMOM looks wildly worse than equal-weight in a window containing a real drawdown, investigate before proceeding.

**(e) Reference.** Moskowitz, Ooi, and Pedersen (2012), "Time Series Momentum", Journal of Financial Economics.

**(f) Engine unit-test property.** Exercises the `sum(W) <= 1` inequality branch and the all-cash state (`h(t) = 0`): assert the engine handles a zero-weight week without NaNs and that equity is flat through it. Also confirms per-asset signal independence: adding or removing one asset from the universe must not change another asset's hold/drop decision (unlike S5).

---

## 5. S5: Cross-sectional momentum (XSMOM), the target family

**(a) Description and intuition.** Rank the universe by trailing L-day return and hold the best performers, equal-weighted. Unlike TSMOM, the judgment is relative: a coin is held for beating its peers, even if its absolute return is negative. This is the strategy family XMom ultimately trades, run here purely as a known baseline, gross of costs. The optional skip of the most recent `k` days is the classic guard against short-term reversal contaminating the momentum signal (the equity-market "12-2" convention scaled down to crypto horizons).

**(b) Signal and weights.** On each rebalance day `t`:

1. Compute `R_i(t; L, k)` for every eligible asset (Section 0.4; note eligibility requires valid closes at both `t - L` and `t - k`).
2. Rank eligible assets by `R_i(t; L, k)` descending, ties broken per Section 0.6.
3. Select the holder set `H(t)` as the top `n_hold(t)` names, where:
   - **Top-N variant:** `n_hold(t) = min(N_top, n_eligible(t))` with default `N_top = 3`.
   - **Top-quintile variant:** `n_hold(t) = max(1, ceil(q * n_eligible(t)))` with `q = 0.20`. With ~13 eligible names this is `ceil(2.6) = 3`, so the two variants usually coincide; they diverge when breadth changes, which is exactly why we run both.
4. Weights:

```
W_i(t) = 1 / n_hold(t)   if i in H(t)
W_i(t) = 0               otherwise
```

There is NO absolute-return filter by default: in a bear market this strategy fully holds the least-bad losers. That is the honest classic definition and the behavioral contrast with S4 we want to see. Parameters and defaults: `L = 30`; `k = 0` (primary) and `k = 7` (skip variant); selection `N_top = 3` (primary) and `q = 0.20` (quintile variant).

**(c) Rebalance rule.** Weekly per Section 0.3.

**(d) Expected behavior.** Strong gross returns in trending, dispersed markets (this is the documented crypto momentum premium at 1 to 4 week formation horizons), but full market beta in crashes: expect drawdowns as deep as or deeper than equal-weight, because it stays 100% invested and concentrated. HIGH turnover, the defining cost problem of this family: with `L = 30` and weekly rebalance expect roughly 500 to 1,500% annualized one-sided turnover. The `k = 7` skip variant should show modestly different (often better) risk-adjusted results if short-term reversal exists in the data, and slightly lower turnover. Time-in-market ~100%.

**THIN-UNIVERSE WARNING (read this twice).** Our screened universe has a median of only ~13 names. Top-3 means each pick is 33.3% of the book, so this is a concentrated bet on 3 coins, not a diversified factor portfolio. Consequences: (i) single-name events (delisting, exploit, idiosyncratic crash) hit the equity curve hard; (ii) performance statistics will be noisy and regime-dependent, so do not over-read Sharpe differences between XS variants on this window; (iii) the classic academic decile construction is impossible here, which is why we use top-N and top-quintile instead; (iv) any later "improvement" to XS momentum must first be checked against the possibility that it is just noise from 3-name concentration. State this caveat verbatim in the Stage 1C results report.

**(e) Reference.** Jegadeesh and Titman (1993), "Returns to Buying Winners and Selling Losers", Journal of Finance (the original cross-sectional momentum construction); Liu, Tsyvinski, and Wu (2022), "Common Risk Factors in Cryptocurrency", Journal of Finance (documents the crypto momentum factor at short formation horizons).

**(f) Engine unit-test property.** The turnover accounting workout: this is the highest-turnover strategy, so its reported annual turnover must be plausibly ranked above all others (assert `turnover(S5) > turnover(S4) > turnover(S2) > turnover(S1)` on the same window). Also the sharpest look-ahead probe: because ranks change fast, an engine that fails to shift weights by one day produces a dramatically (and falsely) better XS equity curve; the look-ahead guard test should use this strategy.

---

## 6. S6: Short-term reversal (mean-reversion contrast)

**(a) Description and intuition.** The mirror image of S5 at a short horizon: buy the WORST recent performers, betting that short-horizon losers bounce. In equities, one-week and one-month reversal is a robust classic. We run it as a contrast, not a candidate: it teaches what a non-momentum signal feels like in this engine and provides a cheap negative control (if reversal and momentum both look great on the same data, something is wrong with the harness).

**(b) Signal and weights.** On each rebalance day `t`:

1. Compute `R_i(t; L, 0)` for every eligible asset, with default `L = 7`.
2. Rank eligible assets by `R_i(t; L, 0)` ASCENDING (worst first), ties per Section 0.6.
3. Hold the bottom `n_hold(t) = min(N_bottom, n_eligible(t))` names, default `N_bottom = 3`.

```
W_i(t) = 1 / n_hold(t)   if i in bottom N_bottom by trailing 7-day return
W_i(t) = 0               otherwise
```

No absolute filter; long-only per the engine contract (the academic version is long losers / short winners; we run the long leg only). Parameters and defaults: `L = 7`, `N_bottom = 3`.

**(c) Rebalance rule.** Weekly per Section 0.3. Note the horizon match is deliberate: a 7-day formation with a 7-day holding period is the canonical weekly reversal setup.

**(d) Expected behavior.** The weakest and noisiest strategy on the sheet, and that is fine. In crypto, short-horizon continuation is generally stronger than reversal, so expect a lower Sharpe than S5, possibly negative, with equal-weight-like or worse drawdowns (it deliberately buys knives; in a persistent downtrend it keeps catching the fastest fallers). Turnover very high, similar order to S5 (roughly 500 to 1,500% annualized one-sided), since 7-day loser ranks churn weekly. If S6 dramatically OUTPERFORMS S5 on this window, treat it as a red flag for a sign error or data problem before treating it as a discovery.

**(e) Reference.** Jegadeesh (1990), "Evidence of Predictable Behavior of Security Returns", Journal of Finance; Lehmann (1990), "Fads, Martingales, and Market Efficiency", Quarterly Journal of Economics.

**(f) Engine unit-test property.** Signal-inversion check: S6 with `(L = 7, bottom 3)` and an XS momentum run with `(L = 7, top 3)` must select disjoint holder sets on every rebalance day where `n_eligible >= 6` (assert this). Confirms the ranking and selection code respects direction and is not accidentally symmetric.

---

## 7. Metrics: what every strategy is reported on

One row per run in a single comparison table, all computed on the common evaluation window (Section 0.5), from the daily portfolio return series `r_p(t)` and the target-weight matrix `W`. Risk-free rate is 0. Annualization factor is 365 (crypto trades every calendar day).

| Metric | Definition |
|---|---|
| Total return | `E(T) / E(0) - 1` where `E` is the equity curve, `E(0) = 1` |
| CAGR | `(E(T) / E(0)) ^ (365 / n_days) - 1` |
| Annualized volatility | `std(r_p, ddof=1) * sqrt(365)` |
| Sharpe | `mean(r_p) / std(r_p, ddof=1) * sqrt(365)` |
| Sortino | `mean(r_p) / std(min(r_p, 0), ddof=1) * sqrt(365)` (downside deviation about 0) |
| Max drawdown | `min_t ( E(t) / cummax(E)(t) - 1 )`, reported as a negative number |
| Calmar | `CAGR / abs(MaxDD)` |
| Annual turnover | daily one-sided turnover `tau(t) = 0.5 * sum_i abs(W_i(t) - W_i(t-1))`, annualized as `sum_t tau(t) * 365 / n_days`. Computed on TARGET weights (drift ignored, consistent with Section 0.3); 100% means the whole book replaced once per year. |
| Hit rate | fraction of days with `r_p(t) > 0`, among days where gross exposure `sum_i W_i(t-1) > 0` |
| Time-in-market | fraction of days with `sum_i W_i(t-1) > 0` |

Plus, per run: an equity-curve plot and a drawdown-curve plot, all runs overlaid on shared axes in the results report, log scale for equity. Every run also records its exact parameter dict and the evaluation window start/end dates so the table is reproducible from this document alone.

---

## 8. Parameter grid: the exact Stage 1C run list

Shared settings for ALL runs: weekly Monday rebalance (Section 0.3), costs = 0, annualization = 365, common evaluation window with 200-day warmup (Section 0.5), tie-break alphabetical (Section 0.6), universe = point-in-time liquidity-screened Kraken USD pairs from Stage 1A.

| Run ID | Strategy | Lookback L | Skip k | Selection | Weighting | Notes |
|---|---|---|---|---|---|---|
| S1 | Buy-and-hold BTC | n/a | n/a | BTC only | 100% BTC | never rebalances; engine sanity target |
| S2 | Equal-weight universe | n/a | n/a | all eligible | 1/n(t) | 1/N baseline |
| S3a | MA filter BTC | N = 200 | n/a | BTC or cash | 100% or 0% | primary Faber run |
| S3b | MA filter BTC | N = 100 | n/a | BTC or cash | 100% or 0% | faster filter |
| S4a | TSMOM | L = 90 | 0 | own return > 0 | 1/h(t) | primary TSMOM |
| S4b | TSMOM | L = 30 | 0 | own return > 0 | 1/h(t) | faster TSMOM |
| S5a | XS momentum | L = 30 | 0 | top N = 3 | 1/3 | primary XS |
| S5b | XS momentum | L = 30 | 7 | top N = 3 | 1/3 | reversal-skip variant |
| S5c | XS momentum | L = 30 | 0 | top quintile, q = 0.20 | 1/n_hold(t) | breadth-adaptive variant |
| S5d (optional) | XS momentum | L = 30 | 7 | top quintile, q = 0.20 | 1/n_hold(t) | run if time permits |
| S6 | Short-term reversal | L = 7 | 0 | bottom N = 3 | 1/3 | contrast / negative control |

Ten required runs (S1 through S6, excluding S5d), one metrics row each, one combined comparison table and overlay chart in `research/phase1_results.md`.

### Predicted ordering to sanity-check against (write predictions BEFORE running)

- Max drawdown, shallowest to deepest: S3a/S3b and S4a should be shallowest; S1 middle; S2, S5x, S6 deepest.
- Turnover, lowest to highest: S1 < S3x < S2 < S4x < S5x and S6.
- Time-in-market: S1 = S2 = S5x = S6 = 100%; S3x and S4x below 100%.
- If any prediction is violated by a wide margin, suspect the engine or the data before crediting the strategy.
