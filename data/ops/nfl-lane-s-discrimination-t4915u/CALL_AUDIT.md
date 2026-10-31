# CALL_AUDIT — t4915u Lane S EXEC

Engineering audit of what this run did and did not touch.

## Identity

| | |
|---|---|
| Ticket | t4915u Phase 1 Lane S ONLY |
| Artifact | `data/ops/nfl-lane-s-discrimination-t4915u/` |
| Role | Cursor eng DRAFT |
| Next | Alex RO (independent). Do not interpret to OWNER from this packet. |
| Label | DEV_RESEARCH / RETRO_FIT exploratory |
| CERT | 0 |
| NFL | NO-GO |

## One EXEC

Single run of `run_lane_s_exec.py` after hash verification. No second pass, no cutoff search, no re-fit.

## Hash gate (STOP conditions)

| File | sha8 / sha256 | Gate |
|---|---|---|
| `inputs/SCORE_RESULTS.json` | **2b9f302e** / `2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a` | STARTS WITH `2b9f302e` — OK |
| `inputs/SAMPLE_MANIFEST_70.json` | **861a6264** | match freeze — OK |
| `inputs/RECON_MATRIX_w2_440314e4.csv` | **708513db** | match CoS box `708513db…` — OK |
| `inputs/RECON_MATRIX_w3w6_f92aaea3.csv` | **cdff0115** | match CoS box `cdff0115…` — OK |
| `EXEC_FREEZE_t4915u_LANE_S_ANALYSIS_PLAN.md` | **29dc4005** / `29dc400571da4f7b…e3ac53fc` | Amend-1 — OK |
| `OWNER_ACCEPT_t4915u_PHASE1_LANE_S.md` | **dd4a2390** / `dd4a2390a96568ab…481518c8` | OK |

SCORE_RESULTS `n=70` unique ids equal manifest ids. Selection hash recomputed; matches manifest `6d4a1279…`.

## Repo tip cross-check

Freeze cites W2 tip `440314e4` and W3–W6 tip `f92aaea3`.
This checkout does **not** contain git objects `440314e43cba…` / `f92aaea385eb…` (packet dirs `data/ops/nfl-hist-bt-stage1b-w2-t4893u` and `…w3w6…` are absent on `deploy-vercel`).
Attached box copies were used. Their sha256 match the freeze/CoS expected prefixes. No reconstruction was re-run.

## Untouched (verified by construction)

| Item | Status |
|---|---|
| Control tip `02197f58` | Not rewritten. Cited only. |
| SCORE_RESULTS `2b9f302e` | Copied into `inputs/`; bytes unchanged. |
| IF tip `6ca03716` | Not invoked. `forecast_margin` read from SCORE_RESULTS only. |
| Forecast regeneration | **Not performed.** |
| Engine ablation / model math / weights / features | **Not performed.** Phase 2 Lane E stays paper-only. |
| New acquisitions / odds / C10 | **None.** |
| 2024–25 access | **None.** Sample is 2017 W2–W6 sealed 70 only. |
| Publish / betting / CERT claims | **None.** |
| Sample expansion | **None.** Four extra W3–W6 RECON bye-partials listed and excluded. |

## What the EXEC called

1. `sha256sum` on attached inputs + freeze docs.
2. Pivot long RECON (`field`,`reconstructed_value`) → wide game rows.
3. Inner-join to SCORE_RESULTS on `game_id` (70/70).
4. Frozen signal formulas (ASSUMPTIONS.md).
5. Frozen comparisons (Spearman+bootstrap, Pearson+bootstrap, SU Wilson, rank tertiles, OLS, week-stratified, leave-one-week-out, Spearman vs `forecast_margin`).
6. Write packet tables. No network. No model-service import. No simulator.

Bootstrap seed **4915**, B=**2000**, `RandomState` MT19937. Wilson \(z=\Phi^{-1}(0.975)\).

## Degenerate-but-reported comparisons

- `wl_home_wpct` and `wl_away_wpct` are in \([0,1]\). Sign split `signal<0` is empty (n−=0). Reported.
- `wl_diff == 0` on 28/70 (tied entering records). Those rows are excluded from the SU sign split only; they remain in Spearman/Pearson/OLS/tertiles.
- `matchup_diff_off_epa_5g` ranks identical to `epa_off_diff` on this sample.
- `matchup_diff_success_rate_5g` ranks identical to `success_net_diff` on this sample (sealed value ≈ net/2).

## Branch / PR

Packet-only branch off current `deploy-vercel`. Analysis is bound to IF tip `6ca03716` via SCORE_RESULTS, not by stacking the three unpublished IF-eval commits. DRAFT PR. Do not merge.
