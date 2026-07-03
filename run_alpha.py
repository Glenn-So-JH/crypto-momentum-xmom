"""
run_alpha.py  -  Handoff #7 WS2: the discovery gauntlet for research/my_alpha.py.

    python run_alpha.py            # playground run (pre-vault data only)
    python run_alpha.py --vault    # ALSO score the locked OOS vault (one look!)
    make alpha                     # same as the first form

What it does, automatically:
  - loads the discovery panel and hands your alpha ONLY pre-vault data (the vault is
    structurally unseeable during tuning, not merely off-limits),
  - validates the weight contract and runs a look-ahead probe (hides the last 10
    weeks, recomputes, and fails loudly if your earlier weights change),
  - backtests GROSS as the headline, with net-50bps as a tradability footnote,
  - breaks metrics down by regime (trend and named eras),
  - sweeps PARAM_GRID for a plateau-versus-lonely-spike view,
  - runs anchored walk-forward folds (consistency of your FIXED params),
  - benchmarks against BTC buy-and-hold and equal-weight on the same window,
  - appends every executed run to research/TRIALS_LEDGER.csv,
  - writes research/my_alpha_report.md and a figure, with a plain-English verdict.
"""

from __future__ import annotations

import itertools
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from research import my_alpha as alpha_module
from xmom import config, engine, metrics, regimes, strategies, validation

PROBE_HIDE_DAYS = 70  # look-ahead probe hides this many trailing days


def load_playground(vault: bool = False):
    close = pd.read_parquet(config.DATA_PROCESSED / "discovery_close.parquet")
    members = pd.read_parquet(config.DATA_PROCESSED / "discovery_universe.parquet")
    if not vault:
        idx = validation.playground_index(close.index)
        close, members = close.loc[idx], members.loc[idx]
    return close, members


def run_weights(close, members, params) -> pd.DataFrame:
    weights = alpha_module.my_alpha(close, members, dict(params))
    weights = weights.reindex(index=close.index, columns=close.columns).fillna(0.0)
    engine.validate_weights(weights, close)
    return weights


def look_ahead_probe(close, members, params, weights) -> None:
    """Hide the trailing PROBE_HIDE_DAYS; earlier weights must be unchanged."""
    cut = close.index[-PROBE_HIDE_DAYS]
    w_trunc = run_weights(close.loc[close.index < cut], members.loc[members.index < cut], params)
    before = close.index[close.index < cut - pd.Timedelta(days=1)]
    same = weights.loc[before].round(12).equals(w_trunc.loc[before].round(12))
    if not same:
        diff = (weights.loc[before] - w_trunc.loc[before]).abs()
        first_bad = diff.max(axis=1)
        first_bad = first_bad[first_bad > 1e-9].index[0]
        raise SystemExit(
            f"LOOK-AHEAD PROBE FAILED: hiding the last {PROBE_HIDE_DAYS} days changed "
            f"your weights as early as {first_bad.date()}. Your alpha is reading the "
            "future (a centered rolling window, a full-sample normalization, or a "
            "shift in the wrong direction are the usual suspects)."
        )


def backtest(close, weights, cost=0.0):
    result = engine.run_backtest(close, weights, cost_per_side=cost)
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    r = result.net_returns.loc[t0:]
    tau = result.turnover.loc[t0:]
    w = result.weights.loc[t0:]
    return result, metrics.summarize(r, tau, w), r


def benchmarks(close, members):
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    out = {}
    for name, build in (("BTC buy-and-hold", lambda: strategies.s1_buy_and_hold(close, t0, "BTC")),
                        ("Equal-weight universe", lambda: strategies.s2_equal_weight(close, members, t0))):
        w = build().loc[t0:]
        _, m, r = backtest(close, w)
        out[name] = (m, r)
    return out


