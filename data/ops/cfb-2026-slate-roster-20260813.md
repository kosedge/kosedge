# CFB Official 2026 Slate + Roster Completeness

**Date:** 2026-08-13  
**Branch:** `feat/cfb-2026-slate-roster-complete` → `deploy-vercel` (stacked on #233 / #234 / #235)  
**Engine:** `cfb-season-engine-v0.12-slate-roster`  
**Doctrine:** Research only. `used_in_spread` stays **false**. No KEI. Densified seed is **not** official. No invented CFP%.

---

## Schedule (one SoT)

| | |
| --- | --- |
| Source | ESPN public team schedule API (`site.web.api.espn.com`), `seasontype=2` regular + `seasontype=3` postseason |
| Why ESPN | CFBD `/games` requires a key (401 here). NCAA HTML is not a clean machine SoT. |
| as_of | 2026-08-13 |
| Engine path | `services/model-service/src/services/cfb_season_engine/data/cfb_official_schedule_2026.json` |
| Warehouse copy | `data/cfb/warehouse/clean/schedules/cfb_official_schedule_2026.json` (local; `clean/` is gitignored) |
| n_games | **889** |
| slate_complete | **true** |
| FCS games | 149 (labeled `fcs:*` placeholders — not generic −25) |
| Postseason / CFP / bowls | **0** (ESPN `seasontype=3` returned no events) |
| Week 15 | Army vs Navy, 2026-12-12, MetLife — ESPN still tags this regular |
| Independents | ND 12 games, CONN 12 games |
| Missing official teams | none (136/136 mapped) |
| Densified seed | **not used** when this package is present |

### Games by week

| Week | Games | Notes |
| ---: | ---: | --- |
| 0 | 8 | Kickoff date before 2026-09-01 (ESPN often labels these Week 1) |
| 1 | 89 | |
| 2 | 86 | |
| 3 | 74 | |
| 4 | 71 | |
| 5 | 59 | |
| 6 | 58 | |
| 7 | 62 | |
| 8 | 56 | |
| 9 | 56 | |
| 10 | 63 | |
| 11 | 67 | |
| 12 | 70 | |
| 13 | 69 | |
| 15 | 1 | Army–Navy only |
| **Total** | **889** | |

Week 0 examples: UNC vs TCU (Aviva, Dublin), plus other Aug 29 openers.

---

## Roster before / after

Root cause of the 11 holes: engine prior book had FCS/alias extras (`ACU`, `CHAT`, `FAU2`, `FAY`, `IDHO`, `OLE`, `OREST`, `SOUTH`, `TA&M`, `TXAM`, `ULL`) instead of the official codes. Packager only fetched codes already in that book.

| | Before | After (2026-08-13) |
| --- | --- | --- |
| Official FBS in universe | 125 (11 missing) | **136 / 136** |
| Holes | ARST, CSU, ECU, JVST, MIZZ, NEV, ODU, TOL, UAB, UNM, UNT | **none** |
| MIZZ in DNA | labeled `roster_pack_missing_neutral` | present (Austin Simmons, incumbent) |
| Still missing after best effort | — | **[]** |
| Camp QB SoT (UGA / MICH / FSU / LSU / ALA) | open / high-σ | **unchanged** `open_competition` |

Filled from ESPN 2026 rosters (aliases `MIZZ→MIZ`, `JVST→JXST`). Report: `data/ops/cfb-2026-roster-holes-20260813.json`.

### Still broken for DNA (labeled, not silent 0)

The same 11 codes plus **M-OH** are **still missing from the 2025 SP+ efficiency snapshot**. Engine uses `league_average_fill` / `fidelity=placeholder` for those rows. That is honest — do not invent SP+.

---

## Week 0 smoke (official slate rows, N=800, research only)

| Matchup | Week | Date | Spread (home) | Total | WP home | used_in_spread |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| UNC @ TCU (neutral, Dublin) | 0 | 2026-08-29 | −16.7 | 53.7 | 75% | false |
| SJSU @ USC | 0 | 2026-08-29 | −28.5 | 62.0 | 88% | false |
| NCSU @ UVA | 0 | 2026-08-29 | −4.7 | 57.3 | 58% | false |
| HAW @ STAN | 0 | 2026-08-29 | +7.9 | 51.1 | 37% | false |
| NMSU @ FSU (open camp) | 0 | 2026-08-29 | −13.0 | 53.9 | 70% | false |

USC −28.5 is still ranking-prior theater if sold as a line. That is why `used_in_spread` stays false.

ND and UConn are on both slate and roster.

---

## Engine wiring

- Season-sim / “full season” reads official slate when packaged (`slate_complete=true`).
- On-demand `project-game` unchanged for arbitrary matchups.
- If slate missing/thin: `slate_complete=false` and win tables emit `win_tables_status=incomplete_slate_not_final` / `win_tables_final=false`.
- Status 200 exposes `schedule_source`, `schedule_as_of`, `n_games`, `slate_complete`, `roster_coverage_official`.
- `used_in_spread=false` on prediction writes. No KEI. CFP/natty stay stub (`null`).

---

## Limited P4 season win totals?

**Yes — limited research win totals on the real slate are unblocked.**  
**No — not as product truth, and not CFP/natty.**

| Question | Answer |
| --- | --- |
| Official slate? | Yes (889, complete) |
| Roster 136/136? | Yes |
| Win tables final? | **No** (`win_tables_final=false`) |
| used_in_spread / KEI? | **false** / none |
| CFP / natty %? | **Stub** (and ESPN has 0 postseason events) |
| Calibration first? | **Yes, before desk-trusting the win numbers.** Walk-forward still ~47.7% ATS; OSU-class blowouts are still ranking theater. Efficiency holes on the 11 filled rosters add DNA noise. |

Recommendation: ship this as the official-slate research path. Next honest pass is **calibration / scale**, not CFP marketing.

---

## Rebuild

```bash
python scripts/cfb/package_official_schedule_2026.py
python scripts/cfb/fill_roster_holes_2026.py
```
