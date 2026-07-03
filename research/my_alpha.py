"""
my_alpha.py  -  YOUR signal idea lives here. Edit this one file, then run:

    make alpha        (or: python run_alpha.py)

The harness does everything else: gross backtest, regime breakdown, parameter
plateau sweep, walk-forward folds, benchmarks, trials-ledger logging, and a report
at research/my_alpha_report.md. Read docs/ALPHA_SANDBOX.md for the 3-step guide.

THE ONE RULE: your function may only use data up to each decision day. The harness
runs an automatic look-ahead probe (it hides the last weeks of data and checks your
earlier weights do not change), and it will fail your run loudly if you peek.
"""

import pandas as pd

from xmom import engine, strategies

# Give your idea a short name: it labels the report, figures, and ledger rows.
ALPHA_NAME = "xs_momentum_28d_quintile"

# Default parameters for the headline run.
PARAMS = {
    "lookback": 28,   # formation window in days (the literature's crypto sweet spot)
    "quantile": 0.20, # hold the top fifth of the eligible cross-section
}

# The plateau sweep: every combination here is run and logged (keep it SMALL; each
# combination is a real trial that raises the multiple-testing bar for your idea).
PARAM_GRID = {
    "lookback": [14, 21, 28, 56],
    "quantile": [0.10, 0.20, 0.30],
}


def my_alpha(prices: pd.DataFrame, universe: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Return DAILY target weights: same index/columns as `prices`, W >= 0, sum <= 1.

    Contract (the engine applies the t -> t+1 lag itself; never shift):
      - decide weights for day t using only data with timestamps <= t,
      - respect the point-in-time `universe` mask (True = tradable that day),
      - cash is the unweighted remainder and earns zero.

    This working example is classic cross-sectional momentum: each Monday, rank the
    eligible universe by trailing `lookback`-day return and hold the top `quantile`,
    equal-weighted. Replace it with your own idea; the helpers in xmom.strategies
    (trailing_return, eligibility) and plain pandas are both fine.
    """
    t0 = engine.evaluation_window(prices.index, warmup_days=200)
    return strategies.s5_xsmom(
        prices, universe, t0,
        lookback=params["lookback"],
        skip=0,
        top_n=None,
        quantile=params["quantile"],
    )
