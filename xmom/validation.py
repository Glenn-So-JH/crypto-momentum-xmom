"""
validation.py  -  the anti-overfitting toolkit from docs/04_VALIDATION_METHODOLOGY.md.

Three jobs:
  1. Trials ledger: append-only CSV recording every backtest actually executed
     (section 1.2). K for the deflated Sharpe comes from this file, never from memory.
  2. Deflated Sharpe Ratio (sections 1.3): observed Sharpe judged against the expected
     maximum of K noise trials, with skew/kurtosis-adjusted PSR (Bailey & Lopez de
     Prado 2014). Implemented with stdlib NormalDist: no new dependencies.
  3. Anchored walk-forward folds (section 2.2): expanding train window, sequential
     13-week test blocks, refits strictly before each test block (no leakage).
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from . import config

LEDGER_PATH = config.REPO_ROOT / "research" / "TRIALS_LEDGER.csv"
LEDGER_COLUMNS = [
    "date", "run_id", "strategy_family", "parameters", "data_window",
    "gross_or_net", "sharpe", "max_drawdown", "annual_turnover", "why_run",
]

_NORMAL = NormalDist()
EULER_GAMMA = 0.5772156649015329


def append_trials(rows: list[dict], ledger_path: Path = LEDGER_PATH) -> int:
    """
    Append executed runs to the ledger (append-only; file is created with a header if
    missing). Each row: the LEDGER_COLUMNS fields; `parameters` may be a dict and is
    JSON-encoded. Returns the number of rows written.
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not ledger_path.exists()
    with ledger_path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
        if new_file:
            writer.writeheader()
        for row in rows:
            row = dict(row)
            row.setdefault("date", date.today().isoformat())
            if isinstance(row.get("parameters"), dict):
                row["parameters"] = json.dumps(row["parameters"], sort_keys=True)
            writer.writerow({k: row.get(k, "") for k in LEDGER_COLUMNS})
    return len(rows)


def count_trials(strategy_family: str | None = None, ledger_path: Path = LEDGER_PATH) -> int:
    """K = rows in the ledger (optionally for one family). Zero if no ledger yet."""
    if not ledger_path.exists():
        return 0
    frame = pd.read_csv(ledger_path)
    if strategy_family is not None:
        frame = frame[frame["strategy_family"] == strategy_family]
    return int(len(frame))


def expected_max_sharpe(k: int, var_sr: float) -> float:
    """
    E[max SR of K noise trials], per-period units (docs/04 section 1.3):
        sqrt(V[SR]) * ((1 - gamma) * Z^-1(1 - 1/K) + gamma * Z^-1(1 - 1/(K e)))
    """
    if k <= 1 or var_sr <= 0:
        return 0.0
    z1 = _NORMAL.inv_cdf(1.0 - 1.0 / k)
    z2 = _NORMAL.inv_cdf(1.0 - 1.0 / (k * math.e))
    return math.sqrt(var_sr) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def probabilistic_sharpe(sr_hat: float, sr_benchmark: float, n: int,
                         skew: float, kurt: float) -> float:
    """
    PSR (Bailey & Lopez de Prado 2012): probability the true per-period Sharpe exceeds
    `sr_benchmark`, given n observations and the sample's skew and (raw) kurtosis.
    """
    if n <= 1:
        return float("nan")
    denom = 1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    if denom <= 0:
        return float("nan")
    z = (sr_hat - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(denom)
    return _NORMAL.cdf(z)


def deflated_sharpe(returns: pd.Series, k: int, trial_sharpes_annual: list[float]) -> dict:
    """
    DSR of a candidate: PSR against the expected-max-of-K-noise-trials benchmark.

    returns: the candidate's DAILY return series (evaluation window).
    k: number of trials from the ledger for this family.
    trial_sharpes_annual: the annualized Sharpes of those trials (cross-trial variance
        feeds the benchmark). Converted to per-period internally.

    Returns dict with sr_hat, sr_benchmark (both per-period), dsr, and inputs.
    """
    r = returns.dropna().to_numpy()
    n = len(r)
    sd = r.std(ddof=1)
    sr_hat = float(r.mean() / sd) if sd > 0 else float("nan")
    m2 = ((r - r.mean()) ** 2).mean()
    skew = float(((r - r.mean()) ** 3).mean() / m2 ** 1.5) if m2 > 0 else 0.0
    kurt = float(((r - r.mean()) ** 4).mean() / m2 ** 2) if m2 > 0 else 3.0

    per_period = np.array(trial_sharpes_annual, dtype="float64") / math.sqrt(config.ANNUALIZATION)
    var_sr = float(per_period.var(ddof=1)) if len(per_period) > 1 else 0.0
    sr_star = expected_max_sharpe(k, var_sr)
    dsr = probabilistic_sharpe(sr_hat, sr_star, n, skew, kurt)
    return {
        "n_obs": n, "k_trials": k,
        "sr_hat_per_period": sr_hat, "sr_benchmark_per_period": sr_star,
        "skew": skew, "kurtosis": kurt, "dsr": dsr,
        "verdict": "credible at 95%" if dsr >= 0.95 else "indistinguishable from selection noise",
    }


def vault_start() -> pd.Timestamp:
    return pd.Timestamp(config.OOS_VAULT_START)


def playground_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """
    The tunable part of the calendar: everything strictly BEFORE the OOS vault.
    Discovery tuning, plateau sweeps, and iteration operate only on this slice; the
    harness passes alphas playground data only, so the vault is unseeable rather
    than merely off-limits (Handoff #7 WS3).
    """
    return index[index < vault_start()]


def vault_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """The locked one-look vault: on/after config.OOS_VAULT_START."""
    return index[index >= vault_start()]


def walk_forward_folds(
    rebalance_days: pd.DatetimeIndex,
    initial_train_weeks: int = 52,
    test_weeks: int = 13,
) -> list[dict]:
    """
    Anchored walk-forward per docs/04 section 2.2: expanding training window starting
    with `initial_train_weeks`, then sequential `test_weeks`-long out-of-sample blocks.
    Any final partial block shorter than test_weeks is dropped (never padded).

    Returns [{fold, train_start, train_end, test_start, test_end}], where train_end is
    the LAST rebalance day strictly before test_start (embargo: refits may only use
    data through train_end).
    """
    days = pd.DatetimeIndex(rebalance_days).sort_values()
    folds = []
    start = initial_train_weeks
    fold_no = 1
    while start + test_weeks <= len(days):
        test = days[start:start + test_weeks]
        folds.append({
            "fold": fold_no,
            "train_start": days[0],
            "train_end": days[start - 1],
            "test_start": test[0],
            "test_end": test[-1],
        })
        start += test_weeks
        fold_no += 1
    return folds
