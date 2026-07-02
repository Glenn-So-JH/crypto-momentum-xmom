"""
phase2_run.py  -  Stage D: the Phase 2 base case vs the cross-sectional challenger.

Pre-registered per docs/05 (DEC-001/002/003) and MASTER_BRIEF Stage D. Decision runs:
  BASE_21: TSMOM L=21 + BTC 200d gate + inverse-vol (25% cap) + 30% vol target, band 20%
  BASE_14: same, L=14 (secondary lookback)
  CHAL_21: XS top-3 by trailing 21d return, identical overlays

plus six registered robustness neighbors on the base (excluded from selection):
L=28, gate=100, vol target 20% and 40%, band 10% and 30%.

Every run goes to the trials ledger. Decisions are made on the net-50bps column only.
Walk-forward folds report consistency of the FROZEN defaults (no per-fold selection).

Run it (after phase1_run_ladder.py):
    python phase2_run.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from xmom import config, engine, metrics, phase2, validation

BAND = 0.20
COSTS = (("gross", 0.0), ("net25", config.COST_PER_SIDE_OPTIMISTIC),
         ("net50", config.COST_PER_SIDE_DECIDING))

REGISTRATION = """\
## Registration block (committed before results were generated)

1. **Question.** Does relative (cross-sectional top-3) selection beat absolute
   (time-series own-return) selection on our venue and universe, when both carry the
   same BTC 200d gate, inverse-vol sizing with a 25% cap, 30% vol target, weekly
   rebalance with a 20% no-trade band, judged net of 50 bps per side?
2. **Configurations.** Decision runs: BASE_21 (TSMOM L=21), BASE_14 (TSMOM L=14),
   CHAL_21 (XS top-3, L=21, k=0). Robustness neighbors on BASE_21, excluded from
   selection: L=28; gate=100; vol target 20% and 40%; band 10% and 30%. Each decision
   run at gross, 25, and 50 bps per side; neighbors at 50 bps. All runs ledger-logged.
3. **Prediction.** Base case beats challenger net of costs (literature prior: TS more
   robust than XS in crypto; thin universe penalizes ranking; XS turnover costs more).
   Base case beats equal-weight (S2) and buy-and-hold BTC (S1) on Sharpe and Calmar
   with materially shallower max drawdown, and does NOT beat BTC on total return.
4. **Decision rule (Gate 2C).** The challenger is kept only if it beats the base case
   on net-50bps Sharpe AND on walk-forward fold win rate (>50% of folds). Ties or
   ambiguity go to the base case. If the base case fails its own success criteria
   (docs/05 section 2), Phase 2 pauses for a rethink; nothing is decorated.
5. **Window and costs.** Full common evaluation window (200-day warmup); costs per
   DEC-002 via the drift-aware engine with no-trade bands. Vol sizing window 30d,
   covariance window 90d, both registered here before running.
