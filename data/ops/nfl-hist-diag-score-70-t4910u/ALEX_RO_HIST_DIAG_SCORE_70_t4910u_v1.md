# ALEX RO — Hist bounded diagnostic score 70 (t4910u) — v1

**VERDICT: CONDITIONAL** · eng tip **19c6a460** (19c6a460752f23d73e7d340572c35adab9ea1996) · PR #672 DRAFT · eng self-label CONDITIONAL_DIAG
NFL NO-GO · CERT=0 · RO only (no re-score, no fit, no Odds, 0 credits)

## Integrity
- SHA256SUMS: 16/16 OK on box packet. git archive of tip packet dir is byte-identical to box mirror (diff -r clean).
- PR scope (19c6a460~1..19c6a460): 19 files, +6966/-0; all under data/ops/nfl-hist-diag-score-70-t4910u/ plus two recreated docs data/ops/EXEC_FREEZE_t4910u_*.md, data/ops/OWNER_ACCEPT_t4910u_*.md. No framework/simulator/contract change.
- Rehash @6ca03716: nfl_simulator.py 52d9e909 MATCH · nfl_handicapping_framework.py a0051cc4 MATCH · contract ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md b41f4b43 MATCH (git ref + box copy).
- Input matrices: W2 RECON_MATRIX 708513db, W3–W6 RECON_MATRIX cdff0115 — match PINS and my prior RO fetches.
- PINS: blend=0, N=4000, seed formula bound, tie→away, rest BIND_PACKET_ONLY, IF tip 6ca03716 (not 90bf65ab).

## Sample 70 + exclusions
- 70 rows = exactly the set of fully DERIVED_PREGAME games across W2 (74 total games in both matrices) — W2 14 · W3 16 · W4 16 · W5 14 · W6 10.
- 4 non-complete (DET_NO, MIA_ATL, SF_WAS, NYG_DEN: 16 DERIVED + 11 MISSING_RECORD each) excluded, listed in SAMPLE_MANIFEST_70 (B0). W2 CHI_TB / MIA_LAC listed W2_INELIGIBLE. No substitutes, no fills.
- 70/70 SCORED, 0 failed, all market_blend=0, simulations=4000.
- Seeds: all 70 recomputed from `201710 + int(sha256(gid)[:12],16) % 1000003` — 0 mismatches.

## Rest bind
- score_t4910u.py: rest from RECON_MATRIX packet values; explicit guard bans import of rest_days_from_schedule / verify_rest_days; runtime assert inputs.rest == packet rest; no games.csv rest; no network imports (no requests/urllib).
- All 70 rows: rest_days_home/away == matrix reconstructed_value (0 mismatches). Thu games keep 4.0 (HOU_CIN, LA_SF, CHI_GB, NE_TB, PHI_CAR).

## Metrics (recompute from SCORE_RESULTS.json vs eng)
| metric | Alex | eng |
|---|---|---|
| straight-up acc IF (70 decided, 0 ties) | 0.4714 | 0.4714 |
| SU naive W-L / pick'em(home) | 0.5000 / 0.5000 | 0.5000 / 0.5000 |
| MAE margin / total | 10.745 / 11.963 | 10.745 / 11.963 |
| RMSE margin / total | 14.171 / 14.645 | 14.171 / 14.645 |
| MAE pick'em margin / const-45.3 total | 10.486 / 11.820 | same |
| Brier IF / naive | 0.2584 / 0.3048 | same |
| log-loss IF | 0.7107 | 0.7107 |
| sd forecast means / sd realized (sample sd) | 2.976 / 13.662 | same (pop sd 2.955/13.564) |
| coverage p10–p90 margin / total | 0.800 / 0.743 | same |
- realized_su and if_su_pick consistent with scores/forecast_margin and wp on all 70.
- Naming: "straight-up outcome accuracy, NOT ATS-vs-0"; no ATS/CLV/market-beat claim; baselines labeled ≠edge. Compression caveat honest (sd_means ≪ realized; σ≈10.0 is noise term). IF fails to beat baselines on SU/MAE — diagnostic finding, not defect.

## Remount residual (EXEC_FREEZE / OWNER_ACCEPT)
- **Box originals ARE present** at ops/nfl_enterprise_green_t4359u/: EXEC_FREEZE 5ecdef1c…, OWNER_ACCEPT 1102720e… (both match their .sha256). Eng recreations 8ef7a834 / d3acd43d differ in wording/format. Eng claim "Box originals not present" is factually wrong for this box (soft: eng box ≠ this box).
- Diff of content: core params faithful — tip 6ca03716, blend 0, contract/as-of/PBP pins, lineage, N=4000, seed (utf-8 encode ≡ encode()), tie→away, rest BIND_PACKET_ONLY, sample rule/expected 70, no replacement, A1 label, benchmarks, bans. Nothing invented/changed → not RETURN.
- Gap vs ORIGINAL freeze metric list (not carried into recreation): WP calibration bins (exploratory), dispersion envelope, realized-on-forecast slope, 50/80/90% interval coverage — packet only has p10–p90 coverage + sd ratio. Soft omission; computable from sealed JSON post hoc without re-score.

## A1 EPA banner
- Every row epa_success_label "RETRO_FIT / DEV_RESEARCH only (A1)"; ASSUMPTIONS §A1 states same; no clean hist-validation claim.

## CALL_AUDIT
- 0 Odds credits; no Odds/Railway/DB; PBP 84eacd96 cited not opened; 2017 market columns unread; 2024–25 untouched.

## Soft notes vs hard defects
- Hard defects: **none**.
- Soft (keep CONDITIONAL): (1) freeze/accept sha remount unmatched in PR (originals exist on box at expected sha; recreations faithful on params); (2) four freeze-listed metrics missing (calibration bins, envelope, slope, 50/90 coverage); (3) EPA DEV_RESEARCH-only; N=70 exploratory; (4) no re-invoke spot-check by Alex (seeds + draw_replay err ≤0.001 in packet accepted).
- To lift to PASS_DIAG_SCORE: replace recreated docs with box originals (5ecdef1c/1102720e) or CoS accepts residual; add the 4 metrics from sealed SCORE_RESULTS (no re-run).

## CoS receipt
Alex RO t4910u · CONDITIONAL · tip 19c6a460 · metrics recompute exact · rest bound 70/70 · seeds 70/70 · no math change · remount: originals on box, recreations param-faithful.

≠fit ≠CERT ≠CLV · NFL NO-GO · CERT=0
