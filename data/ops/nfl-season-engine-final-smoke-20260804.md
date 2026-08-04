# NFL Season Engine — Final Smoke, Trust Check & Light UI Polish

**Date:** 2026-08-04  
**Engine (pre):** `nfl-season-engine-v1.9.1-real-depth` (live Railway at smoke time)  
**Engine (ship):** `nfl-season-engine-v1.9.2-smoke-polish`  
**Branch:** `feat/nfl-season-engine-final-smoke` → `deploy-vercel`  
**Artifacts:** `data/ops/nfl-season-engine-final-smoke-20260804/`  
**Script:** `scripts/nfl/final_smoke_season_engine.py`

## Live status (www BFF → Railway)

| Field | Value |
| --- | --- |
| `mode` | `real` |
| `schedule_source` | `packaged_wall_chart_2026` |
| `schedule_game_count` | 272 |
| `depth_source` | `packaged_nflverse_depth_2026` |
| `depth_as_of` | `2026-08-03` |
| Named skill teams | 32 / 32 |

## Results summary

| Area | Result | Notes |
| --- | --- | --- |
| Status / real schedule+depth | **Passed** | Mode real, 272 games, 32/32 named skill |
| Future game boxes (5 matchups) | **Passed** | SF@LA W1, DET@BUF W2, KC@MIA W3, LAC@SEA W4, ARI@DAL W8 |
| Roles vs packaged depth | **Passed** | CMC RB1, Purdy QB1, Nacua WR1, Stafford QB1, Kyren RB1, etc. |
| Yard/TD sanity | **Passed** | No Cook-100 / WR-9-catch regression; QB ~180–200 pass yds, ~0.9 TD / ~0.6 INT |
| Injury CMC W1–4 | **Passed** | CMC rush 56.5 → 0; Jordan James 24.6 → 60.6 (promoted RB1) |
| Injury CMC outside window | **Passed** | SF@SEA W5 CMC rush ~57 after W1–4 out |
| Injury WR1 Evans W1–3 | **Passed** | Evans rec 4.2 → 0; Deebo/Kirk absorb targets |
| Survivor already_used | **Passed** | BUF/KC excluded when marked used |
| Survivor rankings | **Passed** | Favorites / home spots near top (not random) |
| Survivor byes W5 CAR/KC | **Passed** | Neither in ranked_picks |
| Edge: both-on-bye matchup | **Weak → Fixed (label)** | API still returns hypothetical boxes; now notes `bye_warning` + UI amber banner |

Machine-readable: `smoke-report.json` (13 pass / 1 weak / 0 fail on final re-run before engine note patch).

## Sample: SF @ LA week 1 (p50-ish point estimates)

| Team | Player | Role | Key |
| --- | --- | --- | --- |
| SF | Brock Purdy | QB1 | pass 188 / TD 0.92 / INT 0.56 |
| SF | Christian McCaffrey | RB1 | rush 55 / rec 2.2 |
| SF | Mike Evans | WR1 | rec 4.1 / 44 yds |
| LA | Matthew Stafford | QB1 | pass 192 / TD ~0.9 |
| LA | Kyren Williams | RB1 | rush 40 |
| LA | Puka Nacua | WR1 | rec 5.3 / 56 yds |

## Soft modeling weaknesses (follow-ups — not fixed here)

1. **Camp depth churn / surprising landings** — packaged nflverse 2026-08-03 identities taken as-is (e.g. Evans on SF, Walker on KC). Re-package after cuts.
2. **Efficiency still league priors** when `nfl_player_projection_baselines` empty for 2026.
3. **Injured player may keep role label** (CMC still shows `RB1` at 0 yards) while usage is zeroed — confusing copy, not wrong math.
4. **Backup QBs** still get small nonzero pass yards (share split) — thin but not embarrassing.
5. **Survivor scores** are inspectable heuristics (win% vs save), not multi-entry pool EV.
6. **Synthetic matchups** still runnable for what-ifs; honesty is now labeled, not blocked.
7. **QB rush volume** still light for scramblers (Allen etc.) — known from foundation gaps.

## Fixes in this pass

| Item | Change |
| --- | --- |
| Bye / synthetic honesty | `game_query.py` notes: `bye_warning`, `bye_teams_in_query`, `schedule_match_detail` |
| Version | `v1.9.2-smoke-polish` |
| UI polish | Clearer labels, empty/loading/error states, depth as-of banners, median hierarchy, demo language only when `mode===demo` |
| Smoke script | `scripts/nfl/final_smoke_season_engine.py` for repeatable live checks |

## UI polish (restrained)

Pages: `/pro/nfl/model`, `/pro/nfl/game-boxes`, `/pro/nfl/survivor` (+ clients).

- Ready-for-use badge when real schedule + 32/32 depth
- Schedule/depth source + as-of on all three surfaces
- Empty / loading / clearer error copy
- Amber banner for bye/synthetic game-box queries
- Median (p50) emphasized; columns renamed Stat / Median / Range
- Survivor top-pick callout; Win% / Pick now hierarchy
- Edge Board / KEI untouched

## Ready for use

**Yes — ready for Pro use** with the caveats above. Live path is real 2026 schedule + packaged nflverse depth; injury paths and survivor byes behave correctly in smoke.

## Recommended follow-ups

1. Re-package / re-ingest depth after major camp cuts; prefer DB weekly when populated
2. Wire 2026 player efficiency baselines (kill league-prior yards for stars)
3. Clearer injured-player role labeling (e.g. `OUT` vs keeping RB1)
4. Optional: refuse or strongly gate game-boxes when both teams on bye
5. Survivor multi-entry / field EV
6. Auto-ingest official injury reports into `InjuryPath`
7. Heavier CLI/worker season sims (1k–10k) outside HTTP
