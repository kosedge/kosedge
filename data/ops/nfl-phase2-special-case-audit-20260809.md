# NFL Phase 2 — Special-Case Audit (2026-08-09)

Engine: `nfl-season-engine-v1.25-phase2-features`  
Snapshot: `nfl-depth-2026-w1-20260809T190000Z` (Phase 1 gate **PASS**)  
Branch: `feat/nfl-phase2-features-20260809` → `deploy-vercel`

## Summary counts

| Disposition | Count |
|-------------|------:|
| **Convert** | 11 |
| **Remove** | 6 |
| **Keep** (policy / general / SoT) | 8 |

## Audit table

| Lever | Where | Why it exists | General feature candidate? | Keep / convert / remove |
|-------|-------|---------------|----------------------------|-------------------------|
| ARI/BAL/SEA `TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS` (residual, scheme_mult, soft floor/ceiling) | `season_budgets.py`, `team_volume_budgets.py` | v1.17 board landing zones after looking at 2026 pass volumes | Yes — QB rush profile + coaching + low-cont high-tail + league soft taper + returning-QB prior | **Convert** → removed named map |
| SEA Darnold 70/30 pass anchor | `season_budgets.py` | Hold SEA near 2024–25 Darnold volume under new OC | Yes — `QB_PASS_YARDS_PRIOR_BY_PLAYER_ID` + returning-QB travel | **Convert** (player_id prior; revisit 2026-10-01) |
| `SCHEME_TD_MULT` ARI/BAL/SEA | `offensive_production_stack.py` | LaFleur/Doyle/Fleury TD nudges | Yes — coaching `rz_pass_bias` → scheme TD mult | **Convert** |
| BAL/ARI/SEA rush TD `gl` hardcodes | `offensive_production_stack.py` | Dual-threat / GL lean after board review | Yes — `qb_rush_td_gl_mult` from QB profile | **Convert** |
| BAL/ARI run_rate nudges in rush pool | `offensive_production_stack.py` | Scheme lean duplicate of coaching | Yes — coaching pass bias + `qb_script_run_tilt` | **Convert** / **Remove** team ifs |
| `RB_OL_PROXY_BUMP` named teams | `offensive_production_stack.py` | Pretty RB floors for “good OL” clubs | Yes — `ol_protection.rb_ypc_bump_yards` | **Convert** (dict emptied) |
| `LOCKED_PASS_SCHEME_TEAMS` ARI/BAL/SEA | `offensive_production_stack.py` | Freeze three teams in variance lift | No longer needed — pass yards locked for all 32 from budgets | **Remove** |
| OL→EPA stub (`documented_not_magical`) | depth pack / `data_integrity` deferred | Track WAS Tunsil/Allegretti without inventing EPA | Yes — `ol_protection_v1` transparent index | **Convert** |
| Continuity score as label-only | `continuity_score.py` / drivers stubs | Prior-travel exists but volume path ignored it | Yes — wire travel + new-regime into volume features | **Convert** (strengthened) |
| Coaching tendencies missing ARI/SEA/WAS | `coaching_tendencies.py` | Only partial curated book | Yes — add LaFleur / new-OC SEA / Quinn WAS profiles | **Convert** |
| Depth role → usage via name hygiene | loaders / `CANONICAL_SKILL_TEAM` | Mike Evans team label fix | SoT depth_order/role already; Evans map is identity hygiene | **Keep** (SoT hygiene; not a volume lever) |
| Sticky alpha `PRIOR_YEAR_ALPHA_VOLUME` by name | `offensive_production_stack.py` | Protect proven WR/RB alphas | Prior-year volume feature (stats-keyed); not team sculpture | **Keep** (general prior; revisit 2026-10-01) |
| League rush soft floor/ceiling + tanh taper | `offensive_production_stack.py` | Clear rush piles without hard clips | Already general (all teams) | **Keep** |
| High-volume pass TD floor | `offensive_production_stack.py` | Enterprise soft-flag: volume↔TD coherence | General efficiency floor | **Keep** |
| Soft RB alpha prior band | `offensive_production_stack.py` | Prevent RB1 collapse / single-yard piles | General prior + rank span | **Keep** |
| PF/PA/win tapered stretch | defensive stack / v1.24 ops | Clear win/PF piles post-board | General league taper | **Keep** |
| Usage other-bucket floor 8% | `calibration.py` | Conservation / sparse roster | General conservation | **Keep** |
| Curated staff continuity flags | `continuity_score.CURATED_STAFF_BY_SEASON` | 2026 HC carousel | Explicit, time-limited staff book | **Keep** (revisit 2026-10-01) |
| QB rush tier map by player_id | `qb_rushing_profile.py` | Dual-threat volume without team names | General player trait | **Keep** (revisit 2026-10-01) |
| Post-hoc “pretty board” win/PF micro-spreads beyond taper | v1.24 rebuild notes | Aesthetic ranking spreads | Prefer residual micro-spread already general; no new team piles | **Remove** new ones; existing taper **Keep** |

## Retained overrides (policy)

| Override | Type | Justification (decision-time) | Reproducible path | Revisit / expiry |
|----------|------|-------------------------------|-------------------|------------------|
| `QB_RUSH_TIER_BY_PLAYER_ID` | player trait prior | Recent dual-threat rush-share bands; keyed by SoT GSIS | `qb_rushing_profile.py` | **2026-10-01** |
| `QB_PASS_YARDS_PRIOR_BY_PLAYER_ID` (Darnold) | player prior yards | 2024–25 high-efficiency volume; not a SEA hardcode | `season_budgets.py` | **2026-10-01** |
| `CURATED_STAFF_BY_SEASON[2026]` | staff continuity | Known HC/OC carousel at pack time | `continuity_score.py` | **2026-10-01** |
| Coaching `_CURATED` profiles | scheme prior | Distinctive play-mix; modest clamps | `coaching_tendencies.py` | ongoing; no team soft yards |
| `PRIOR_YEAR_ALPHA_VOLUME` | prior-year stats | Sticky usage from observed 2025 volume | `offensive_production_stack.py` | **2026-10-01** |
| `CANONICAL_SKILL_TEAM` (Mike Evans→TB) | identity hygiene | Packaged depth team label fix | production stack desk map | until SoT row corrected |
| League pass soft taper 2900–4400 | league rail | Replaces named soft floors/ceilings | `season_budgets._taper_pass_yards` | recalibrate with Week-5 |

Undocumented named-team / post-hoc clamps after this pass = **bugs**.
