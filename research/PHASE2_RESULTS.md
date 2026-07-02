# Phase 2 results: base case vs challenger (Stage D)

Window: **2019-07-22 to 2026-07-01** (363 weekly observations). Engine: drift-aware with 20% no-trade bands. Decisions on the net-50bps column only (DEC-002).

## Registration block (committed before results were generated)

1. **Question.** Does relative (cross-sectional top-3) selection beat absolute
   (time-series own-return) selection on our venue and universe, when both carry the
   same BTC 200d gate, inverse-vol sizing with a 25% cap, 30% vol target, weekly
   rebalance with a 20% no-trade band, judged net of 50 bps per side?
2. **Configurations.** Decision runs: BASE_21 (TSMOM L=21), BASE_14 (TSMOM L=14),
   CHAL_21 (XS top-3, L=21, k=0). Robustness neighbors on BASE_21, excluded from
   selection: L=28; gate=100; vol target 20% and 40%; band 10% and 30%. Each decision
   run at gross, 25, and 50 bps per side; neighbors at 50 bps. All runs ledger-logged.
3. **Prediction.** Base case beats challenger net of costs (literature prior: TS more
   robust than XS in crypto; thin universe penalizes ranking; XS turnover costs more).
   Base case beats equal-weight (S2) and buy-and-hold BTC (S1) on Sharpe and Calmar
   with materially shallower max drawdown, and does NOT beat BTC on total return.
4. **Decision rule (Gate 2C).** The challenger is kept only if it beats the base case
   on net-50bps Sharpe AND on walk-forward fold win rate (>50% of folds). Ties or
   ambiguity go to the base case. If the base case fails its own success criteria
   (docs/05 section 2), Phase 2 pauses for a rethink; nothing is decorated.
5. **Window and costs.** Full common evaluation window (200-day warmup); costs per
   DEC-002 via the drift-aware engine with no-trade bands. Vol sizing window 30d,
   covariance window 90d, both registered here before running.


## Head-to-head (decision runs)

| run | cost | Sharpe | CAGR | vol | maxDD | Calmar | turnover/yr | TIM |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BASE_21 | gross | +1.05 | +25.1% | 24.0% | -37.2% | +0.68 | 508% | 54% |
| BASE_21 | net25 | +0.95 | +22.0% | 24.0% | -38.6% | +0.57 | 508% | 54% |
| BASE_21 | net50 | +0.84 | +18.9% | 24.0% | -40.0% | +0.47 | 508% | 54% |
| BASE_14 | gross | +1.09 | +26.6% | 24.5% | -39.0% | +0.68 | 594% | 54% |
| BASE_14 | net25 | +0.97 | +22.9% | 24.5% | -40.7% | +0.56 | 594% | 54% |
| BASE_14 | net50 | +0.84 | +19.3% | 24.5% | -42.3% | +0.46 | 594% | 54% |
| CHAL_21 | gross | +1.16 | +27.7% | 23.4% | -35.1% | +0.79 | 502% | 58% |
| CHAL_21 | net25 | +1.05 | +24.5% | 23.4% | -36.5% | +0.67 | 502% | 58% |
| CHAL_21 | net50 | +0.95 | +21.4% | 23.4% | -37.9% | +0.57 | 502% | 58% |

Benchmarks on the same window (Stage C, vectorized engine): S1 BTC net50 Sharpe +0.73, S2 equal-weight net50 Sharpe +0.47.

## Robustness neighbors (registered, excluded from selection, net50)

| neighbor | Sharpe | CAGR | maxDD | turnover/yr |
|---|---:|---:|---:|---:|
| NBR_L28 | +0.83 | +18.4% | -38.3% | 453% |
| NBR_GATE100 | +1.06 | +24.9% | -35.8% | 505% |
| NBR_VT20 | +0.84 | +13.0% | -28.7% | 346% |
| NBR_VT40 | +0.84 | +24.1% | -48.9% | 658% |
| NBR_BAND10 | +0.84 | +18.9% | -40.1% | 517% |
| NBR_BAND30 | +0.87 | +19.6% | -39.0% | 494% |

## Walk-forward fold consistency (23 anchored 13-week folds, frozen params)

No per-fold parameter selection was performed (defaults are pre-registered), so these folds measure consistency of the frozen configuration, not selection skill.

