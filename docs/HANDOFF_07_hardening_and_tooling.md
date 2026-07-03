# Handoff #7 (revised): Clean discovery data + alpha sandbox + regime/OOS levers

Correction to the prior version: the earlier draft dragged Kraken trading constraints (thin universe, cost lens, splice-to-match) into the discovery phase. That was over-engineered. Discovery uses the cleanest, broadest data, gross of costs, judged across market regimes. Kraken constraints move OUT of discovery and into a later tradability gate applied only to signals that already survived.

Same hard stop as before: backtests and reports only, no keys, no orders, nothing deployed. Commit each workstream separately with a `PROGRESS_LOG.md` entry and a `docs/HANDOFFS.md` result note.

Context to read first: `docs/DECISIONS.md`, `docs/04_VALIDATION_METHODOLOGY.md`, `research/stage_a_data_report.md`.

---

## Workstream 1: One clean discovery dataset (broad, gross, regime-ready)

Goal: a single-source, seam-free, broad price panel built for signal discovery, not for Kraken execution.

1. **Single price source, whole history.** Use Binance as the one daily-close source across the full window per coin. No splice, no Kraken reconciliation, no correlation gate, no volume-rescaling proxy. This removes the seam and all the fudges in one move.
2. **Broad, survivorship-conscious universe.** Build the widest reasonable liquid universe from Binance liquidity with a generous bar (liquid enough to be a real market, not the Kraken-thin $1M screen). Critically, include coins that later died or delisted where data exists, so discovery is not survivorship-biased toward winners. Keep a point-in-time liquidity screen only to avoid ranking untradeable microcaps, but set the threshold generously so the cross-section is wide (this directly helps cross-sectional signals that the thin Kraken universe was strangling).
3. **Gross only at this stage.** Costs are OFF for discovery. The dormant cost hook stays in the engine but discovery reports gross. (Net stays available for later.)
4. **Regimes are first-class.** Define a simple, documented regime labeling (for example BTC above/below its 200-day average for bull/bear, plus named historical windows: 2020 COVID crash, 2021 bull, 2022 bear, 2023 to 2025 recovery/chop). Every backtest reports metrics broken down BY regime, not just overall. A signal that only works in one regime is the thing we most want to catch.
5. Update `research/stage_a_data_report.md` to describe the new clean discovery dataset and explicitly note that Kraken tradability is deferred to a later gate.

Keep engine and data tests green. Re-run the existing ladder and Phase 2 head-to-head GROSS on the broad universe and report how conclusions change (especially whether the cross-sectional signal looks better on a wide cross-section).

## Workstream 2: The alpha sandbox (discovery-first)

Goal: test a new signal by editing ONE function and running ONE command, judged gross and by regime.

1. Create `research/my_alpha.py` with a single documented template following the engine contract:
   ```python
   def my_alpha(prices, universe, params):
       """Return target weights (>=0, sum<=1) using ONLY data up to today."""
       ...
   ```
   Pre-fill with a simple working example so it runs out of the box.
2. Create `run_alpha.py` (and `make alpha`) that runs the full discovery gauntlet automatically:
   - backtest GROSS as the headline, with net at 50 bps shown only as a small "tradability preview" footnote (not the decision metric at this stage),
   - a per-regime metrics breakdown (does the edge hold in bull, bear, chop?),
   - a parameter-plateau sweep (plateau versus lonely spike),
   - a walk-forward / OOS evaluation using the vault lever from Workstream 3,
   - benchmarks side by side (BTC buy-and-hold, equal-weight),
   - auto-appends every run to `research/TRIALS_LEDGER.csv`.
   Output `research/my_alpha_report.md`: gross metrics table, the regime breakdown, an equity-curve figure, and a plain-English verdict versus benchmarks and the noise floor.
3. Write `docs/ALPHA_SANDBOX.md`: a beginner-friendly "test your own idea in three steps" guide, with two or three worked example signal ideas, and a clear note that discovery judges gross + regime robustness, and Kraken costs come later.

## Workstream 3: Regime + out-of-sample levers

1. Expose a clear config block (in `xmom/config.py`) for:
   - `OOS_VAULT_START` (default `2025-01-01`): everything on/after is the locked one-look vault.
   - Walk-forward settings (initial train window, test-fold length, step).
   - The regime definitions from Workstream 1, editable in one place.
2. Enforce it: tuning and the plateau sweep use only pre-vault data; the vault is scored once and labeled the final exam.
3. Document the discipline in `docs/ALPHA_SANDBOX.md`.

---

## Report back to the owner
- Confirmation the dataset is now single-source and seam-free, and how the ladder/Phase 2 results look GROSS on the broad universe versus the old Kraken-thin ones (especially whether cross-sectional improves with a wider cross-section).
- The regime breakdown for the base case: does the edge hold across bull, bear, and chop?
- A 3-step recap of the alpha sandbox with an example run.
- The OOS vault size versus the playground.
