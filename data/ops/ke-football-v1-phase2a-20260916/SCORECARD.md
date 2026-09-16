# KE Football v1 — Phase 2A unit rating scorecard

**Status:** `UNIT_RATINGS_PHASE2A` · `production_promote=false`
**STOP:** Team Strength, overall weights, matchup, scoring, market, ATS, UI, boards.

`NO_ADJUSTMENT_WINNER` accepted. Opponent adjustment was not reopened.
Complexity must beat trailing EPA. If it does not, the unit rating is shrunken/raw EPA.

### NFL 2025 as_of 18

Off winner: `epa_shrunken` · Def winner: `epa_shrunken`

**off unit** — PARTIAL · No composite earned inclusion over the strongest constituent. Publish epa_shrunken as the honest v1 unit rating (shrunken/raw EPA). Do not invent weights.

| Method | Conf MAE | Conf r | n | Beats EPA? |
| --- | --- | --- | --- | --- |
| epa_raw | 0.164 | 0.296 | 214 | False |
| epa_shrunken | 0.163 | 0.292 | 214 | False |
| z_pass | 0.164 | 0.298 | 214 | False |
| z_earned | 0.164 | 0.298 | 214 | False |
| pca_earned | 0.193 | 0.303 | 214 | False |
| ridge_earned | 0.163 | 0.313 | 214 | False |

Earned PARTIAL features: []
Finishing earned: {'ke.ppo': False, 'ke.finish': False}
shrink k: 160.0

**def unit** — PARTIAL · No composite earned inclusion over the strongest constituent. Publish epa_shrunken as the honest v1 unit rating (shrunken/raw EPA). Do not invent weights.

| Method | Conf MAE | Conf r | n | Beats EPA? |
| --- | --- | --- | --- | --- |
| epa_raw | 0.165 | 0.282 | 214 | False |
| epa_shrunken | 0.164 | 0.282 | 214 | False |
| z_pass | 0.167 | 0.258 | 214 | False |
| z_earned | 0.170 | 0.230 | 214 | False |
| pca_earned | 0.180 | 0.239 | 214 | False |
| ridge_earned | 0.170 | 0.159 | 214 | False |

Earned PARTIAL features: ['ke.expl_allowed', 'ke.disruption_proxy_nfl']
Finishing earned: {}
shrink k: 160.0

### CFB 2025 as_of 13

Off winner: `epa_shrunken` · Def winner: `epa_shrunken`

**off unit** — PARTIAL · No composite earned inclusion over the strongest constituent. Publish epa_shrunken as the honest v1 unit rating (shrunken/raw EPA). Do not invent weights.

| Method | Conf MAE | Conf r | n | Beats EPA? |
| --- | --- | --- | --- | --- |
| epa_raw | 0.172 | 0.339 | 446 | False |
| epa_shrunken | 0.169 | 0.341 | 446 | False |
| z_pass | 0.173 | 0.319 | 446 | False |
| z_earned | 0.173 | 0.319 | 446 | False |
| pca_earned | 0.285 | 0.320 | 446 | False |
| ridge_earned | 0.173 | 0.318 | 446 | False |

Earned PARTIAL features: []
Finishing earned: {'ke.ppo': False, 'ke.finish': False}
shrink k: 160.0

**def unit** — PARTIAL · No composite earned inclusion over the strongest constituent. Publish epa_shrunken as the honest v1 unit rating (shrunken/raw EPA). Do not invent weights.

| Method | Conf MAE | Conf r | n | Beats EPA? |
| --- | --- | --- | --- | --- |
| epa_raw | 0.176 | 0.286 | 446 | False |
| epa_shrunken | 0.172 | 0.322 | 446 | False |
| z_pass | 0.176 | 0.286 | 446 | False |
| z_earned | 0.175 | 0.292 | 446 | False |
| pca_earned | 0.185 | 0.292 | 446 | False |
| ridge_earned | 0.173 | 0.293 | 446 | False |

Earned PARTIAL features: ['ke.success_allowed']
Finishing earned: {}
shrink k: 160.0

Narrative: `docs/ratings/KE_FOOTBALL_V1_UNIT_RATINGS_PHASE2A_2026-09-16.md`.