| fold | test window | base return | base Sharpe | chal return | chal Sharpe |
|---|---|---:|---:|---:|---:|
| 1 | 2020-07-20 to 2020-10-12 | -1.9% | -0.10 | -7.3% | -0.77 |
| 2 | 2020-10-19 to 2021-01-11 | +63.0% | +5.24 | +49.7% | +4.49 |
| 3 | 2021-01-18 to 2021-04-12 | +47.5% | +5.70 | +1.7% | +0.42 |
| 4 | 2021-04-19 to 2021-07-12 | -4.6% | -0.36 | -0.3% | +0.08 |
| 5 | 2021-07-19 to 2021-10-11 | +9.0% | +1.99 | +28.9% | +4.92 |
| 6 | 2021-10-18 to 2022-01-10 | -8.8% | -1.60 | +10.5% | +1.93 |
| 7 | 2022-01-17 to 2022-04-11 | +0.0% | n/a | +0.0% | n/a |
| 8 | 2022-04-18 to 2022-07-11 | +0.0% | n/a | +0.0% | n/a |
| 9 | 2022-07-18 to 2022-10-10 | +0.0% | n/a | +0.0% | n/a |
| 10 | 2022-10-17 to 2023-01-09 | +0.0% | n/a | +0.0% | n/a |
| 11 | 2023-01-16 to 2023-04-10 | +6.1% | +0.96 | +9.0% | +1.30 |
| 12 | 2023-04-17 to 2023-07-10 | -11.6% | -1.83 | -5.1% | -0.73 |
| 13 | 2023-07-17 to 2023-10-09 | -13.4% | -3.76 | -14.4% | -4.31 |
| 14 | 2023-10-16 to 2024-01-08 | +64.3% | +5.24 | +68.9% | +5.28 |
| 15 | 2024-01-15 to 2024-04-08 | +14.4% | +1.68 | +3.5% | +0.60 |
| 16 | 2024-04-15 to 2024-07-08 | -15.0% | -3.60 | -14.0% | -2.54 |
| 17 | 2024-07-15 to 2024-10-07 | -13.8% | -4.06 | -12.7% | -3.73 |
| 18 | 2024-10-14 to 2025-01-06 | +34.7% | +3.10 | +44.4% | +3.88 |
| 19 | 2025-01-13 to 2025-04-07 | -15.5% | -3.27 | -16.0% | -3.58 |
| 20 | 2025-04-14 to 2025-07-07 | +10.3% | +1.77 | +19.8% | +2.70 |
| 21 | 2025-07-14 to 2025-10-06 | -1.6% | -0.00 | -2.7% | -0.22 |
| 22 | 2025-10-13 to 2026-01-05 | +4.5% | +1.42 | +9.8% | +2.44 |
| 23 | 2026-01-12 to 2026-04-06 | +0.0% | n/a | +0.0% | n/a |

Fold wins: base 7, challenger 11 (of 23; remainder ties/both-flat). Base positive in 9/23 folds; challenger positive in 10/23.

## Multiple-testing accounting

- Trials ledger rows for family `phase2_base`: **K = 12** (all cost levels and neighbors count; docs/04 section 1.2).
- Deflated Sharpe of BASE_21 net50: **DSR = 0.962** -> **credible at 95%** (n = 2537 daily obs, skew -0.17, kurtosis 12.5, benchmark per-period SR 0.0088).
- Single-name dependence: the top coin contributes 12% of positive gross P&L (top 3: DOGE +0.28, LINK +0.26, XRP +0.23).

## Verdict (registered rule applied)

**Winner: BASE CASE (gated TSMOM).**

Base-case success criteria (docs/05 section 2):
- PASS: beats S2 net Sharpe
- PASS: beats S1 net Sharpe
- PASS: beats S2 Calmar
- PASS: shallower maxDD than S1
- PASS: shallower maxDD than S2
- PASS: sign stable L14 vs L21
- PASS: sign stable gate 100 vs 200

### Verdict narrative

**The base case earned its keep.** Net of 50 bps per side it delivers Sharpe 0.84, CAGR 18.9%,
max drawdown -40.0% against buy-and-hold BTC's -76.6% and equal-weight's -83.6%, at 24%
volatility (the 30% target binding as designed) with 54% time-in-market. All seven registered
success criteria passed. The four consecutive all-flat folds from 2022-01 to 2023-01 are the
BTC 200-day gate holding the entire book in cash through the worst crypto bear in the sample:
the component added exactly for that purpose, doing exactly that.

**The challenger was NOT crushed, and honesty requires saying so plainly.** The registered
prediction was that the XS challenger would lose net of costs. It did not lose: CHAL_21 posted
net-50 Sharpe 0.95 against the base's 0.84, a slightly shallower drawdown, and 11 wins in the
18 decided folds (5 folds were both-flat because the shared gate was off). Why the base case
still wins: the Sharpe gap of 0.11 is under a third of one standard error on this window
(~0.38), which by our own statistical rules (docs/04 section 3.2) makes the comparison a
statistical tie, and the registered rule sends ties and ambiguity to the base case because it
is simpler and structurally cheaper to trade. Under the strict reading of the registered
fold clause (more than 50% of ALL folds, ties included) the challenger also falls short at
11 of 23. Both readings land in the same place, but the substantive finding stands: with
identical overlays, relative selection was NOT worse than absolute selection here. The
thin-universe XS penalty we predicted did not materialize once the gate, vol sizing, and name
cap were shared. That is a genuine surprise relative to both the literature prior and our
registration, recorded rather than smoothed over. It earns the challenger a future registered
experiment (E5, the TS+XS intersection, already on the docs/05 menu), not silent adoption.

**Parameter plateau, including a neighbor that outperformed.** The six registered neighbors
span net-50 Sharpe 0.83 to 1.06 with no sign flips: the chosen point sits on a plateau, not a
cliff. The best neighbor (gate = 100 days, Sharpe 1.06) OUTPERFORMS the chosen config. Per the
registration, neighbors test fragility and are excluded from selection, so we do not switch;
switching after seeing results would be exactly the post-hoc selection this methodology
exists to prevent. Noted for a future registered experiment.

**Costs and capacity.** Turnover ~508%/yr one-sided costs about 6 points of CAGR at 50 bps
per side (25.1% gross to 18.9% net); at 25 bps the drag roughly halves. The no-trade band is
not doing hidden work: 10% and 30% settings move turnover by under 5% and Sharpe by under
0.03 relative to the 20% default.

**What this does NOT establish.** DSR = 0.962 with K = 12 clears the 0.95 bar, but three
caveats keep it provisional: the 12 trials are highly correlated variants of one idea (which
understates the noise-maximum benchmark), the window is one macro regime cycle, and daily
kurtosis of 12.5 makes normal-theory bands optimistic. Per the charter, nothing here is
proof; it is a candidate that survived its first honest pass. Before any capital: the full
Phase 3 cost model (spread and slippage measured, cost-sensitivity curve with breakeven and
margin >= 2) and every unchecked box in the docs/04 section 7 checklist.