def plateau_sweep(close, members, ledger_rows, window_label):
    grid_items = sorted(alpha_module.PARAM_GRID.items())
    keys = [k for k, _ in grid_items]
    combos = list(itertools.product(*[v for _, v in grid_items]))
    if len(combos) > 32:
        print(f"WARNING: PARAM_GRID has {len(combos)} combinations; capping at 32. "
              "A big grid is a big multiple-testing bill.")
        combos = combos[:32]
    rows = []
    for combo in combos:
        params = {**alpha_module.PARAMS, **dict(zip(keys, combo))}
        try:
            w = run_weights(close, members, params)
            _, m, _ = backtest(close, w)
        except Exception as exc:
            rows.append({**dict(zip(keys, combo)), "sharpe": np.nan, "error": str(exc)[:60]})
            continue
        rows.append({**dict(zip(keys, combo)), "sharpe": m["sharpe"],
                     "max_drawdown": m["max_drawdown"], "annual_turnover": m["annual_turnover"]})
        ledger_rows.append({
            "run_id": f"{alpha_module.ALPHA_NAME}_sweep_{'_'.join(str(c) for c in combo)}",
            "strategy_family": f"sandbox_{alpha_module.ALPHA_NAME}",
            "parameters": {**params, "cost_per_side": 0.0, "panel": "discovery_playground"},
            "data_window": window_label, "gross_or_net": "gross",
            "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
            "annual_turnover": round(m["annual_turnover"], 4),
            "why_run": "alpha sandbox plateau sweep",
        })
    return pd.DataFrame(rows), keys


def fold_consistency(returns, close):
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    reb = engine.rebalance_days(close.index, start=t0)
    folds = validation.walk_forward_folds(reb, config.WF_INITIAL_TRAIN_WEEKS, config.WF_TEST_WEEKS)
    rows = []
    for f in folds:
        r = returns.loc[f["test_start"]:f["test_end"] + pd.Timedelta(days=6)]
        rows.append({"fold": f["fold"], "start": f["test_start"].date().isoformat(),
                     "end": f["test_end"].date().isoformat(),
                     "return": float((1 + r).prod() - 1), "sharpe": metrics.sharpe(r)})
    return pd.DataFrame(rows)


