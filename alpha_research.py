"""
alpha_research.py  -  Handoff #8 WS-C/WS-D: the firm-sim alpha research run.

    python alpha_research.py analytics   # WS-C: build all 9 books on the playground,
                                         # per-alpha metrics, betas, correlations,
                                         # heatmap, pre-registered subset selection
    python alpha_research.py combine     # WS-D: combine the selected subset, folds,
                                         # deflated Sharpe (TOTAL ledger K), the ONE
                                         # vault look, finish the report

Everything is GROSS (dormant cost/funding hooks stay at zero) on the broad discovery
panel; tuning never sees the vault. Deliverable: research/ALPHA_RESEARCH_REPORT.md.

Pre-registered selection rule (written before results were computed):
  rank alphas by playground gross Sharpe, descending; accept an alpha iff
  (a) Sharpe >= 0.30 and (b) max |corr| with all already-accepted alphas < 0.50.
  At least two alphas must qualify for a combination to proceed.
"""

from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from xmom import alphas, config, engine, metrics, neutral, regimes, validation

SEL_MIN_SHARPE = 0.30
SEL_MAX_CORR = 0.50
BOOKS_DIR = config.DATA_PROCESSED / "mn_books"
STATE_PATH = config.DATA_PROCESSED / "mn_state.json"
RETURNS_PATH = config.DATA_PROCESSED / "mn_alpha_returns.parquet"
REPORT_PATH = config.REPO_ROOT / "research" / "ALPHA_RESEARCH_REPORT.md"


def load_panels(playground_only: bool = True):
    close = pd.read_parquet(config.DATA_PROCESSED / "discovery_close.parquet")
    members = pd.read_parquet(config.DATA_PROCESSED / "discovery_universe.parquet")
    if playground_only:
        idx = validation.playground_index(close.index)
        close, members = close.loc[idx], members.loc[idx]
    return close, members


def realized_beta(returns: pd.Series, market: pd.Series) -> float:
    joined = pd.concat([returns, market], axis=1, keys=["a", "m"]).dropna()
    var = joined["m"].var(ddof=1)
    return float(joined["a"].cov(joined["m"]) / var) if var > 0 else float("nan")


def build_all_books(close, members, t0):
    risk = neutral.precompute_risk(close)
    books = {}
    for name, spec in alphas.ALPHAS.items():
        signal = spec["fn"](close)
        books[name] = neutral.build_alpha_book(close, members, signal, t0, risk=risk)
        print(f"  built {name}")
    return books


def fmt_pct(x):
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt2(x):
    return f"{x:+.2f}" if pd.notna(x) else "n/a"


