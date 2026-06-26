# Handoffs to Claude Code

This file is the durable record of work handed from the architect/planner (Claude, in Cowork) to the execution agent (Claude Code), which writes/runs code and owns the GitHub repo.

**Convention.** Each handoff has: an ID and date, a goal, the context Claude Code needs, a numbered task list, explicit acceptance criteria, and a "report back" section. Claude Code should append a short result note under each handoff when done, and add a dated entry to `PROGRESS_LOG.md`.

**Repo:** public from day one. **Auth:** GitHub already configured. **Golden rule:** no secret ever enters git. Keys live only in `.env` (gitignored). Verify before every push.

---

## Handoff #1  -  2026-06-26  -  Initialize public repo + verify Phase 0 environment

### Goal
Turn the existing `crypto-momentum/` scaffolding into a public GitHub repo, prove the Phase 0 environment works by running the live-price script, and commit the result. Do NOT write new strategy code yet.

### Context
- Working dir: `/Users/glennso/Documents/Claude/Projects/Quant Projects/crypto-momentum`
- The folder may already contain a local `.git` (init'd during scoping). Reuse it or re-init as needed.
- Scaffolding already present: `README.md`, `requirements.txt`, `.gitignore`, `.env.example`, `phase0_hello.py`, and `docs/` (charter, roadmap, resources, setup, this file), plus a `PROGRESS_LOG.md`.
- Target exchange: Kraken. The script uses public data only (no keys required).

### Tasks
1. **Secret-hygiene check FIRST (blocking).** Confirm `.gitignore` excludes `.env`, `.env.*`, `data/raw/*`, `data/processed/*`, and `logs/*`. Run `git status` and confirm no `.env` or key material is staged or tracked. If any secret is tracked, stop and fix before continuing. The repo is public.
2. **Python environment.** Create `.venv`, activate it, `pip install -r requirements.txt`. Report the installed `ccxt` version.
3. **Run the Phase 0 script.** Execute `python phase0_hello.py`. Capture the full output. Save a copy to `logs/phase0_output.txt` (gitignored, fine). If Kraken returns a network/geolocation error, note it and report back; do not silently switch exchanges.
4. **Create the public GitHub repo.** Name suggestion: `crypto-momentum-xmom` (user may override). Set a one-line description: "Systematic crypto cross-sectional momentum: a rigorously documented personal quant project." Add remote, push `main`.
5. **Optional but recommended.** Add an MIT `LICENSE` and a short repo description/topics (quant, crypto, momentum, algorithmic-trading). Ask the user before adding a license if unsure.
6. **Commit + log.** Make a clean initial commit ("Phase 0: project scaffolding, charter, roadmap, hello-world data script"). Append a dated entry to `PROGRESS_LOG.md` summarizing what was set up and pasting the key Phase 0 output numbers (spreads + fees).

### Acceptance criteria
- Public GitHub repo exists and contains the scaffolding, with NO `.env` or secrets in history.
- `phase0_hello.py` ran and produced a live bid/ask/spread/fee table (or a clearly-reported venue error).
- `PROGRESS_LOG.md` has a new dated Phase 0 entry.

### Report back (paste to the architect / into Cowork)
- The live output table from `phase0_hello.py` (the actual bid/ask/spread/volume numbers and Kraken's maker/taker fees).
- The public repo URL.
- Any errors hit and how they were resolved.

These numbers matter: the architect will use your real spreads and fees to set the transaction-cost assumptions for the Phase 3 backtest.

<!-- Claude Code: append your result note here -->

### Result note (Claude Code, 2026-06-26)
**Status: DONE.** All acceptance criteria met.
- **Secret hygiene:** `.gitignore` excludes `.env`, `.env.*`, `data/raw/*`, `data/processed/*`, `logs/*` (verified with `git check-ignore`). No `.env` on disk, no key material staged or tracked. Repo is safe to be public.
- **Environment:** `.venv` created; `pip install -r requirements.txt` succeeded on Python 3.14.5. **ccxt version: 4.5.60.**
- **Phase 0 run:** `phase0_hello.py` connected to Kraken (1,506 markets), printed a live bid/ask/spread/volume table and the fee schedule. **No venue/geo error** (Kraken responded; no fallback needed). Full output saved to `logs/phase0_output.txt`. Live fees: **maker 0.25% / taker 0.40%** (taker round-trip ~0.80% pre-spread/slippage). Snapshot pasted into `PROGRESS_LOG.md`.
- **Repo:** public GitHub repo `crypto-momentum-xmom` created, `main` pushed. Topics: quant, crypto, momentum, algorithmic-trading. **No license** (per user decision).
- **Commit:** clean initial commit `Phase 0: project scaffolding, charter, roadmap, hello-world data script`.
