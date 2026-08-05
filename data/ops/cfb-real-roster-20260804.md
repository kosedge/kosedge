# CFB Real Roster Overlay (v0.6)

**Branch:** `feat/cfb-real-roster` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.6-real-roster`  
**Date:** 2026-08-04  
**Status:** Layers 1–3 rest on packaged ESPN 2026 roster / depth / portal-history snapshot. UI contracts unchanged; status + hub copy expose real sources.

## Confirmation — off weak/demo roster data

| Field | Value |
| --- | --- |
| `roster_source` | `packaged_espn_roster_2026` |
| `depth_source` | `espn_roster_production_depth` |
| `portal_source` | `espn_athlete_team_history` |
| `returning_source` | `espn_class_year_plus_qb_stats` |
| Coverage | 133 teams with roster + named QB; 126 with portal-in sample; 13k+ athletes; 5.8k depth rows |
| Preference | DB (optional/empty) → packaged ESPN snapshot → legacy curated priors |
| Not claimed | demo depth / weak placeholder roster when snapshot present |

```bash
python scripts/cfb/package_real_roster_2026.py
CFBD_API_KEY=... python scripts/cfb/package_real_roster_2026.py   # optional overlay
```

Artifacts:

- `services/model-service/src/services/cfb_season_engine/data/cfb_real_roster_snapshot_2026.json`
- merged into `cfb_fbs_team_priors_2026.json` (home_field + coaching retained)

## Before / after team examples

| Team | Before (v0.5.1 curated/illustrative) | After (ESPN 2026 snapshot) |
| --- | --- | --- |
| TEX | Arch Manning / incumbent (illustrative) | **Arch Manning** incumbent, 404 pass attempts in 2025; MJ Morris portal depth |
| UGA | Gunner Stockton / incumbent | **Ryan Puglisi** (Stockton gone from ESPN 2026 roster); roster_strength ~69 |
| FSU | Tommy Castellanos / portal | **Dean DeNobile** QB1 by 2025 attempts; Ashton Daniels portal depth |
| OSU | Julian Sayin / incumbent | **Julian Sayin** confirmed on Buckeyes roster (not Newark collision) |
| COLO | true_freshman / unnamed | **Kaidon Salter** / portal |
| BALL | placeholder unknown | **Keldric Luster** / open_competition; named roster |

Material moves: starter names/classes, `qb_situation_index`, `roster_strength`, unit grades. Recruiting capital retained from curated priors and blended into returning/portal levels so blue-blood hierarchy is not washed out by class-year proxies.

## Sources + freshness

| Signal | Source | Freshness / fidelity |
| --- | --- | --- |
| Roster identities | ESPN team roster API (2026 preseason) | Real identities; packaged as_of 2026-08-04 |
| Depth order | Heuristic: QB by 2025 pass attempts, else experience | Approximate — camp battles unresolved |
| Portal-in | ESPN athlete `teamHistory` (QBs + experienced sample) | Real when history present; sample not full roster |
| Portal-out | Incomplete proxy blended with recruiting baseline | Approximate / gap |
| Returning snap/start | Class-year proxy blended with recruiting-informed baseline | Approximate (not measured SNAP%) |
| Recruiting | Retained curated prior (optional CFBD `/recruiting/teams`) | Approximate unless CFBD overlay |
| HFA / coaching | Unchanged curated priors | Approximate |

## Known gaps

- Official ESPN depth charts empty early preseason → production/experience heuristic
- Full portal ledger / measured returning production need CFBD (`CFBD_API_KEY` supported)
- Schedule still densified sample (not official FBS slate)
- No Edge Board KEI — markets-only CFB board unchanged
- Unmatched prior codes: `FAY`, `SOUTH` (no ESPN abbrev bridge)

## Tests / smoke

```bash
cd services/model-service
pytest tests/test_cfb_real_roster.py tests/test_cfb_season_engine.py -q
curl -sS "$MODEL_SERVICE_URL/cfb/season-engine/status" \
  | jq '{engine_version,roster_source,depth_source,portal_source,as_of,roster_coverage}'
```

Web: `/pro/cfb/model` shows roster source line; project-game drivers expose real starter names/classes.
