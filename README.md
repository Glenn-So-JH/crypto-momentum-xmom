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
  docs/         charter, roadmap, resources
  data/raw/     downloaded OHLCV (gitignored)
  data/processed/  cleaned datasets, universe membership
  research/     signal exploration, notebooks-as-scripts
  backtest/     vectorized and event-driven backtest code
  portfolio/    position sizing, risk management
  live/         the execution engine (paper, then live)
  logs/         run logs, fills, reconciliation (gitignored)
  tests/        unit tests for signals, backtest, risk rules
  notebooks/    exploratory Jupyter notebooks
  PROGRESS_LOG.md
  README.md
```

## Ground rules
- **Earn complexity.** A transparent baseline exists before anything advanced.
- **Backtests are guilty until proven innocent.** Model costs, validate out-of-sample, count how many variants are tested.
- **Secret hygiene.** API keys are trade-only (never withdrawal), live in environment variables, and are never committed. See `.gitignore`.
- **Log everything.** Every session gets a `PROGRESS_LOG.md` entry; every live decision and fill is logged.

## Status
Phase 0: scoping complete, environment setup beginning. See the progress log for the latest.
