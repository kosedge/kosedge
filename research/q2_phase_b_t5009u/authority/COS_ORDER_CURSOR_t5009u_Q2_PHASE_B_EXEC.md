# COS ORDER → Cursor — t5009u Q2 Phase B EXEC
Authority: OWNER t5009u CLEAR Q2PB (ACCEPT file COS_ACCEPT_OWNER_CLEAR_t5009u_Q2_PHASE_B_v1.md). Label: DEV_RESEARCH. CERT=0. Budget ≤12 d ASSUMPTION.

## Scope
1. Build opponent-adjusted as-of strength: margin_ij = h + s_i − s_j, ridge/solve on games.csv tip 4fe1cdd7, kickoff-before-target rule tip cf514078.
2. Fit ALL hyperparameters and comparators on DEV 2013–16 REG W2–17 ONLY: λ, regression fraction, WL_MARGIN (a,b), WL_WP (c_WL,d_WL), Q2 maps (c,d). Measure DEV ICC on residuals; record n_fit; ties excluded.
3. wl_diff = home as-of win% − away as-of win%, recomputed as-of from games.csv 4fe1cdd7 (verify column name at freeze; mapping not definition).
4. PBP 6ee24b44 EPA secondary only; mapping b41f4b43 UNVERIFIED. If ONLY EPA carries signal → STOP (rename/S1 guard, kill 50f57195).
5. HARD STOP: seal FROZEN_CONFIG (fit object sha256 + config sha + America/New_York timestamp) BEFORE reading any EVAL 2018–22 row.
6. DEV early stop: DEV Spearman ρ(home_s−away_s, m) < +0.10 OR DEV MAE(pm_new,m) ≥ WL_MARGIN MAE → STOP, seal report, NO EVAL.
7. If DEV passes: exactly one EVAL look k:0→1 on 2018–22 REG W2–17; keep/stop EXACTLY per Q2_EVAL_SPEC_CLARIFY tip 349e081e §6 (ρ≥+0.15 AND cluster CI lower>0; paired ΔMAE vs WL_MARGIN CI excludes 0 as improvement; kill if Pearson corr(pm_new−pm_WL, m−pm_WL)>0; no post-EVAL tuning). Bootstrap team-season B=10000, seed 4918.
8. Reuse pinned_assets_t4918u/ only for games.csv 4fe1cdd7. NOTE (CoS filing check): pinned_assets_t4918u/historical_oos_games.csv hashes to 1ee90fac = the gated index — do NOT consume it for scored use (gate 83646d78). Locate games.csv 4fe1cdd7 and verify its sha256 before use; if absent, STOP and report (no new data acquisition). Market lines: descriptive reference only.
9. Outputs sealed 0444 + .sha256 under /workspace/ops/nfl_enterprise_green_t4359u/: FROZEN_CONFIG_Q2PB_t5009u.md (+ fit artifact hashes), DEV_EARLY_STOP or EVAL_ONELOOK results, engineering hours, component list. Labels DEV_RESEARCH / RETRO_FIT as applicable.

## Prohibited
2017/2023/2024–25 in fits or EVAL beyond reserved; scored reuse of 1ee90fac; trailing_*; S1/EPA-trail revive; math/eval rule changes; merge/deploy/pub/bet; prod writes; new data acquisition; Stage C EXEC.

## Stop
After FROZEN_CONFIG (and EVAL if opened): stop for Alex RO → CoS. Do not self-ACCEPT keep.
