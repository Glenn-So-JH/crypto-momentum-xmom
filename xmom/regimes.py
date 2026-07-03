"""
regimes.py  -  first-class regime labeling and per-regime metrics (Handoff #7).

A signal that only works in one regime is the thing we most want to catch, so every
discovery backtest reports its metrics broken down by regime, not just overall.

Two orthogonal labelings, both defined in config and documented there:
  1. Trend regime (daily): BULL when BTC close > its 200d SMA, else BEAR.
  2. Named eras: contiguous historical windows (mania/bust, covid, bulls, bears...).
"""

from __future__ import annotations

import pandas as pd

from . import config, metrics


def trend_regime(close: pd.DataFrame) -> pd.Series:
    """Daily label series: 'bull' / 'bear' from the config trend asset and SMA."""
    px = close[config.REGIME_TREND_ASSET]
    sma = px.rolling(config.REGIME_TREND_SMA, min_periods=config.REGIME_TREND_SMA).mean()
    return pd.Series(pd.NA, index=close.index, dtype="object").mask(px > sma, "bull").mask(
        (px <= sma) & sma.notna(), "bear"
    )


def era_labels(index: pd.DatetimeIndex) -> pd.Series:
    """Daily label series from config.REGIME_ERAS (None bounds clamp to the panel)."""
    labels = pd.Series(pd.NA, index=index, dtype="object")
    for name, start, end in config.REGIME_ERAS:
        lo = index[0] if start is None else pd.Timestamp(start)
        hi = index[-1] if end is None else pd.Timestamp(end)
        labels.loc[(index >= lo) & (index <= hi)] = name
    return labels


def per_regime_metrics(returns: pd.Series, labels: pd.Series) -> pd.DataFrame:
    """
    One metrics row per regime label: n_days, total return, CAGR, ann vol, Sharpe,
    max drawdown. Labels with under 30 days are reported but flagged unstable.
    """
    labels = labels.reindex(returns.index)
    rows = []
    seen = []
    for name in labels.dropna().unique():
        if name in seen:
            continue
        seen.append(name)
        r = returns[labels == name]
        if len(r) == 0:
            continue
        rows.append({
            "regime": name,
            "n_days": len(r),
            "total_return": metrics.total_return(r),
            "cagr": metrics.cagr(r) if len(r) >= 30 else float("nan"),
            "ann_vol": metrics.ann_vol(r),
            "sharpe": metrics.sharpe(r),
            "max_drawdown": metrics.max_drawdown(r),
            "stable": len(r) >= 30,
        })
    return pd.DataFrame(rows).set_index("regime")


def regime_report_lines(returns: pd.Series, close: pd.DataFrame, title: str) -> list[str]:
    """Markdown lines for both regime breakdowns of one return series."""
    lines = [f"### Regime breakdown: {title}", ""]
    for label_name, labels in (("trend regime (BTC vs 200d SMA)", trend_regime(close)),
                               ("named eras", era_labels(returns.index))):
        table = per_regime_metrics(returns, labels)
        lines.append(f"**By {label_name}:**")
        lines.append("")
        lines.append("| regime | days | total ret | CAGR | vol | Sharpe | maxDD |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for name, r in table.iterrows():
            flag = "" if r["stable"] else " (short)"
            cagr = f"{r['cagr']:+.1%}" if pd.notna(r["cagr"]) else "n/a"
            lines.append(f"| {name}{flag} | {r['n_days']} | {r['total_return']:+.1%} | {cagr} | "
                         f"{r['ann_vol']:.1%} | {r['sharpe']:+.2f} | {r['max_drawdown']:+.1%} |")
        lines.append("")
    return lines
