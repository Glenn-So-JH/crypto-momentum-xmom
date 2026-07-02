"""
phase1_run_ladder.py  -  Stage C: the classic-strategy validation ladder (S1 to S6).

Runs the exact 10-run grid from docs/03_STRATEGY_SPECS.md section 8 through the engine:
gross (costs off, the spec's own setting) plus net at 50 and 25 bps per side (DEC-002,
MASTER_BRIEF Stage C). Produces:

  research/PHASE1_RESULTS.md          comparison table, gate checks, observations
  research/figures/phase1_equity.png  all gross equity curves, log scale, shared axes
  research/figures/phase1_drawdown.png  drawdown curves, shared axes
  research/TRIALS_LEDGER.csv          one appended row per executed run x cost level

Run it (after phase1_build_universe.py):
    python phase1_run_ladder.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from xmom import config, engine, metrics, strategies, validation

GROSS = 0.0
NET_OPT = config.COST_PER_SIDE_OPTIMISTIC  # 25 bps
NET_DEC = config.COST_PER_SIDE_DECIDING    # 50 bps


def load_panels():
    close = pd.read_parquet(config.DATA_PROCESSED / "close.parquet")
    members = pd.read_parquet(config.DATA_PROCESSED / "universe.parquet")
    return close, members


def run_grid():
    close, members = load_panels()
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)

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

    window = f"{t0.date()}..{close.index[-1].date()}"
    table_rows, ledger_rows, curves = [], [], {}
    for run_id, family, params, build in runs:
        weights = build().loc[t0:]
        per_cost = {}
        for label, cost in (("gross", GROSS), ("net25", NET_OPT), ("net50", NET_DEC)):
            result = engine.run_backtest(close, weights, cost_per_side=cost)
            m = metrics.summarize(result.net_returns, result.turnover, result.weights)
            per_cost[label] = (result, m)
            ledger_rows.append({
                "run_id": f"{run_id}_{label}", "strategy_family": family,
                "parameters": {**params, "cost_per_side": cost},
                "data_window": window, "gross_or_net": label,
                "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
                "annual_turnover": round(m["annual_turnover"], 4),
                "why_run": "Stage C validation ladder (MASTER_BRIEF; spec docs/03 section 8)",
            })
        g = per_cost["gross"][1]
        table_rows.append({
            "run_id": run_id, "family": family, "params": json.dumps(params),
            **{k: g[k] for k in ("total_return", "cagr", "ann_vol", "sharpe", "sortino",
                                  "max_drawdown", "calmar", "annual_turnover", "hit_rate",
                                  "time_in_market")},
            "net25_sharpe": per_cost["net25"][1]["sharpe"],
            "net25_cagr": per_cost["net25"][1]["cagr"],
            "net50_sharpe": per_cost["net50"][1]["sharpe"],
            "net50_cagr": per_cost["net50"][1]["cagr"],
        })
        curves[run_id] = per_cost["gross"][0]
        print(f"{run_id:<5} gross Sharpe {g['sharpe']:+.2f}  maxDD {g['max_drawdown']:+.1%}  "
              f"turnover {g['annual_turnover']:.1%}  net50 Sharpe {per_cost['net50'][1]['sharpe']:+.2f}")

    table = pd.DataFrame(table_rows).set_index("run_id")
    validation.append_trials(ledger_rows)

    # --- Gate checks (spec section 8 predicted ordering + S1 calibration) ----------
    checks = {}
    btc = close["BTC"].loc[t0:]
    s1_equity = curves["S1"].equity
    checks["s1_reproduces_btc"] = bool(np.allclose(s1_equity.iloc[1:],
                                                   (btc / btc.iloc[0]).iloc[1:], rtol=1e-10))
    tau = table["annual_turnover"]
    checks["turnover_ordering"] = bool(tau["S5a"] > tau["S4a"] > tau["S2"] > tau["S1"])
    tim = table["time_in_market"]
    checks["full_exposure_strategies"] = bool(min(tim["S2"], tim["S5a"], tim["S6"]) > 0.99)
    checks["filtered_strategies_below_full"] = bool(max(tim["S3a"], tim["S3b"], tim["S4a"]) < 1.0)
    dd = table["max_drawdown"]
    checks["s3_s4_shallower_than_s1"] = bool(max(dd["S3a"], dd["S4a"]) > dd["S1"])  # less negative
    checks["s6_not_best"] = bool(table["sharpe"]["S6"] < table["sharpe"].drop("S6").max())

    return table, curves, checks, t0, close


def make_figures(curves, t0):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for run_id, result in curves.items():
        ax.plot(result.equity.index, result.equity, label=run_id, linewidth=1.2)
    ax.set_yscale("log")
    ax.set_title(f"Stage C validation ladder: gross equity curves (start {t0.date()} = 1.0)")
    ax.set_ylabel("equity (log scale)")
    ax.legend(ncol=5, fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "phase1_equity.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    for run_id, result in curves.items():
        dd = result.equity / result.equity.cummax() - 1.0
        ax.plot(dd.index, dd, label=run_id, linewidth=1.0)
    ax.set_title("Stage C validation ladder: drawdown curves (gross)")
    ax.set_ylabel("drawdown")
    ax.legend(ncol=5, fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "phase1_drawdown.png", dpi=150)
    plt.close(fig)


def fmt_pct(x):
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt2(x):
    return f"{x:+.2f}" if pd.notna(x) else "n/a"


def write_report(table, checks, t0, close):
    mondays = close.index[(close.index.weekday == 0) & (close.index >= t0)]
    lines = ["# Phase 1 results: the classic-strategy validation ladder (Stage C)", ""]
    lines.append(f"Window: **{t0.date()} to {close.index[-1].date()}** "
                 f"({len(mondays)} weekly rebalance observations). Universe: point-in-time "
                 f"liquidity-screened Kraken USD pairs (see research/stage_a_data_report.md). "
                 f"Annualization 365. Weekly Monday rebalance. Tie-breaks alphabetical.")
    lines.append("")
    lines.append("## Pre-registration (from docs/03, written before any run)")
    lines.append("")
    lines.append("The grid is the ten required runs of docs/03 section 8, run gross (the spec's "
                 "setting) plus net at 25 and 50 bps per side (DEC-002). Predicted orderings, "
                 "registered in the spec before execution:")
    lines.append("")
    lines.append("- Max drawdown shallowest to deepest: S3a/S3b and S4a shallowest; S1 middle; S2, S5x, S6 deepest.")
    lines.append("- Turnover lowest to highest: S1 < S3x < S2 < S4x < S5x and S6.")
    lines.append("- Time-in-market: S1 = S2 = S5x = S6 = 100%; S3x and S4x below 100%.")
    lines.append("- S6 is the weakest or among the weakest; if S6 dramatically beats S5, suspect the harness.")
    lines.append("")
    lines.append("## Comparison table (gross of costs)")
    lines.append("")
    lines.append("| run | params | total ret | CAGR | vol | Sharpe | Sortino | maxDD | Calmar | turnover/yr | hit | TIM |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for run_id, r in table.iterrows():
        lines.append(
            f"| {run_id} | `{r['params']}` | {fmt_pct(r['total_return'])} | {fmt_pct(r['cagr'])} | "
            f"{r['ann_vol']:.1%} | {fmt2(r['sharpe'])} | {fmt2(r['sortino'])} | "
            f"{fmt_pct(r['max_drawdown'])} | {fmt2(r['calmar'])} | {r['annual_turnover']:.0%} | "
            f"{r['hit_rate']:.1%} | {r['time_in_market']:.0%} |"
        )
    lines.append("")
    lines.append("## Net of costs (DEC-002: 50 bps/side decides, 25 bps/side optimistic)")
    lines.append("")
    lines.append("| run | gross Sharpe | net Sharpe @25bps | net Sharpe @50bps | gross CAGR | net CAGR @25bps | net CAGR @50bps |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for run_id, r in table.iterrows():
        lines.append(
            f"| {run_id} | {fmt2(r['sharpe'])} | {fmt2(r['net25_sharpe'])} | {fmt2(r['net50_sharpe'])} | "
            f"{fmt_pct(r['cagr'])} | {fmt_pct(r['net25_cagr'])} | {fmt_pct(r['net50_cagr'])} |"
        )
    lines.append("")
    lines.append("![equity](figures/phase1_equity.png)")
    lines.append("")
    lines.append("![drawdown](figures/phase1_drawdown.png)")
    lines.append("")
    lines.append("## Gate checks")
    lines.append("")
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {name}")
    lines.append("")
    lines.append("## Observations")
    lines.append("")
    lines.append("<!-- filled in by the run report below -->")
    lines.append("")
    lines.append("## Thin-universe warning (restated verbatim from docs/03 section 5)")
    lines.append("")
    lines.append("> Our screened universe is thin. Top-3 means each pick is a third of the book, so this "
                 "is a concentrated bet on 3 coins, not a diversified factor portfolio. Consequences: "
                 "(i) single-name events hit the equity curve hard; (ii) performance statistics will be "
                 "noisy and regime-dependent, so do not over-read Sharpe differences between XS variants "
                 "on this window; (iii) the classic academic decile construction is impossible here, which "
                 "is why we use top-N and top-quintile instead; (iv) any later improvement to XS momentum "
                 "must first be checked against the possibility that it is just noise from 3-name "
                 "concentration.")
    lines.append("")
    lines.append("## Statistical power statement (docs/04 section 3.2)")
    lines.append("")
    se = (52 / len(mondays)) ** 0.5
    lines.append(f"This window contains {len(mondays)} weekly observations, so the annualized Sharpe "
                 f"standard error is roughly {se:.2f} and a 95% confidence interval on any Sharpe here is "
                 f"about plus or minus {1.96 * se:.1f}. Nothing in these tables is statistical proof of an "
                 f"edge; the grid itself is 10 runs, and the expected best Sharpe of 10 pure-noise trials "
                 f"on this sample is material (docs/04 section 1.1). These runs validate the ENGINE and "
                 f"build intuition. They do not certify any strategy.")
    lines.append("")
    (config.REPO_ROOT / "research" / "PHASE1_RESULTS.md").write_text("\n".join(lines) + "\n")


def main():
    table, curves, checks, t0, close = run_grid()
    make_figures(curves, t0)
    write_report(table, checks, t0, close)
    print("\nGate checks:")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    table.to_csv(config.DATA_PROCESSED / "phase1_table.csv")
    print(f"\nReport: research/PHASE1_RESULTS.md; figures in research/figures/.")
    return table, checks


if __name__ == "__main__":
    main()
