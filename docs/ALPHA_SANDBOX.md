# The Alpha Sandbox: test your own signal idea in three steps

You have an idea ("coins that dumped hard bounce", "hold whatever is above its own
100-day average", "rank by volatility-adjusted momentum"). This sandbox turns it into
an honest backtest with one file edit and one command, and it makes the classic
self-deceptions (peeking at the future, cherry-picking parameters, quietly forgetting
failed runs) either impossible or automatically counted against you.

## The three steps

**Step 1. Edit `research/my_alpha.py`.** Change `ALPHA_NAME`, set your `PARAMS`, and
rewrite the `my_alpha(prices, universe, params)` function. The contract:

- return DAILY target weights (same index and columns as `prices`), every weight
  `>= 0`, each row summing to `<= 1` (the remainder is cash, earning zero);
- use only data up to each decision day (no `shift(-1)`, no centered windows, no
  full-sample normalizations);
- respect the `universe` mask (True = tradable that day, decided point-in-time).

The pre-filled example (28-day cross-sectional momentum, top quintile) runs as-is.

**Step 2. Run `make alpha`** (or `python run_alpha.py`). The harness automatically:

- validates the weight contract and runs a **look-ahead probe**: it hides the last
  ten weeks of data, recomputes your weights, and fails the run loudly if any
  earlier weight changed (that can only happen if you read the future);
- backtests **GROSS as the headline** on the broad discovery panel, with a net-50bps
  footnote as a tradability preview only;
- breaks results down **by regime** (BTC trend bull/bear, plus named eras: covid
  crash, 2021 bull, 2022 bear, ...), because a signal that only works in one regime
  is the thing we most want to catch;
- sweeps your `PARAM_GRID` for a **plateau check** (a real effect survives its
  neighbors; a lonely spike is noise);
- runs anchored **walk-forward folds** for consistency of your fixed parameters;
- benchmarks against **BTC buy-and-hold and the equal-weight universe**;
- appends every run to `research/TRIALS_LEDGER.csv`: failed ideas count, and the
  noise floor in your verdict rises with every trial, as it should.

**Step 3. Read `research/my_alpha_report.md`.** It ends in a plain-English verdict:
does the idea beat both benchmarks, is the plateau stable, how many folds are
positive, and where the noise floor sits given your trial count.

## The vault (read before you celebrate)

Everything from **2025-01-01 onward is locked in a one-look out-of-sample vault**.
The harness structurally withholds it: your alpha never receives that data during
normal runs, so you cannot tune on it even by accident. When (and only when) an idea
has survived the playground, the plateau, and the folds, run:

    python run_alpha.py --vault

That scores the vault ONCE, labels it the final exam in the report and the ledger,
and spends your look. Re-running the vault after further tuning turns it into
in-sample data; if you do it, the ledger shows it, and the honest label for any
later vault number is "seen before."

Also set expectations: the vault holds ~78 weekly observations, a Sharpe standard
error near 0.8. It can catch a disaster or gross overfitting. It cannot certify an
edge. Certification is Phase 3+ work (costs, Kraken tradability, paper trading).

## Why gross? Why this panel?

Discovery and tradability are deliberately separated (Handoff #7). Here you are
asking "does this signal contain information?", on the broadest clean cross-section
we have (Binance panel, dead coins included, corporate-action seams severed). Kraken
constraints (thin universe, 50 bps costs, thin books) are a LATER gate applied only
to survivors; applying them during ideation kills ideas for the wrong reason. The
net-50bps line in your report exists only to keep turnover visible: a gross winner
with 3,000% turnover has a fee problem to solve BEFORE the tradability gate, e.g.
slower rebalancing or bands.

## Worked example ideas

1. **Vol-adjusted momentum (the pre-filled example, upgraded).** Rank by trailing
   28-day return DIVIDED by trailing 30-day volatility instead of raw return, top
   quintile. Hypothesis: raw-return ranking is secretly a volatility ranking; the
   adjusted version keeps the winners without maximum-beta names. Two-line change:
   compute `strategies.trailing_return(...) / prices.pct_change().rolling(30).std()`
   and rank that.
2. **Own-trend filter basket (TSMOM, the Phase 2 base ingredient).** Hold every
   eligible coin above its own 100-day SMA, inverse-vol weighted. Hypothesis: the
   absolute filter avoids the pump-chasing that killed top-N ranking on this panel
   (see research/DISCOVERY_BASELINES.md observation 1).
3. **Short-term reversal, quintile, bull-gated.** Buy the WORST 7-day performers,
   bottom quintile, but only when BTC is above its 200-day SMA. Hypothesis: reversal
   was catastrophic ungated (S6 gross Sharpe -0.98) because it catches knives in
   bears; the gate removes the knives. Expect the regime table to decide this one.

## House rules (the short version)

- The ledger is append-only and every executed run belongs in it. A run that is not
  in the ledger does not exist.
- Grids are small on purpose: every combination raises the bar your winner must
  clear. If you need 200 combinations to find the edge, there is no edge.
- Surprising results are bugs until investigated (see the LUNA +17.7M% story in the
  progress log for why).
- No em dashes in reports. House style.
