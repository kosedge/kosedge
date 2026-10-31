# EXEC_FREEZE t4915u — Lane S Analysis Plan (sealed before EXEC)

Amend-1 t4915u: add sealed W-L index diffs per proposal 44e3451f wording; still pre-EXEC.

Binds: OWNER_ACCEPT_t4915u (`/workspace/ops/nfl_enterprise_green_t4359u/OWNER_ACCEPT_t4915u_PHASE1_LANE_S.md`, sha256 dd4a2390a96568ab223fbc24031e4630d3f1607cccdc7bc38c0f5ec5481518c8) · proposal 44e3451f.
Verified pre-freeze: SCORE_RESULTS.json sha256 2b9f302e097183ef… (sha8 2b9f302e OK); SAMPLE_MANIFEST_70.json sha8 861a6264.

Binding note: this document freezes signal definitions, outcome orientation, comparisons and analysis plan under t4915u BEFORE any Lane S EXEC. Any deviation requires a new OWNER ACCEPT. One EXEC allowed.

```yaml
artifact: nfl-lane-s-discrimination-t4915u
label: DEV_RESEARCH / RETRO_FIT exploratory
cert: 0
nfl: NO-GO
sample: sealed 70 from SAMPLE_MANIFEST_70 (W2 14 + W3–W6 56); no expansion
control_tip: 02197f58   # packet tip; DO NOT CHANGE
score_results_sha8: 2b9f302e  # DO NOT CHANGE
if_tip: 6ca03716
w2_tip: 440314e4
w3w6_tip: f92aaea3
contract: b41f4b43
epa_success_label: RETRO_FIT / DEV_RESEARCH only (A1)

signals_frozen:  # definitions locked; no search over alternate transforms
  wl_home_wpct: "wins/(wins+losses) from record_asof_home; ties ignored in denom; if wins+losses==0 → MISSING"
  wl_away_wpct: "same for away"
  wl_diff: "wl_home_wpct - wl_away_wpct"  # home-positive
  wl_index_off_diff: "offense_index_home - offense_index_away (sealed RECON_MATRIX)"
  wl_index_def_diff: "defense_index_away - defense_index_home (home-favorable)"
  wl_index_net: "wl_index_off_diff + wl_index_def_diff"
  epa_off_diff: "home_off_epa_5g - away_off_epa_5g"  # from sealed RECON_MATRIX; A1 labeled
  epa_def_diff: "away_def_epa_allowed_5g - home_def_epa_allowed_5g"  # home-favorable = opponent allows more
  epa_net_diff: "epa_off_diff + epa_def_diff"
  success_off_diff: "home_success_offense_5g - away_success_offense_5g"
  success_def_diff: "away_success_defense_allowed_5g - home_success_defense_allowed_5g"
  success_net_diff: "success_off_diff + success_def_diff"
  matchup_diff_off_epa_5g: "as sealed in RECON_MATRIX (precomputed)"
  matchup_diff_success_rate_5g: "as sealed in RECON_MATRIX (precomputed)"
  # FORBIDDEN: inventing new composites, opponent-adjust, or weight search on this sample

outcomes_frozen:
  realized_margin: "home_score - away_score (from SCORE_RESULTS)"
  realized_su: "1 if realized_margin>0 else 0 if realized_margin<0 else TIE (exclude ties from SU rates; report n_ties)"
  orientation: home-positive throughout

comparisons_frozen:  # ALL must be reported; none may be dropped for being weak
  - spearman_rho(signal, realized_margin) + bootstrap 95% CI (B=2000, seed=4915)
  - pearson_r(signal, realized_margin) + bootstrap 95% CI
  - SU win rate when signal>0 vs signal<0 (exclude ==0); binomial 95% Wilson CI; n each side
  - decile or tertile mean realized_margin by signal (fixed tertiles by rank; no optimized cutoffs)
  - OLS realized_margin ~ signal (slope, intercept, SE, 95% CI); report if CI crosses 0
  - week-stratified: same Spearman + SU rate for weeks 2,3,4,5,6 separately; flag concentration if one week drives overall
  - leave-one-week-out: recompute Spearman on 70 minus each week; report range
  - vs control IF: Spearman(forecast_margin, realized_margin) already known; report Spearman(signal, forecast_margin) as association-to-IF only (not a retune)
  - MISSING handling: list games with any signal MISSING; do not impute; report n_complete per signal

analysis_plan_rules:
  - freeze this plan before EXEC; one EXEC allowed
  - no weight/cutoff/feature selection to maximize performance on these 70
  - no forecast regeneration; no engine ablation; no model math change
  - no 2024–25; no odds acquire; no publish/betting/CERT claims
  - RETRO_FIT / DEV_RESEARCH on every EPA/success claim
  - verdict vocabulary: USEFUL_DISCRIMINATION | FAILS_TO_SHOW | INCONCLUSIVE
  - recommend next bounded experiment after Alex RO (Lane E paper if signals useful; signal research if not; else inconclusive next)

inputs:
  score_results: /workspace copy of SCORE_RESULTS.json (sha8 2b9f302e) — outcomes + record_asof
  recon_w2: data/ops/nfl-hist-bt-stage1b-w2-t4893u/RECON_MATRIX.csv @ tip 440314e4
  recon_w3w6: data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/RECON_MATRIX.csv @ tip f92aaea3
  sample_manifest: SAMPLE_MANIFEST_70.json from score packet
  recon_matrices_box_copies: /workspace/ops/nfl_enterprise_green_t4359u/_lane_s_inputs/RECON_MATRIX_w2_440314e4.csv and RECON_MATRIX_w3w6_f92aaea3.csv (sha must match tips)

deliverables: [EXEC_FREEZE, SIGNAL_TABLE (70 rows), DISCRIMINATION_RESULTS.json/.md, WEEK_SUBSET_AUDIT.md, ASSUMPTIONS.md, CALL_AUDIT.md, VERDICT_ENG.md, SHA256SUMS]
review: Alex RO before interpretation delivery to OWNER
```