def analytics():
    close, members = load_panels(playground_only=True)
    t0 = engine.evaluation_window(close.index, config.WARMUP_DAYS)
    window = f"{t0.date()}..{close.index[-1].date()} (playground)"
    market_rets = close[config.MN_MARKET_ASSET].pct_change(fill_method=None)
    print(f"Playground window: {window}. Building {len(alphas.ALPHAS)} books...")

    books = build_all_books(close, members, t0)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    rows, returns, ledger_rows = {}, {}, []
    for name, weights in books.items():
        result = engine.run_ls_backtest(close, weights)
        r = result.net_returns.loc[t0:]
        m = metrics.summarize(r, result.turnover.loc[t0:], result.weights.loc[t0:])
        beta = realized_beta(r, market_rets.loc[t0:])
        gross_exp = result.weights.abs().sum(axis=1).loc[t0:]
        rows[name] = {**m, "beta_btc": beta, "avg_gross": float(gross_exp.mean())}
        returns[name] = r
        weights.to_parquet(BOOKS_DIR / f"{name}.parquet")
        ledger_rows.append({
            "run_id": f"MN_{name}_gross", "strategy_family": f"mn_{alphas.ALPHAS[name]['family']}",
            "parameters": {"alpha": name, "construction": "beta-neutral LS, 15% vol target",
                           "cost_per_side": 0.0, "panel": "discovery_playground"},
            "data_window": window, "gross_or_net": "gross",
            "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
            "annual_turnover": round(m["annual_turnover"], 4),
            "why_run": "Handoff 8 WS-C per-alpha analytics",
        })
        print(f"{name:<15} Sharpe {m['sharpe']:+.2f}  vol {m['ann_vol']:.1%}  "
              f"maxDD {m['max_drawdown']:+.1%}  turnover {m['annual_turnover']:.0%}  "
              f"beta {beta:+.3f}")

    validation.append_trials(ledger_rows)
    table = pd.DataFrame(rows).T
    ret_frame = pd.DataFrame(returns)
    ret_frame.to_parquet(RETURNS_PATH)
    corr = ret_frame.corr()

    # Pre-registered greedy selection.
    selection, decisions = [], []
    for name in table.sort_values("sharpe", ascending=False).index:
        sharpe = float(table.loc[name, "sharpe"])
        if sharpe < SEL_MIN_SHARPE:
            decisions.append(f"{name}: REJECTED (Sharpe {sharpe:+.2f} < {SEL_MIN_SHARPE})")
            continue
        rhos = [abs(float(corr.loc[name, s])) for s in selection]
        if rhos and max(rhos) >= SEL_MAX_CORR:
            worst = selection[int(np.argmax(rhos))]
            decisions.append(f"{name}: REJECTED (|corr| {max(rhos):.2f} with {worst} >= {SEL_MAX_CORR})")
            continue
        selection.append(name)
        decisions.append(f"{name}: SELECTED (Sharpe {sharpe:+.2f}, "
                         f"max |corr| to selected {max(rhos) if rhos else 0:.2f})")

    STATE_PATH.write_text(json.dumps({
        "window": window, "t0": str(t0.date()), "selection": selection,
        "decisions": decisions,
        "table": {k: {kk: (None if pd.isna(vv) else float(vv)) for kk, vv in v.items()
                      if kk not in ("start", "end")} for k, v in rows.items()},
    }, indent=2))

    make_heatmap(corr)
    make_alpha_equity_figure(returns, t0)
    write_report_analytics(table, corr, decisions, selection, returns, close, window)

    print(f"\nSelected subset ({len(selection)}): {', '.join(selection)}")
    print(f"Correlation heatmap + per-alpha figures in research/figures/.")
    print(f"Report (sections 1-4): {REPORT_PATH}")


