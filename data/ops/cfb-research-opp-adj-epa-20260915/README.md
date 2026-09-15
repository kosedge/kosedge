# CFB research opponent-adjusted O/D EPA (as_of 20260915)

Research-only. **Not KE Ratings.** Not KEI. Not a point spread.

| File | Role |
| --- | --- |
| `delayed_game_verification.json` | #559 delayed game close (`401868140`) |
| `delayed_game_pbp_audit.json` | PBP vs official 49–7 (partial Q2 28–0 cut → exclude) |
| `hist_inventory.json` | 2014–2025 restore checksums + Aug 13 reconcile |
| `validation_report.json` | rematerialized train / val / 2025 holdout (`fit_joint_v2`) |
| `closed_559_eligibility_summary.json` | regenerated #559 eligibility (84 games) |
| `cfb_2026_adj_epa.json` | frozen 2026 efficiency estimates (`λ=40 / n0=4`) |
| `frozen_method.json` | locked knobs + holdout call |
| `ryan_audit_560.json` | Ryan audit: seal, obs checksum, μ/h by season |
| `holdout_2025_obs_keys.tsv` | sorted holdout observation keys |
| `artifact_checksums.json` | SHA-256 of locked artifacts |
| `summary.json` | one-page rollup |

Recommendation: **advance** (research; `production_promote=false`). Frozen: `λ=40`, `n0=4`, `decay=0.75`. Pre-fix 0.1659 is not frozen.

See `docs/cfb/CFB_RESEARCH_OPP_ADJ_EPA_2026-09-15.md`.
