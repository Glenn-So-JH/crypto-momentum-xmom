"""
discovery_baselines.py  -  Handoff #7 WS1: re-run the ladder + Phase 2 GROSS on the
broad discovery panel and report how conclusions change versus the Kraken-thin panel.

These runs are benchmarks, not tuning, so they use the full window (including the
vault era) for comparability with Stage C/D; the OOS vault discipline applies to
NEW signal work in the alpha sandbox, not to these fixed reference strategies.

Run it (after discovery_build.py):
    python discovery_baselines.py

Writes research/DISCOVERY_BASELINES.md (+ figure), appends every run to the ledger.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from xmom import config, engine, metrics, phase2, regimes, strategies, validation


def load():
    close = pd.read_parquet(config.DATA_PROCESSED / "discovery_close.parquet")
    members = pd.read_parquet(config.DATA_PROCESSED / "discovery_universe.parquet")
    return close, members


def run_ladder(close, members, t0):
    runs = [
        ("S1", "buy_and_hold", {"asset": "BTC"},
         lambda: strategies.s1_buy_and_hold(close, t0, "BTC")),
        ("S2", "equal_weight", {},
         lambda: strategies.s2_equal_weight(close, members, t0)),
        ("S3a", "ma_filter", {"asset": "BTC", "N": 200},
         lambda: strategies.s3_ma_filter(close, t0, "BTC", 200)),
        ("S3b", "ma_filter", {"asset": "BTC", "N": 100},
         lambda: strategies.s3_ma_filter(close, t0, "BTC", 100)),
        ("S4a", "tsmom", {"L": 90, "k": 0},
         lambda: strategies.s4_tsmom(close, members, t0, 90)),
        ("S4b", "tsmom", {"L": 30, "k": 0},
         lambda: strategies.s4_tsmom(close, members, t0, 30)),
        ("S5a", "xsmom", {"L": 30, "k": 0, "select": "top3"},
         lambda: strategies.s5_xsmom(close, members, t0, 30, 0, top_n=3)),
        ("S5b", "xsmom", {"L": 30, "k": 7, "select": "top3"},
         lambda: strategies.s5_xsmom(close, members, t0, 30, 7, top_n=3)),
        ("S5c", "xsmom", {"L": 30, "k": 0, "select": "q20"},
         lambda: strategies.s5_xsmom(close, members, t0, 30, 0, top_n=None, quantile=0.20)),
        ("S6", "reversal", {"L": 7, "select": "bottom3"},
         lambda: strategies.s6_reversal(close, members, t0, 7, 3)),
    ]
    out = {}
    for run_id, family, params, build in runs:
        weights = build().loc[t0:]
        result = engine.run_backtest(close, weights, cost_per_side=0.0)
        m = metrics.summarize(result.net_returns, result.turnover, result.weights)
        out[run_id] = (result, m, family, params)
        print(f"{run_id:<5} gross Sharpe {m['sharpe']:+.2f}  maxDD {m['max_drawdown']:+.1%}  "
              f"turnover {m['annual_turnover']:.0%}")
    return out


def run_phase2(close, members, t0):
    out = {}
    for run_id, mode in (("BASE_21", "tsmom"), ("CHAL_21", "xsmom")):
        targets = phase2.build_targets(close, members, t0, lookback=21, mode=mode, top_n=3)
        result = engine.run_drift_backtest(close, targets, members, band=0.20, cost_per_side=0.0)
        m = metrics.summarize(result.net_returns, result.turnover, result.weights)
        out[run_id] = (result, m, f"phase2_{'base' if mode == 'tsmom' else 'challenger'}",
                       {"lookback": 21, "mode": mode, "band": 0.20})
        print(f"{run_id:<8} gross Sharpe {m['sharpe']:+.2f}  maxDD {m['max_drawdown']:+.1%}  "
              f"turnover {m['annual_turnover']:.0%}  TIM {m['time_in_market']:.0%}")
    return out


def main():
    close, members = load()
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    window = f"{t0.date()}..{close.index[-1].date()}"
    print(f"Discovery evaluation window: {window}\n")

    print("=== Ladder (gross, broad universe) ===")
    ladder = run_ladder(close, members, t0)
    print("\n=== Phase 2 head-to-head (gross, broad universe) ===")
    p2 = run_phase2(close, members, t0)

    all_runs = {**ladder, **p2}
    ledger_rows = [{
        "run_id": f"DISC_{run_id}_gross", "strategy_family": family,
        "parameters": {**params, "cost_per_side": 0.0, "panel": "discovery"},
        "data_window": window, "gross_or_net": "gross",
        "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
        "annual_turnover": round(m["annual_turnover"], 4),
        "why_run": "Handoff 7 WS1 discovery baseline (broad universe, gross)",
    } for run_id, (result, m, family, params) in all_runs.items()]
    validation.append_trials(ledger_rows)

    # Old-panel gross numbers for comparison, straight from committed artifacts.
    old_ladder = pd.read_csv(config.DATA_PROCESSED / "phase1_table.csv", index_col=0)
    ledger = pd.read_csv(validation.LEDGER_PATH)
    old_p2 = {rid: ledger[ledger["run_id"] == f"{rid}_gross"].iloc[0]
              for rid in ("BASE_21", "CHAL_21")}

    write_report(all_runs, old_ladder, old_p2, close, t0, window)
    make_figure(all_runs, t0)
    print("\nReport: research/DISCOVERY_BASELINES.md")


def fmt_pct(x):
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt2(x):
    return f"{x:+.2f}" if pd.notna(x) else "n/a"


def write_report(all_runs, old_ladder, old_p2, close, t0, window):
    mondays = close.index[(close.index.weekday == 0) & (close.index >= t0)]
    L = ["# Discovery baselines: the ladder and Phase 2 re-run GROSS on the broad universe", ""]
    L.append(f"Window: **{window}** ({len(mondays)} weekly observations). Universe: discovery panel "
             f"(Binance single-source, >= ${config.DISCOVERY_LIQUIDITY_MIN_USD/1e6:.0f}M/day "
             "point-in-time screen, dead coins included, halt-split). All numbers GROSS: this "
             "compares signal shapes across universes, not tradability. Old-panel numbers are the "
             "Kraken execution panel from PHASE1_RESULTS.md / PHASE2_RESULTS.md (gross columns).")
    L.append("")
    L.append("| run | new gross Sharpe | old gross Sharpe | new maxDD | old maxDD | new turnover | old turnover |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for run_id, (result, m, family, params) in all_runs.items():
        if run_id in old_ladder.index:
            o_sh, o_dd, o_to = (old_ladder.loc[run_id, "sharpe"],
                                old_ladder.loc[run_id, "max_drawdown"],
                                old_ladder.loc[run_id, "annual_turnover"])
        else:
            row = old_p2[run_id]
            o_sh, o_dd, o_to = row["sharpe"], row["max_drawdown"], row["annual_turnover"]
        L.append(f"| {run_id} | {fmt2(m['sharpe'])} | {fmt2(float(o_sh))} | "
                 f"{fmt_pct(m['max_drawdown'])} | {fmt_pct(float(o_dd))} | "
                 f"{m['annual_turnover']:.0%} | {float(o_to):.0%} |")
    L.append("")
    L.append("![discovery equity](figures/discovery_baselines.png)")
    L.append("")
    for run_id in ("BASE_21", "CHAL_21", "S5a"):
        result = all_runs[run_id][0]
        L += regimes.regime_report_lines(result.net_returns, close, f"{run_id} (gross, discovery panel)")
    L.append("## Observations")
    L.append("")
    L.append("<!-- filled after the run -->")
    (config.REPO_ROOT / "research" / "DISCOVERY_BASELINES.md").write_text("\n".join(L) + "\n")


def make_figure(all_runs, t0):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for run_id, (result, m, family, params) in all_runs.items():
        style = {"linewidth": 2.0} if run_id in ("BASE_21", "CHAL_21") else {"linewidth": 0.9, "alpha": 0.8}
        ax.plot(result.equity.index, result.equity, label=run_id, **style)
    ax.set_yscale("log")
    ax.set_title(f"Discovery panel, gross equity (start {t0.date()} = 1.0)")
    ax.legend(ncol=6, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "discovery_baselines.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
