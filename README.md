# XMom: Crypto Cross-Sectional Momentum

A first-principles, fully documented personal quant project: build a systematic long-only crypto momentum strategy, validate it honestly, and run it live with real capital.

This is a learning project run to professional standards. The goal is not a "money printer," it is a reproducible, honest pipeline and a clear answer to the question: *does cross-sectional momentum in crypto survive realistic transaction costs?*

## Start here
1. `docs/00_PROJECT_CHARTER.md` - the scope, thesis, risk rules, and what success means.
2. `docs/01_ROADMAP.md` - the phase-by-phase learning and build plan.
3. `docs/RESOURCES.md` - curated books, papers, and tool docs.
4. `PROGRESS_LOG.md` - the running journal (and the seed for the LinkedIn series).

## Folder layout
```
crypto-momentum/
  docs/         charter, roadmap, decision log, specs, phase designs, research synthesis
  xmom/         the library: config, data, quality, universe, engine, metrics,
                strategies (S1-S6), phase2 (base case + challenger), validation (DSR, folds)
  data/raw/     downloaded OHLCV, Kraken + secondary venue + spliced (gitignored)
  data/processed/  cleaned panels, universe membership, provenance (gitignored)
  research/     committed results: reports, figures, trials ledger, data notes
  backtest/     (reserved) event-driven backtest code
  portfolio/    (reserved) position sizing, risk management
  live/         (reserved) the execution engine (paper, then live)
  logs/         run logs (gitignored)
  tests/        unit tests: engine gates, look-ahead guards, strategies, validation
  notebooks/    exploratory Jupyter notebooks
  phase0_hello.py          live bid/ask/spread/fee check (Phase 0)
  phase1_fetch_data.py     enumerate + fetch + deep-splice OHLCV -> data/raw (Stage A)
  phase1_build_universe.py clean + point-in-time liquidity screen (Stage A)
  phase1_run_ladder.py     the S1-S6 validation ladder -> research/PHASE1_RESULTS.md
  phase2_run.py            base case vs challenger -> research/PHASE2_RESULTS.md
  Makefile                 make data / make backtests / make test
  PROGRESS_LOG.md
  README.md
```

## Reproduce everything
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
make data        # rebuild the full dataset from public APIs (~20 min, no keys)
make test        # engine sanity, look-ahead guards, 50+ unit tests
make backtests   # Stage C ladder + Phase 2 head-to-head, reports into research/
```

## Ground rules
- **Earn complexity.** A transparent baseline exists before anything advanced.
- **Backtests are guilty until proven innocent.** Model costs, validate out-of-sample, count how many variants are tested.
- **Secret hygiene.** API keys are trade-only (never withdrawal), live in environment variables, and are never committed. See `.gitignore`.
- **Log everything.** Every session gets a `PROGRESS_LOG.md` entry; every live decision and fill is logged.

## Status
Phase 1, Stage 1A complete: trustworthy 2-year daily dataset for ~22 Kraken USD pairs, with a
point-in-time liquidity screen and a data-quality note (`research/phase1a_data_quality.md`). Next:
Stage 1B, the vectorized backtest engine and its sanity + look-ahead tests. See the progress log.