def main():
    vault_requested = "--vault" in sys.argv
    close, members = load_playground(vault=False)
    window_label = f"{close.index[0].date()}..{close.index[-1].date()} (playground)"
    name = alpha_module.ALPHA_NAME
    print(f"Alpha: {name}   params: {alpha_module.PARAMS}")
    print(f"Playground: {window_label}; the vault ({config.OOS_VAULT_START}+) is "
          f"{'ALSO SCORED THIS RUN (one look!)' if vault_requested else 'locked away'}\n")

    ledger_rows = []
    weights = run_weights(close, members, alpha_module.PARAMS)
    look_ahead_probe(close, members, alpha_module.PARAMS, weights)
    print("Look-ahead probe: PASS")

    result, m_gross, r_gross = backtest(close, weights)
    _, m_net50, _ = backtest(close, weights, cost=config.COST_PER_SIDE_DECIDING)
    bench = benchmarks(close, members)
    sweep, sweep_keys = plateau_sweep(close, members, ledger_rows, window_label)
    folds = fold_consistency(r_gross, close)

    ledger_rows.append({
        "run_id": f"{name}_headline", "strategy_family": f"sandbox_{name}",
        "parameters": {**alpha_module.PARAMS, "cost_per_side": 0.0, "panel": "discovery_playground"},
        "data_window": window_label, "gross_or_net": "gross",
        "sharpe": round(m_gross["sharpe"], 4), "max_drawdown": round(m_gross["max_drawdown"], 4),
        "annual_turnover": round(m_gross["annual_turnover"], 4),
        "why_run": "alpha sandbox headline run",
    })

    vault_block = None
    if vault_requested:
        close_f, members_f = load_playground(vault=True)
        w_full = run_weights(close_f, members_f, alpha_module.PARAMS)
        res_f = engine.run_backtest(close_f, w_full, cost_per_side=0.0)
        vr = res_f.net_returns.loc[validation.vault_index(res_f.net_returns.index)]
        vault_block = {
            "n_days": len(vr), "total_return": metrics.total_return(vr),
            "sharpe": metrics.sharpe(vr), "max_drawdown": metrics.max_drawdown(vr),
        }
        ledger_rows.append({
            "run_id": f"{name}_VAULT", "strategy_family": f"sandbox_{name}",
            "parameters": {**alpha_module.PARAMS, "cost_per_side": 0.0, "panel": "discovery_vault"},
            "data_window": f"{config.OOS_VAULT_START}..{close_f.index[-1].date()} (VAULT)",
            "gross_or_net": "gross", "sharpe": round(vault_block["sharpe"], 4),
            "max_drawdown": round(vault_block["max_drawdown"], 4),
            "annual_turnover": np.nan, "why_run": "alpha sandbox VAULT SCORING (one look)",
        })

    validation.append_trials(ledger_rows)
    k = validation.count_trials(f"sandbox_{name}")

    # Plain-English verdict.
    se = (52 / max(m_gross["n_days"] / 7, 1)) ** 0.5
    btc_sharpe = bench["BTC buy-and-hold"][0]["sharpe"]
    ew_sharpe = bench["Equal-weight universe"][0]["sharpe"]
    beats = m_gross["sharpe"] > max(btc_sharpe, ew_sharpe)
    plateau_ok = bool(sweep["sharpe"].notna().all() and
                      (np.sign(sweep["sharpe"]) == np.sign(m_gross["sharpe"])).mean() >= 0.75)
    pos_folds = int((folds["return"] > 0).sum())
    verdict = []
    verdict.append(f"Gross Sharpe {m_gross['sharpe']:+.2f} vs BTC {btc_sharpe:+.2f} and "
                   f"equal-weight {ew_sharpe:+.2f}: "
                   + ("BEATS both benchmarks" if beats else "does NOT beat both benchmarks")
                   + " on the playground.")
    verdict.append(f"Noise floor: the Sharpe standard error here is ~{se:.2f}, and this idea's "
                   f"family has K={k} ledger trials, so treat anything under "
                   f"~{2 * se:.1f} as indistinguishable from selection noise.")
    verdict.append(f"Parameter plateau: {'stable (>=75% of the grid shares the headline sign)' if plateau_ok else 'FRAGILE: the grid flips sign; suspect a lonely spike'}.")
    verdict.append(f"Fold consistency: positive in {pos_folds}/{len(folds)} walk-forward folds.")
    verdict.append(f"Tradability preview (NOT a discovery criterion): net-50bps Sharpe "
                   f"{m_net50['sharpe']:+.2f} at {m_gross['annual_turnover']:.0%}/yr turnover.")

    write_report(name, close, m_gross, m_net50, bench, sweep, sweep_keys, folds,
                 verdict, vault_block, r_gross, k)
    make_figure(name, r_gross, bench)

    print(f"\nHeadline gross: Sharpe {m_gross['sharpe']:+.2f}, CAGR {m_gross['cagr']:+.1%}, "
          f"maxDD {m_gross['max_drawdown']:+.1%}, turnover {m_gross['annual_turnover']:.0%}")
    for line in verdict:
        print("  - " + line)
    if vault_block:
        print(f"\nVAULT (one look, now spent): Sharpe {vault_block['sharpe']:+.2f}, "
              f"total {vault_block['total_return']:+.1%}, maxDD {vault_block['max_drawdown']:+.1%}")
    print("\nReport: research/my_alpha_report.md")


def fmt_pct(x):
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt2(x):
    return f"{x:+.2f}" if pd.notna(x) else "n/a"