def combine():
    state = json.loads(STATE_PATH.read_text())
    selection = state["selection"]
    if len(selection) < 2:
        print("Fewer than two alphas selected: no combination to run. Reported as-is.")
        return
    close, members = load_panels(playground_only=True)
    t0 = pd.Timestamp(state["t0"])
    market_rets = close[config.MN_MARKET_ASSET].pct_change(fill_method=None)

    books = {n: pd.read_parquet(BOOKS_DIR / f"{n}.parquet") for n in selection}
    combined_w = sum(books.values()) / len(books)  # sleeves are vol-targeted: ~equal risk
    result = engine.run_ls_backtest(close, combined_w)
    r = result.net_returns.loc[t0:]
    m = metrics.summarize(r, result.turnover.loc[t0:], result.weights.loc[t0:])
    beta = realized_beta(r, market_rets.loc[t0:])

    ret_frame = pd.read_parquet(RETURNS_PATH)
    standalone = {n: metrics.sharpe(ret_frame[n].dropna()) for n in selection}
    best_name = max(standalone, key=standalone.get)
    sleeve_turnovers = {n: metrics.annual_turnover(
        engine.run_ls_backtest(close, books[n]).turnover.loc[t0:]) for n in selection}

    # Walk-forward folds (consistency of the fixed, pre-registered construction).
    reb = engine.rebalance_days(close.index, start=t0)
    folds = validation.walk_forward_folds(reb, config.WF_INITIAL_TRAIN_WEEKS, config.WF_TEST_WEEKS)
    fold_rows = []
    for f in folds:
        fr = r.loc[f["test_start"]:f["test_end"] + pd.Timedelta(days=6)]
        fold_rows.append({"fold": f["fold"], "start": f["test_start"].date().isoformat(),
                          "end": f["test_end"].date().isoformat(),
                          "return": float((1 + fr).prod() - 1), "sharpe": metrics.sharpe(fr)})
    fold_frame = pd.DataFrame(fold_rows)

    # Deflated Sharpe with the TOTAL ledger trial count (per the handoff).
    ledger = pd.read_csv(validation.LEDGER_PATH)
    k_total = len(ledger)
    trial_sharpes = pd.to_numeric(ledger["sharpe"], errors="coerce").dropna().tolist()
    dsr = validation.deflated_sharpe(r, k_total, trial_sharpes)

    ledger_rows = [{
        "run_id": "MN_COMBINED_gross", "strategy_family": "mn_combined",
        "parameters": {"alphas": selection, "blend": "equal-weight of vol-targeted sleeves",
                       "cost_per_side": 0.0, "panel": "discovery_playground"},
        "data_window": state["window"], "gross_or_net": "gross",
        "sharpe": round(m["sharpe"], 4), "max_drawdown": round(m["max_drawdown"], 4),
        "annual_turnover": round(m["annual_turnover"], 4),
        "why_run": "Handoff 8 WS-D combined book",
    }]

    # THE one vault look: rebuild on the full panel, score the vault segment only.
    close_f, members_f = load_panels(playground_only=False)
    t0_f = engine.evaluation_window(close_f.index, config.WARMUP_DAYS)
    risk_f = neutral.precompute_risk(close_f)
    vault_books = []
    for name in selection:
        sig = alphas.ALPHAS[name]["fn"](close_f)
        vault_books.append(neutral.build_alpha_book(close_f, members_f, sig, t0_f, risk=risk_f))
    combined_full = sum(vault_books) / len(vault_books)
    result_full = engine.run_ls_backtest(close_f, combined_full)
    vr = result_full.net_returns.loc[validation.vault_index(result_full.net_returns.index)]
    vault = {
        "n_days": int(len(vr)), "total_return": metrics.total_return(vr),
        "sharpe": metrics.sharpe(vr), "max_drawdown": metrics.max_drawdown(vr),
        "beta": realized_beta(vr, close_f[config.MN_MARKET_ASSET].pct_change(fill_method=None)
                              .loc[vr.index]),
    }
    ledger_rows.append({
        "run_id": "MN_COMBINED_VAULT", "strategy_family": "mn_combined",
        "parameters": {"alphas": selection, "cost_per_side": 0.0, "panel": "discovery_vault"},
        "data_window": f"{config.OOS_VAULT_START}..{close_f.index[-1].date()} (VAULT)",
        "gross_or_net": "gross", "sharpe": round(vault["sharpe"], 4),
        "max_drawdown": round(vault["max_drawdown"], 4), "annual_turnover": np.nan,
        "why_run": "Handoff 8 WS-D VAULT single look (final exam)",
    })
    validation.append_trials(ledger_rows)

    make_combined_figures(r, ret_frame[best_name].dropna(), best_name, market_rets, t0)
    write_report_combined(m, beta, standalone, best_name, sleeve_turnovers, fold_frame,
                          dsr, k_total, vault, selection, r, close)

    print(f"Combined ({len(selection)} alphas): Sharpe {m['sharpe']:+.2f} vs best individual "
          f"{best_name} {standalone[best_name]:+.2f}")
    print(f"Combined beta to BTC: {beta:+.3f}; turnover {m['annual_turnover']:.0%} vs "
          f"mean sleeve {np.mean(list(sleeve_turnovers.values())):.0%}")
    print(f"DSR (K={k_total} total trials): {dsr['dsr']:.3f} -> {dsr['verdict']}")
    print(f"VAULT (one look, now spent): Sharpe {vault['sharpe']:+.2f}, "
          f"total {vault['total_return']:+.1%}, maxDD {vault['max_drawdown']:+.1%}, "
          f"beta {vault['beta']:+.3f}")
    print(f"Report complete: {REPORT_PATH}")


