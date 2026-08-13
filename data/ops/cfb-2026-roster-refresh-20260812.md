# CFB 2026 Roster Refresh (Source of Truth)

**Date:** 2026-08-12  
**Branch:** `feat/cfb-2026-roster-refresh` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.9-inseason` (unchanged)  
**Doctrine:** One packaged ESPN roster SoT. No display-vs-model dual maps. No headline overrides. PRESEASON/MODEL labels unchanged. No KEI.

## Source

| Field | Value |
| --- | --- |
| Primary | ESPN public 2026 team roster + athlete bio/overview (`scripts/cfb/package_real_roster_2026.py --skip-cfbd`) |
| `roster_source` | `packaged_espn_roster_2026` |
| `depth_source` | `espn_roster_production_depth` (heuristic: 2025 pass attempts, then experience) |
| `portal_source` | `espn_athlete_team_history` (QBs + experienced sample) |
| `returning_source` | `espn_class_year_plus_qb_stats` (class-year proxy, not measured SNAP%) |
| CFBD overlay | **skipped** (`CFBD_API_KEY` not used this pass) |
| Preference | DB (optional/empty) → this packaged snapshot → legacy curated priors |

Artifacts:

- `services/model-service/src/services/cfb_season_engine/data/cfb_real_roster_snapshot_2026.json`
- merged into `cfb_fbs_team_priors_2026.json` (HFA + coaching retained)

## Coverage

| | 2026-08-04 (before) | 2026-08-12 (after) |
| --- | --- | --- |
| `as_of` | 2026-08-04 | **2026-08-12** |
| Teams in snapshot | 134 | 134 |
| Teams with roster | 133 | **134** |
| Teams with named QB | 133 | **134** |
| Portal-in sample | 126 | 129 |
| Athletes | 13,116 | **13,353** |
| Depth rows | ~5.8k | **5,903** |
| Unmatched prior codes | `FAY`, `SOUTH` | `FAY`, `SOUTH` (unchanged) |

UF was the missing roster: ESPN abbreviation `UF` is Findlay (D2); Florida Gators are `FLA`. Packager now prefers the explicit alias `UF → FLA`. Florida Gators roster (100 athletes) is in the SoT.

## Sample project-game

Local engine smoke (packaged universe):

- `GET /cfb/season-engine/status` → `roster_source=packaged_espn_roster_2026`, `as_of=2026-08-12`, 134 named QBs
- TEX vs OSU week 1 project-game loads: Arch Manning incumbent, roster_strength 72.33
- UGA vs ALA week 1 project-game loads: pack QB1 Ryan Puglisi (see conflicts)
- Web: `/pro/cfb/model` + `/pro/cfb/project-game` remain PRESEASON + MODEL (no label rewrite this pass)
- Edge Board: markets-only; **no KEI invented**

## QB1 name moves vs 2026-08-04 pack (15)

Confirmed by public reporting (packager followed ESPN roster, not headlines):

| Team | Before | After | Notes |
| --- | --- | --- | --- |
| COLO | Kaidon Salter | **Julian Lewis** | Salter left (CFL); Lewis is the 2026 face of the room |
| BAY | Sawyer Robertson | **DJ Lagway** | Robertson NFL; Lagway is the public starter (class still `incumbent` — see classification flags) |
| TCU | Ken Seals | **Jaden Craig** | Craig is the projected 2026 starter |

Other name moves (Group / duplicate codes): FAU/FAU2 Drew Devillier, IDHO Sawyer Teeney, NW Aidan Chiles, OHIO Matt Vezza, OKST Drew Mestemaker, OREST/ORST Braden Atkinson, USM Landry Lyddy, WKU Rodney Tisdale Jr., WSU Caden Pinnick.

Unchanged smoke names: **TEX Arch Manning** incumbent (404 att); **OSU Julian Sayin** incumbent.

## High-profile QB / depth conflicts — human review

**Do not silently rewrite these from headlines.** Depth is still a 2025-attempts heuristic; ESPN 2026 rosters are incomplete for some stars.

| Team | Pack QB1 | Public consensus (Aug 12) | Why the pack differs |
| --- | --- | --- | --- |
| **UGA** | Ryan Puglisi (27 att) | Gunner Stockton is the unquestioned 2026 starter | Stockton is **absent** from ESPN's 2026 UGA roster. Pack will not invent him. |
| **MICH** | Brayden Fowler-Nicolosi (82 att) | Bryce Underwood is "clear No. 1" (Whittingham) | Underwood is **absent** from ESPN's 2026 Michigan roster. Fowler-Nicolosi is a CSU transfer on the ESPN list. |
| **FSU** | Dean DeNobile (347 att, Lafayette 2025) | Ashton Daniels named starter 2026-04-21 | Both on ESPN roster. Heuristic ranks FCS 2025 attempts over Daniels (119). |
| **LSU** | Landen Clark (277 att, Elon 2025) | Sam Leavitt is the public QB1 | Both on ESPN roster. Heuristic ranks Elon attempts over Leavitt (239). |
| **ALA** | Austin Mack incumbent (32 att) | Open camp battle Mack vs Keelon Russell; no starter named | Heuristic picks Mack on 2025 backup attempts. Do not name Russell. |
| **UF** | Tramell Jones Jr. `true_freshman` (35 att) | Open camp battle Jones vs Aaron Philo; no starter named | Jones edges Philo 35–28 attempts. Class should read closer to open; pack does not invent a named starter. |
| **NW** | Aidan Chiles `portal` | Favorite, but Braun has not named a Week 1 starter | Pack names Chiles from production; competition still open publicly. |
| **PSU** | Rocco Becht `incumbent` | Iowa State transfer; public starter | Name is right; **class is wrong** (ESPN teamHistory did not flag portal). |
| **BAY** | DJ Lagway `incumbent` | Florida transfer; public starter | Name is right; **class is wrong** (portal not flagged). |

## Honesty / non-goals

- Missing ESPN identities → pack uses who is on the roster, not press-conference starters
- Returning snap% remains a class-year proxy unless CFBD overlay is applied later
- Portal-out still incomplete
- No CFB KEI, no Edge Board edges, no PFF, no PBP EPA rebuild, no schedule densify rewrite

## Railway / Vercel

PR targets `deploy-vercel` (Vercel production). Model-service status `as_of` only moves after **Railway** deploys this snapshot. If Railway still tracks `restore-working-ui`, merge or cherry-pick this pack there before treating prod status as current.

```bash
cd services/model-service
pytest tests/test_cfb_real_roster.py tests/test_cfb_season_engine.py -q
curl -sS "$MODEL_SERVICE_URL/cfb/season-engine/status" \
  | jq '{engine_version,roster_source,as_of,roster_as_of,roster_coverage}'
```