def write_report(name, close, m_gross, m_net50, bench, sweep, sweep_keys, folds,
                 verdict, vault_block, r_gross, k):
    L = [f"# Alpha sandbox report: `{name}`", ""]
    L.append(f"Playground window: {close.index[0].date()} to {close.index[-1].date()} "
             f"(vault {config.OOS_VAULT_START}+ excluded from all tuning). Panel: discovery "
             f"(broad, gross-judged). Params: `{alpha_module.PARAMS}`. Ledger trials for this "
             f"family: K = {k}.")
    L.append("")
    L.append("## Verdict (plain English)")
    L.append("")
    for line in verdict:
        L.append(f"- {line}")
    L.append("")
    L.append("## Headline metrics (GROSS decides at discovery; net is a preview)")
    L.append("")
    L.append("| series | Sharpe | CAGR | vol | maxDD | Calmar | turnover/yr | TIM |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    rows = [(f"{name} (gross)", m_gross), (f"{name} (net 50bps preview)", m_net50)]
    rows += [(f"benchmark: {b}", bm) for b, (bm, _) in bench.items()]
    for label, m in rows:
        L.append(f"| {label} | {fmt2(m['sharpe'])} | {fmt_pct(m['cagr'])} | {m['ann_vol']:.1%} | "
                 f"{fmt_pct(m['max_drawdown'])} | {fmt2(m['calmar'])} | "
                 f"{m['annual_turnover']:.0%} | {m['time_in_market']:.0%} |")
    L.append("")
    L.append(f"![equity](figures/{name}_equity.png)")
    L.append("")
    L += regimes.regime_report_lines(r_gross, close, f"{name} (gross)")
    L.append("## Parameter plateau sweep (gross Sharpe per combination)")
    L.append("")
    L.append("| " + " | ".join(sweep_keys) + " | Sharpe | maxDD | turnover |")
    L.append("|" + "---|" * (len(sweep_keys) + 3))
    for _, r in sweep.iterrows():
        cells = [str(r[key]) for key in sweep_keys]
        L.append("| " + " | ".join(cells) + f" | {fmt2(r.get('sharpe'))} | "
                 f"{fmt_pct(r.get('max_drawdown'))} | "
                 + (f"{r['annual_turnover']:.0%} |" if pd.notna(r.get("annual_turnover")) else "n/a |"))
    L.append("")
    L.append("## Walk-forward folds (fixed params; consistency, not selection)")
    L.append("")
    L.append("| fold | window | return | Sharpe |")
    L.append("|---|---|---:|---:|")
    for _, r in folds.iterrows():
        L.append(f"| {int(r['fold'])} | {r['start']} to {r['end']} | {fmt_pct(r['return'])} | "
                 f"{fmt2(r['sharpe'])} |")
    L.append("")
    if vault_block:
        L.append("## VAULT SCORE (the one look, now spent)")
        L.append("")
        L.append(f"Window {config.OOS_VAULT_START} onward: **Sharpe {fmt2(vault_block['sharpe'])}**, "
                 f"total return {fmt_pct(vault_block['total_return'])}, "
                 f"maxDD {fmt_pct(vault_block['max_drawdown'])} over {vault_block['n_days']} days. "
                 "Re-running the vault after further tuning invalidates it as out-of-sample "
                 "evidence; any new look must be declared as such in the ledger.")
        L.append("")
    L.append("*(Discovery judges gross performance and regime robustness on the broad panel. "
             "Kraken tradability, thin-universe constraints, and the DEC-002 cost lens are a "
             "later gate for survivors. See docs/ALPHA_SANDBOX.md.)*")
    (config.REPO_ROOT / "research" / "my_alpha_report.md").write_text("\n".join(L) + "\n")


def make_figure(name, r_gross, bench):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot((1 + r_gross).cumprod(), label=f"{name} (gross)", linewidth=1.8)
    for b, (bm, br) in bench.items():
        ax.plot((1 + br).cumprod(), label=b, linewidth=1.0, alpha=0.85)
    ax.set_yscale("log")
    ax.set_title(f"{name}: playground equity, gross (log scale)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / f"{name}_equity.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
