# XMom reproducibility entry points (MASTER_BRIEF final deliverable):
#   make data       rebuilds the full dataset from public APIs (fetch + clean + screen)
#   make backtests  runs every registered backtest (Stage C ladder + Phase 2 if present)
#   make test       runs the unit-test suite the gates depend on

PY := .venv/bin/python

.PHONY: data fetch build backtests test discovery

data: fetch build

# Discovery dataset (Handoff #7): broad Binance-only panel for signal discovery
discovery:
	$(PY) discovery_fetch.py
	$(PY) discovery_build.py
	$(PY) discovery_baselines.py

fetch:
	$(PY) phase1_fetch_data.py

build:
	$(PY) phase1_build_universe.py

backtests:
	$(PY) phase1_run_ladder.py
	@if [ -f phase2_run.py ]; then $(PY) phase2_run.py; fi

test:
	$(PY) -m pytest tests/ -q