"""


def per_coin_contribution(result) -> pd.Series:
    """Arithmetic per-coin P&L contribution: sum_t W_i(t-1) * r_i(t)."""
    w_lag = result.weights.shift(1).fillna(0.0)
    close = pd.read_parquet(config.DATA_PROCESSED / "close.parquet")
    rets = close[result.weights.columns].pct_change(fill_method=None).reindex(result.weights.index)
    return (w_lag * rets).sum(axis=0, skipna=True).sort_values(ascending=False)


def run_one(close, members, t0, run_id, why, ledger_rows, cost_levels=COSTS, **params):
    targets = phase2.build_targets(
        close, members, t0,
        lookback=params.get("lookback", 21),
        mode=params.get("mode", "tsmom"),
        top_n=params.get("top_n", 3),
        vol_target=params.get("vol_target", phase2.VOL_TARGET),
        gate_n=params.get("gate_n", phase2.GATE_SMA),
    )
    band = params.get("band", BAND)
    window = f"{t0.date()}..{close.index[-1].date()}"
    out = {}
    for label, cost in cost_levels:
        result = engine.run_drift_backtest(close, targets, members, band=band, cost_per_side=cost)
        m = metrics.summarize(result.net_returns, result.turnover, result.weights)
        out[label] = (result, m)
        family = "phase2_base" if params.get("mode", "tsmom") == "tsmom" else "phase2_challenger"
        ledger_rows.append({
            "run_id": f"{run_id}_{label}", "strategy_family": family,
            "parameters": {**params, "band": band, "cost_per_side": cost},
            "data_window": window, "gross_or_net": label,
            "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
            "annual_turnover": round(m["annual_turnover"], 4), "why_run": why,
        })
    g, n50 = out.get("gross", (None, {}))[1], out["net50"][1]
    print(f"{run_id:<22} gross Sharpe {g.get('sharpe', float('nan')):+.2f}  "
          f"net50 Sharpe {n50['sharpe']:+.2f}  maxDD {n50['max_drawdown']:+.1%}  "
          f"turnover {n50['annual_turnover']:.0%}  TIM {n50['time_in_market']:.0%}")
    return out


def fold_table(result, folds) -> pd.DataFrame:
    rows = []
    for f in folds:
        r = result.net_returns.loc[f["test_start"]:f["test_end"] + pd.Timedelta(days=6)]
        rows.append({
            "fold": f["fold"],
            "test_start": f["test_start"].date().isoformat(),
            "test_end": f["test_end"].date().isoformat(),
            "return": float((1 + r).prod() - 1),
            "sharpe": metrics.sharpe(r),
        })
    return pd.DataFrame(rows).set_index("fold")


def main():
    close = pd.read_parquet(config.DATA_PROCESSED / "close.parquet")
    members = pd.read_parquet(config.DATA_PROCESSED / "universe.parquet")
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    ledger_rows: list[dict] = []

    print("=== Decision runs ===")
    base21 = run_one(close, members, t0, "BASE_21", "Phase 2 decision run (registered)",
                     ledger_rows, lookback=21, mode="tsmom")
    base14 = run_one(close, members, t0, "BASE_14", "Phase 2 decision run (registered)",
                     ledger_rows, lookback=14, mode="tsmom")
    chal21 = run_one(close, members, t0, "CHAL_21", "Phase 2 decision run (registered)",
                     ledger_rows, lookback=21, mode="xsmom", top_n=3)

    print("=== Robustness neighbors (excluded from selection) ===")
    net50_only = (("net50", config.COST_PER_SIDE_DECIDING),)
    neighbors = {}
    for run_id, params in [
        ("NBR_L28", {"lookback": 28}),
        ("NBR_GATE100", {"lookback": 21, "gate_n": 100}),
        ("NBR_VT20", {"lookback": 21, "vol_target": 0.20}),
        ("NBR_VT40", {"lookback": 21, "vol_target": 0.40}),
        ("NBR_BAND10", {"lookback": 21, "band": 0.10}),
        ("NBR_BAND30", {"lookback": 21, "band": 0.30}),
    ]:
        neighbors[run_id] = run_one(close, members, t0, run_id,
                                    "Phase 2 registered robustness neighbor (not for selection)",
                                    ledger_rows, mode="tsmom", cost_levels=net50_only, **params)

    validation.append_trials(ledger_rows)

    # Walk-forward fold consistency (frozen params, no selection).
    reb = engine.rebalance_days(close.index, start=t0)
    folds = validation.walk_forward_folds(reb, initial_train_weeks=52, test_weeks=13)
    base_folds = fold_table(base21["net50"][0], folds)
    chal_folds = fold_table(chal21["net50"][0], folds)
    base_wins = int((base_folds["return"] > chal_folds["return"]).sum())
    chal_wins = int((chal_folds["return"] > base_folds["return"]).sum())

    # DSR for the base candidate, K from the ledger's phase2_base family.
    ledger = pd.read_csv(validation.LEDGER_PATH)
    fam = ledger[ledger["strategy_family"] == "phase2_base"]
    k = len(fam)
    dsr = validation.deflated_sharpe(base21["net50"][0].net_returns, k,
                                     fam["sharpe"].astype(float).tolist())

    # Single-name dependence.
    contrib = per_coin_contribution(base21["net50"][0])
    total_pos = contrib[contrib > 0].sum()
    top_share = float(contrib.iloc[0] / total_pos) if total_pos > 0 else np.nan

    # Benchmarks from Stage C (same window, same cost convention, vectorized engine).
    bench = pd.read_csv(config.DATA_PROCESSED / "phase1_table.csv", index_col=0)

    # Verdict per the registered decision rule.
    b, c = base21["net50"][1], chal21["net50"][1]
    challenger_wins = (c["sharpe"] > b["sharpe"]) and (chal_wins > len(folds) / 2)
    winner = "CHALLENGER (XS top-3)" if challenger_wins else "BASE CASE (gated TSMOM)"

    base_success = {
        "beats S2 net Sharpe": bool(b["sharpe"] > float(bench.loc["S2", "net50_sharpe"])),
        "beats S1 net Sharpe": bool(b["sharpe"] > float(bench.loc["S1", "net50_sharpe"])),
        "beats S2 Calmar": bool(b["calmar"] > float(bench.loc["S2", "net50_cagr"])
                                / abs(float(bench.loc["S2", "max_drawdown"]))),
        "shallower maxDD than S1": bool(b["max_drawdown"] > float(bench.loc["S1", "max_drawdown"])),
        "shallower maxDD than S2": bool(b["max_drawdown"] > float(bench.loc["S2", "max_drawdown"])),
        "sign stable L14 vs L21": bool(np.sign(base14["net50"][1]["sharpe"]) == np.sign(b["sharpe"])),
        "sign stable gate 100 vs 200": bool(
            np.sign(neighbors["NBR_GATE100"]["net50"][1]["sharpe"]) == np.sign(b["sharpe"])),
    }

    write_report(t0, close, base21, base14, chal21, neighbors, base_folds, chal_folds,
                 base_wins, chal_wins, dsr, k, top_share, contrib, bench, winner,
                 base_success, len(folds))
    make_figures(base21, chal21, t0)

    print(f"\nWinner by registered rule: {winner}")
    print(f"Base success criteria: {sum(base_success.values())}/{len(base_success)} passed")
    print(f"DSR (base, net50, K={k}): {dsr['dsr']:.3f} -> {dsr['verdict']}")
    print("Report: research/PHASE2_RESULTS.md")


def fmt_pct(x):
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt2(x):
    return f"{x:+.2f}" if pd.notna(x) else "n/a"


def write_report(t0, close, base21, base14, chal21, neighbors, base_folds, chal_folds,
                 base_wins, chal_wins, dsr, k, top_share, contrib, bench, winner,
                 base_success, n_folds):
    mondays = close.index[(close.index.weekday == 0) & (close.index >= t0)]
    L = ["# Phase 2 results: base case vs challenger (Stage D)", ""]
    L.append(f"Window: **{t0.date()} to {close.index[-1].date()}** ({len(mondays)} weekly "
             f"observations). Engine: drift-aware with 20% no-trade bands. Decisions on the "
             f"net-50bps column only (DEC-002).")
    L.append("")
    L.append(REGISTRATION)
    L.append("")
    L.append("## Head-to-head (decision runs)")
    L.append("")
    L.append("| run | cost | Sharpe | CAGR | vol | maxDD | Calmar | turnover/yr | TIM |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, runs in (("BASE_21", base21), ("BASE_14", base14), ("CHAL_21", chal21)):
        for label in ("gross", "net25", "net50"):
            m = runs[label][1]
            L.append(f"| {name} | {label} | {fmt2(m['sharpe'])} | {fmt_pct(m['cagr'])} | "
                     f"{m['ann_vol']:.1%} | {fmt_pct(m['max_drawdown'])} | {fmt2(m['calmar'])} | "
                     f"{m['annual_turnover']:.0%} | {m['time_in_market']:.0%} |")
    L.append("")
    L.append("Benchmarks on the same window (Stage C, vectorized engine): "
             f"S1 BTC net50 Sharpe {fmt2(float(bench.loc['S1', 'net50_sharpe']))}, "
             f"S2 equal-weight net50 Sharpe {fmt2(float(bench.loc['S2', 'net50_sharpe']))}.")
    L.append("")
    L.append("## Robustness neighbors (registered, excluded from selection, net50)")
    L.append("")
    L.append("| neighbor | Sharpe | CAGR | maxDD | turnover/yr |")
    L.append("|---|---:|---:|---:|---:|")
    for run_id, runs in neighbors.items():
        m = runs["net50"][1]
        L.append(f"| {run_id} | {fmt2(m['sharpe'])} | {fmt_pct(m['cagr'])} | "
                 f"{fmt_pct(m['max_drawdown'])} | {m['annual_turnover']:.0%} |")
    L.append("")
    L.append(f"## Walk-forward fold consistency ({n_folds} anchored 13-week folds, frozen params)")
    L.append("")
    L.append("No per-fold parameter selection was performed (defaults are pre-registered), so "
             "these folds measure consistency of the frozen configuration, not selection skill.")
    L.append("")
    L.append("| fold | test window | base return | base Sharpe | chal return | chal Sharpe |")
    L.append("|---|---|---:|---:|---:|---:|")
    for fold in base_folds.index:
        bf, cf = base_folds.loc[fold], chal_folds.loc[fold]
        L.append(f"| {fold} | {bf['test_start']} to {bf['test_end']} | {fmt_pct(bf['return'])} | "
                 f"{fmt2(bf['sharpe'])} | {fmt_pct(cf['return'])} | {fmt2(cf['sharpe'])} |")
    L.append("")
    L.append(f"Fold wins: base {base_wins}, challenger {chal_wins} "
             f"(of {n_folds}; remainder ties/both-flat). Base positive in "
             f"{int((base_folds['return'] > 0).sum())}/{n_folds} folds; challenger positive in "
             f"{int((chal_folds['return'] > 0).sum())}/{n_folds}.")
    L.append("")
    L.append("## Multiple-testing accounting")
    L.append("")
    L.append(f"- Trials ledger rows for family `phase2_base`: **K = {k}** (all cost levels and "
             f"neighbors count; docs/04 section 1.2).")
    L.append(f"- Deflated Sharpe of BASE_21 net50: **DSR = {dsr['dsr']:.3f}** -> **{dsr['verdict']}** "
             f"(n = {dsr['n_obs']} daily obs, skew {dsr['skew']:.2f}, kurtosis {dsr['kurtosis']:.1f}, "
             f"benchmark per-period SR {dsr['sr_benchmark_per_period']:.4f}).")
    L.append(f"- Single-name dependence: the top coin contributes {top_share:.0%} of positive gross "
             f"P&L (top 3: {', '.join(f'{i} {v:+.2f}' for i, v in contrib.head(3).items())}).")
    L.append("")
    L.append("## Verdict (registered rule applied)")
    L.append("")
    L.append(f"**Winner: {winner}.**")
    L.append("")
    L.append("Base-case success criteria (docs/05 section 2):")
    for name, ok in base_success.items():
        L.append(f"- {'PASS' if ok else 'FAIL'}: {name}")
    L.append("")
    L.append("<!-- verdict narrative appended by the run report -->")
    (config.REPO_ROOT / "research" / "PHASE2_RESULTS.md").write_text("\n".join(L) + "\n")


def make_figures(base21, chal21, t0):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})
    for name, runs, color in (("BASE_21 (gated TSMOM)", base21, "tab:blue"),
                              ("CHAL_21 (XS top-3)", chal21, "tab:orange")):
        eq = runs["net50"][0].equity
        axes[0].plot(eq.index, eq, label=f"{name} net50", color=color, linewidth=1.4)
        dd = eq / eq.cummax() - 1.0
        axes[1].plot(dd.index, dd, color=color, linewidth=1.1)
    axes[0].set_yscale("log")
    axes[0].set_title(f"Phase 2 head-to-head, net of 50 bps/side (start {t0.date()} = 1.0)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[1].set_title("Drawdown")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "phase2_head_to_head.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