def make_heatmap(corr: pd.DataFrame):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(corr)), corr.index, fontsize=9)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(corr.iloc[i, j]) > 0.6 else "black")
    ax.set_title("Alpha daily-return correlations (gross, playground)")
    fig.colorbar(im, shrink=0.8)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "mn_correlation_heatmap.png", dpi=150)
    plt.close(fig)


def make_alpha_equity_figure(returns: dict, t0):
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for name, r in returns.items():
        ax.plot((1 + r).cumprod(), label=name, linewidth=1.1)
    ax.set_title(f"Market-neutral alpha sleeves, gross equity (start {t0.date()} = 1.0)")
    ax.legend(ncol=3, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "mn_alpha_equity.png", dpi=150)
    plt.close(fig)


def make_combined_figures(r_comb, r_best, best_name, market_rets, t0):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})
    for label, r, lw in ((f"combined book", r_comb, 2.0), (f"best single: {best_name}", r_best, 1.1)):
        eq = (1 + r).cumprod()
        axes[0].plot(eq, label=label, linewidth=lw)
        axes[1].plot(eq / eq.cummax() - 1.0, linewidth=lw)
    axes[0].set_title("Combined market-neutral book vs best single alpha (gross)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[1].set_title("Drawdown")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "mn_combined.png", dpi=150)
    plt.close(fig)

    joined = pd.concat([r_comb, market_rets.loc[r_comb.index]], axis=1, keys=["a", "m"]).dropna()
    roll_beta = joined["a"].rolling(90).cov(joined["m"]) / joined["m"].rolling(90).var()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(roll_beta, linewidth=1.2)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhspan(-0.1, 0.1, alpha=0.15, color="green")
    ax.set_title("Combined book: rolling 90d beta to BTC (green band = +/-0.1)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES / "mn_rolling_beta.png", dpi=150)
    plt.close(fig)


def write_report_analytics(table, corr, decisions, selection, returns, close, window):
    L = ["# Alpha Research Report: a stable of market-neutral crypto momentum alphas", ""]
    L.append(f"Firm-sim deliverable (docs/08_FIRM_SIM_CHARTER.md, Handoff #8). Panel: broad "
             f"Binance discovery dataset (survivorship-conscious, corporate-action seams severed; "
             f"see research/stage_a_data_report.md). Window: {window}; the OOS vault "
             f"({config.OOS_VAULT_START}+) is excluded from everything until the single final "
             f"evaluation in section 6. All results GROSS of costs and funding (dormant hooks in "
             f"the engine); a realism layer is future work and noted in the limitations.")
    L.append("")
    L.append("## 1. The stable")
    L.append("")
    L.append("Nine signals, one construction. Each raw signal is cross-sectionally z-scored "
             "(winsorized at 3), sized inverse-vol, hedged to ex-ante zero beta against BTC with "
             "a hedge leg (rolling 90d betas), and scaled to a 15% annualized vol target under "
             "gross (2.0) and per-name (10%) caps, weekly Monday rebalance. So the differences "
             "below are differences in INFORMATION, not construction.")
    L.append("")
    L.append("| alpha | family | idea |")
    L.append("|---|---|---|")
    for name, spec in alphas.ALPHAS.items():
        L.append(f"| {name} | {spec['family']} | {spec['description']} |")
    L.append("")
    L.append("*(A funding/term-structure momentum sleeve is future work: it requires perp "
             "funding-rate history we do not ingest yet.)*")
    L.append("")
    L.append("## 2. Standalone performance (gross, playground)")
    L.append("")
    L.append("| alpha | Sharpe | ann vol | maxDD | turnover/yr | avg gross | beta to BTC | hit |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, row in table.iterrows():
        L.append(f"| {name} | {fmt2(row['sharpe'])} | {row['ann_vol']:.1%} | "
                 f"{fmt_pct(row['max_drawdown'])} | {row['annual_turnover']:.0%} | "
                 f"{row['avg_gross']:.2f} | {row['beta_btc']:+.3f} | {row['hit_rate']:.1%} |")
    L.append("")
    L.append("![alpha equity](figures/mn_alpha_equity.png)")
    L.append("")
    L.append("### Regime slices (gross Sharpe by regime)")
    L.append("")
    trend = regimes.trend_regime(close)
    eras = regimes.era_labels(close.index)
    L.append("| alpha | bull | bear | " + " | ".join(n for n, _, _ in config.REGIME_ERAS[1:-1]) + " |")
    L.append("|---|" + "---:|" * (2 + len(config.REGIME_ERAS) - 2))
    for name, r in returns.items():
        cells = [name]
        for label in ("bull", "bear"):
            rr = r[trend.reindex(r.index) == label]
            cells.append(fmt2(metrics.sharpe(rr)) if len(rr) > 30 else "n/a")
        for era_name, _, _ in config.REGIME_ERAS[1:-1]:
            rr = r[eras.reindex(r.index) == era_name]
            cells.append(fmt2(metrics.sharpe(rr)) if len(rr) > 30 else "n/a")
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    L.append("## 3. Market-neutrality check")
    L.append("")
    worst = table["beta_btc"].abs().max()
    L.append(f"Realized full-window beta to BTC per sleeve is in the table above: largest "
             f"magnitude {worst:.3f}. The combined book's rolling beta is in section 5. "
             f"Construction is hedged ex ante; realized betas stay near zero ex post.")
    L.append("")
    L.append("## 4. Correlation structure and selection")
    L.append("")
    L.append("![correlation heatmap](figures/mn_correlation_heatmap.png)")
    L.append("")
    L.append(f"Pre-registered rule (in alpha_research.py before results): rank by Sharpe, accept "
             f"iff Sharpe >= {SEL_MIN_SHARPE} and max |corr| to already-accepted < {SEL_MAX_CORR}.")
    L.append("")
    for d in decisions:
        L.append(f"- {d}")
    L.append("")
    L.append(f"**Selected subset ({len(selection)}): {', '.join(selection) if selection else 'none'}.**")
    L.append("")
    REPORT_PATH.write_text("\n".join(L) + "\n")


def write_report_combined(m, beta, standalone, best_name, sleeve_turnovers, fold_frame,
                          dsr, k_total, vault, selection, r, close):
    best = standalone[best_name]
    L = ["## 5. The combined book (the diversification result)", ""]
    L.append(f"Equal-capital blend of the {len(selection)} selected sleeves (each sleeve is "
             f"vol-targeted at 15%, so equal capital is approximately equal risk). Weights are "
             f"netted BEFORE trading, so the combination also nets turnover.")
    L.append("")
    L.append("| series | Sharpe | ann vol | maxDD | Calmar | turnover/yr | beta to BTC |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    L.append(f"| **combined** | **{fmt2(m['sharpe'])}** | {m['ann_vol']:.1%} | "
             f"{fmt_pct(m['max_drawdown'])} | {fmt2(m['calmar'])} | {m['annual_turnover']:.0%} | "
             f"{beta:+.3f} |")
    for n in selection:
        L.append(f"| {n} (standalone) | {fmt2(standalone[n])} | | | | {sleeve_turnovers[n]:.0%} | |")
    L.append("")
    gain = m["sharpe"] - best
    if gain >= 0:
        L.append(f"**Diversification gain: combined Sharpe {fmt2(m['sharpe'])} vs best single "
                 f"sleeve ({best_name}) {fmt2(best)}, a gain of {gain:+.2f}.**")
    else:
        L.append(f"**The combination did NOT beat the best sleeve on Sharpe: {fmt2(m['sharpe'])} "
                 f"combined versus {fmt2(best)} for {best_name}.** Blending pays only when the "
                 f"weaker bets carry comparable Sharpe; here they did not, so the blend traded "
                 f"headline Sharpe for lower vol and drawdown. Reported as measured.")
    L.append(f"Combined turnover {m['annual_turnover']:.0%} vs mean sleeve turnover "
             f"{np.mean(list(sleeve_turnovers.values())):.0%} (netting).")
    L.append("")
    L.append("![combined](figures/mn_combined.png)")
    L.append("")
    L.append("![rolling beta](figures/mn_rolling_beta.png)")
    L.append("")
    L += regimes.regime_report_lines(r, close, "combined book (gross)")
    L.append("## 6. Validation")
    L.append("")
    L.append(f"**Walk-forward folds** (anchored, {config.WF_TEST_WEEKS}-week tests, fixed "
             f"pre-registered construction, no per-fold selection): positive in "
             f"{int((fold_frame['return'] > 0).sum())}/{len(fold_frame)} folds.")
    L.append("")
    L.append("| fold | window | return | Sharpe |")
    L.append("|---|---|---:|---:|")
    for _, row in fold_frame.iterrows():
        L.append(f"| {int(row['fold'])} | {row['start']} to {row['end']} | "
                 f"{fmt_pct(row['return'])} | {fmt2(row['sharpe'])} |")
    L.append("")
    L.append(f"**Deflated Sharpe:** DSR = {dsr['dsr']:.3f} with K = {k_total}, the TOTAL "
             f"trials-ledger count across the whole project (every backtest ever executed, per "
             f"docs/04). Verdict: {dsr['verdict']} (n = {dsr['n_obs']} daily obs, skew "
             f"{dsr['skew']:.2f}, kurtosis {dsr['kurtosis']:.1f}).")
    L.append("")
    L.append("**The vault (single look, now spent).** The combined book, rebuilt on the full "
             "panel with identical construction and equal weights (nothing fitted), scored once "
             f"on {config.OOS_VAULT_START} onward:")
    L.append("")
    L.append(f"- Sharpe {fmt2(vault['sharpe'])}, total return {fmt_pct(vault['total_return'])}, "
             f"maxDD {fmt_pct(vault['max_drawdown'])}, beta to BTC {vault['beta']:+.3f} "
             f"over {vault['n_days']} days (~{vault['n_days'] // 7} weekly observations, "
             f"Sharpe SE ~0.8: a disaster check, not a certification).")
    L.append("")
    L.append("## 7. Limitations (read before quoting any number above)")
    L.append("")
    L.append("- **Gross only.** No trading costs, no perp funding, no borrow constraints. At "
             "these turnover levels a realistic cost layer will take a large bite; that layer "
             "is the next workstream and nothing here is claimed net.")
    L.append("- **One market cycle.** The playground spans 2018-2024: one full bear, one mania, "
             "one recovery. Regime tables above show which sleeves depend on which regimes.")
    L.append("- **Multiple testing.** K in the DSR is the full ledger count, but trials are "
             "correlated variants, so the deflation is approximate in both directions.")
    L.append("- **Shorting is abstracted.** Perp availability, margin, and funding asymmetries "
             "are assumed away at the research layer by charter; capacity and borrow reality "
             "can only shrink these numbers.")
    L.append("- **Single-factor neutrality.** Books are hedged to BTC only; residual sector or "
             "size exposures may remain (a sector factor model is noted as future work).")
    existing = REPORT_PATH.read_text()
    marker = "## 5. The combined book"
    if marker in existing:
        existing = existing[: existing.index(marker)].rstrip() + "\n\n"
    REPORT_PATH.write_text(existing + "\n".join(L) + "\n")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "analytics"
    if mode == "analytics":
        analytics()
    elif mode == "combine":
        combine()
    else:
        raise SystemExit(f"unknown mode: {mode} (use 'analytics' or 'combine')")
