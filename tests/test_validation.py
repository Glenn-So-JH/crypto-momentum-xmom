"""Validation-toolkit tests: ledger append-only, DSR sanity, fold no-leak guard."""

import numpy as np
import pandas as pd

from xmom import validation


def test_ledger_appends_and_counts(tmp_path):
    ledger = tmp_path / "ledger.csv"
    rows = [
        {"run_id": "S1", "strategy_family": "benchmark", "parameters": {"asset": "BTC"},
         "data_window": "2020..2026", "gross_or_net": "gross", "sharpe": 1.0,
         "max_drawdown": -0.5, "annual_turnover": 0.0, "why_run": "test"},
        {"run_id": "S5a", "strategy_family": "xsmom", "parameters": {"L": 30},
         "data_window": "2020..2026", "gross_or_net": "gross", "sharpe": 0.7,
         "max_drawdown": -0.6, "annual_turnover": 8.0, "why_run": "test"},
    ]
    validation.append_trials(rows, ledger)
    validation.append_trials(rows[:1], ledger)  # append again: file must grow, not reset
    assert validation.count_trials(ledger_path=ledger) == 3
    assert validation.count_trials("xsmom", ledger_path=ledger) == 1
    frame = pd.read_csv(ledger)
    assert list(frame.columns) == validation.LEDGER_COLUMNS


def test_expected_max_sharpe_grows_with_k():
    v = 0.05
    values = [validation.expected_max_sharpe(k, v) for k in (2, 10, 50, 200)]
    assert all(values[i] < values[i + 1] for i in range(len(values) - 1))
    assert validation.expected_max_sharpe(1, v) == 0.0


def test_dsr_strong_vs_noise():
    idx = pd.date_range("2020-01-01", periods=2000, freq="D")
    rng = np.random.default_rng(5)
    strong = pd.Series(rng.normal(0.003, 0.01, 2000), index=idx)   # daily SR ~ 0.3
    noise = pd.Series(rng.normal(0.0, 0.01, 2000), index=idx)
    trials = [0.2, 0.5, -0.1, 0.3, 0.8]  # annualized trial Sharpes
    d_strong = validation.deflated_sharpe(strong, k=5, trial_sharpes_annual=trials)
    d_noise = validation.deflated_sharpe(noise, k=5, trial_sharpes_annual=trials)
    assert d_strong["dsr"] > 0.99
    assert d_noise["dsr"] < 0.90
    assert d_noise["verdict"] == "indistinguishable from selection noise"


def test_walk_forward_folds_do_not_leak():
    days = pd.date_range("2020-01-06", periods=130, freq="7D")  # 130 weekly Mondays
    folds = validation.walk_forward_folds(days, initial_train_weeks=52, test_weeks=13)
    assert len(folds) == 6  # (130 - 52) // 13
    for f in folds:
        assert f["train_end"] < f["test_start"]          # embargo: strictly before
        assert f["train_start"] == days[0]               # anchored, expanding
    for a, b in zip(folds, folds[1:]):
        assert a["test_end"] < b["test_start"]           # contiguous, non-overlapping
        assert b["train_end"] >= a["test_end"]           # training absorbs past folds only


def test_walk_forward_drops_partial_tail():
    days = pd.date_range("2020-01-06", periods=70, freq="7D")
    folds = validation.walk_forward_folds(days, initial_train_weeks=52, test_weeks=13)
    assert len(folds) == 1  # 18 weeks left after train: one full block, partial dropped
