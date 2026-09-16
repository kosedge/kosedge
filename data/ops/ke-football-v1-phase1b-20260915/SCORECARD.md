# KE Football v1 — Phase 1B component scorecard

**Status:** `MEASUREMENT_PHASE1B` · `production_promote=false`
**GO:** Ryan review of #570 Phase 1 → measurement validation and repair only.
**STOP:** Team Strength / composite weights, scoring, matchup, market, UI, boards, named KE Disruption.

Architecture preserved: RAW → DERIVED → ADJUSTED → MODELED. Week W never consumes post-W info.
Objectives are football-only (EPA, success, explosiveness, finishing, pace). Not ATS/ROI/CLV.

### NFL 2025 as_of 18

Team-games: 512. Bakeoff winner: `NO_ADJUSTMENT_WINNER`.

| ID | Grade | Phase 2 | Recommendation |
| --- | --- | --- | --- |
| ke.off_eff | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.def_eff | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.success_native | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.success_standard | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.success_allowed | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.pace | PARTIAL | yes | Publish plays/game. Competitive/clock variants stay labeled. |
| ke.pace_competitive | PARTIAL | yes | Publish plays/game. Competitive/clock variants stay labeled. |
| ke.pace_seconds | PARTIAL | yes | Publish plays/game. Competitive/clock variants stay labeled. |
| ke.expl | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.expl_pass | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.expl_rush | PARTIAL | yes | Measurement publishes; predictive persistence is weak. Do not overweight in a later composite. |
| ke.expl_allowed | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.off_pass_epa | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.off_rush_epa | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.off_early_epa | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.ppo | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.finish | PARTIAL | yes | Measurement publishes; predictive persistence is weak. Do not overweight in a later composite. |
| ke.opp_rate | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.rz_td | PARTIAL | yes | Keep as PARTIAL sibling. Do not substitute for drive finishing. |
| ke.st | PARTIAL | yes | Eligible as a DERIVED component only. Do not weight into Team Strength this phase. |
| ke.havoc | DATA_INSUFFICIENT | no | Keep OMIT. Do not invent KE Disruption weights. |
| ke.disruption_sack | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_interception | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_qb_hit | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_fumble | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_fumble_forced | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_tackle_for_loss | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_pass_breakup | DATA_INSUFFICIENT | no | Do not impute. |
| ke.disruption_proxy_nfl | PARTIAL | yes | Keep the proxy ID. Do not promote to named havoc. |
| ke.opp_adj_epa | PARTIAL | no | NO_ADJUSTMENT_WINNER. Do not promote an opponent adjustment because it is theoretically desirable. Phase 2 may keep the PIT SOS research cell as ADJUSTED-not-promoted. |

Counts: {"PASS": 6, "PARTIAL": 22, "FAIL": 0, "DATA_INSUFFICIENT": 2}

Finishing repair (owned nflverse):

- kickoff yl≤40 rate: 0.9939508506616257
- opportunity rate: 0.5207692307692308
- PPO repaired: 3.946085672082718
- finish repaired: 0.7477843426883308
- calibrated: False

### CFB 2025 as_of 13

Team-games: 1624. Bakeoff winner: `NO_ADJUSTMENT_WINNER`.

| ID | Grade | Phase 2 | Recommendation |
| --- | --- | --- | --- |
| ke.off_eff | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.def_eff | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.success_native | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.success_standard | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.success_allowed | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.pace | PARTIAL | yes | Publish plays/game. Competitive/clock variants stay labeled. |
| ke.pace_competitive | PARTIAL | yes | Publish plays/game. Competitive/clock variants stay labeled. |
| ke.pace_seconds | PASS | yes | Eligible for Phase 2 as a distinct pace component. Do not convert to points. |
| ke.expl | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.expl_pass | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.expl_rush | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.expl_allowed | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.off_pass_epa | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.off_rush_epa | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.off_early_epa | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.ppo | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.finish | PARTIAL | yes | Eligible with caveats (sample / early-season / collinearity). Validate again before weighting. |
| ke.opp_rate | PASS | yes | Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet. |
| ke.rz_td | PARTIAL | yes | Keep as PARTIAL sibling. Do not substitute for drive finishing. |
| ke.st | DATA_INSUFFICIENT | no | Do not manufacture. Leave OMIT / DATA_INSUFFICIENT. |
| ke.havoc | DATA_INSUFFICIENT | no | Keep OMIT. Do not invent KE Disruption weights. |
| ke.disruption_sack | PARTIAL | yes | Eligible as a per-event DERIVED rate only. Not named ke.havoc. |
| ke.disruption_interception | DATA_INSUFFICIENT | no | Leave DATA_INSUFFICIENT. Do not substitute fake rates or a havoc bundle. |
| ke.disruption_qb_hit | DATA_INSUFFICIENT | no | Do not impute. |
| ke.disruption_fumble | DATA_INSUFFICIENT | no | Do not impute. |
| ke.disruption_fumble_forced | DATA_INSUFFICIENT | no | Leave DATA_INSUFFICIENT. Do not substitute fake rates or a havoc bundle. |
| ke.disruption_tackle_for_loss | DATA_INSUFFICIENT | no | Leave DATA_INSUFFICIENT. Do not substitute fake rates or a havoc bundle. |
| ke.disruption_pass_breakup | DATA_INSUFFICIENT | no | Leave DATA_INSUFFICIENT. Do not substitute fake rates or a havoc bundle. |
| ke.opp_adj_epa | PARTIAL | no | NO_ADJUSTMENT_WINNER. Do not promote an opponent adjustment because it is theoretically desirable. Phase 2 may keep the PIT SOS research cell as ADJUSTED-not-promoted. |

Counts: {"PASS": 8, "PARTIAL": 13, "FAIL": 0, "DATA_INSUFFICIENT": 8}

## Phase 2 eligibility (measurement only)

Eligible IDs may enter a later Team Strength GO as independent measurements. This PR does not assign weights.

- NFL eligible: ke.off_eff, ke.def_eff, ke.success_native, ke.success_standard, ke.success_allowed, ke.pace, ke.pace_competitive, ke.pace_seconds, ke.expl, ke.expl_pass, ke.expl_rush, ke.expl_allowed, ke.off_pass_epa, ke.off_rush_epa, ke.off_early_epa, ke.ppo, ke.finish, ke.opp_rate, ke.rz_td, ke.st, ke.disruption_sack, ke.disruption_interception, ke.disruption_qb_hit, ke.disruption_fumble, ke.disruption_fumble_forced, ke.disruption_tackle_for_loss, ke.disruption_proxy_nfl
- NFL hold: ke.havoc, ke.disruption_pass_breakup, ke.opp_adj_epa
- CFB eligible: ke.off_eff, ke.def_eff, ke.success_native, ke.success_standard, ke.success_allowed, ke.pace, ke.pace_competitive, ke.pace_seconds, ke.expl, ke.expl_pass, ke.expl_rush, ke.expl_allowed, ke.off_pass_epa, ke.off_rush_epa, ke.off_early_epa, ke.ppo, ke.finish, ke.opp_rate, ke.rz_td, ke.disruption_sack
- CFB hold: ke.st, ke.havoc, ke.disruption_interception, ke.disruption_qb_hit, ke.disruption_fumble, ke.disruption_fumble_forced, ke.disruption_tackle_for_loss, ke.disruption_pass_breakup, ke.opp_adj_epa

Narrative: `docs/ratings/KE_FOOTBALL_V1_MEASUREMENT_PHASE1B_2026-09-15.md`.
