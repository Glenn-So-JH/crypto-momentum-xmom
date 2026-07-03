"""WS-B tests: every alpha in the stable is trailing-only, sane, and registry-complete."""

import numpy as np
import pandas as pd
import pytest

from xmom import alphas


def make_close(n=250, seed=17, cols=6):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="D")
    return pd.DataFrame(
        {f"C{i}": 50.0 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n))) for i in range(cols)},
        index=idx,
    )


def test_registry_shapes_and_completeness():
    close = make_close()
    assert len(alphas.ALPHAS) == 9
    for name, spec in alphas.ALPHAS.items():
        sig = spec["fn"](close)
        assert sig.shape == close.shape, name
        assert sig.index.equals(close.index), name
        assert spec["description"] and spec["family"], name


@pytest.mark.parametrize("name", list(alphas.ALPHAS))
def test_every_alpha_is_trailing_only(name):
    close = make_close()
    base = alphas.ALPHAS[name]["fn"](close)
    perturbed = close.copy()
    d = close.index[180]
    perturbed.loc[d:, "C3"] *= 5.0
    bumped = alphas.ALPHAS[name]["fn"](perturbed)
    before = close.index[close.index < d]
    pd.testing.assert_frame_equal(base.loc[before], bumped.loc[before])


def test_donchian_bounded_and_extremes():
    close = make_close()
    sig = alphas.donchian(close, 55)
    valid = sig.dropna(how="all")
    assert valid.max().max() <= 1.0 + 1e-12
    assert valid.min().min() >= -1.0 - 1e-12
    # A fresh 55-day high must sit at exactly +1.
    idx = pd.date_range("2023-01-02", periods=100, freq="D")
    up = pd.DataFrame({"A": np.arange(1.0, 101.0)}, index=idx)  # new high every day
    assert alphas.donchian(up, 55)["A"].iloc[-1] == pytest.approx(1.0)


def test_macd_sign_tracks_trend():
    idx = pd.date_range("2023-01-02", periods=200, freq="D")
    up = pd.DataFrame({"A": 100.0 * 1.01 ** np.arange(200)}, index=idx)
    down = pd.DataFrame({"A": 100.0 * 0.99 ** np.arange(200)}, index=idx)
    assert alphas.macd(up)["A"].iloc[-1] > 0
    assert alphas.macd(down)["A"].iloc[-1] < 0


def test_mom_accel_identity():
    close = make_close()
    sig = alphas.mom_accel(close, 30, 14)
    mom = close.pct_change(30, fill_method=None)
    expected = mom - mom.shift(14)
    pd.testing.assert_frame_equal(sig, expected)


def test_xs_rank_centered_uniform():
    close = make_close(cols=11)
    sig = alphas.xs_rank(close, 21).iloc[-1]
    assert sig.min() == pytest.approx(1 / 11 - 0.5)
    assert sig.max() == pytest.approx(0.5)
    assert abs(sig.mean()) < 0.05
