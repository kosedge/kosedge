# NFL Roster Source-of-Truth → Season Engine — 2026-08-09

Branch: `feat/nfl-roster-sot-engine` → `deploy-vercel` (+ Railway model-service).

## Goal

One authoritative player→team map. Wrong assignments distort volume, usage, PF,
and wins. The season engine must never carry an independent roster map that can
diverge from the depth SoT.

## Single source of truth

| Artifact | Path | Role |
|----------|------|------|
| **Depth / roster SoT** | `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json` | Exclusive player→team + skill depth 1–3 |
| **Loader** | `nfl_season_engine/loaders.py` → `load_packaged_depth_chart` | Engine universe identities |
| **Packager** | `scripts/nfl/package_season_engine_depth_2026.py` | nflverse → pack + SoT QB overrides |
| **Intel** | `GET /nfl/intel/depth-charts`, `/rosters` | Pack-primary when SoT present |
| **Label repair** | `canonical_qb1_from_depth_sot()` | Derived from pack — not a second map |

**Forward rule:** Depth/roster changes update the pack (and packager overrides)
only. The season engine never again carries independent player-team assignments.

## Root cause

1. Packaged depth (PR #150 / v1.9.1) correctly had **Kyler → MIN**, **Brissett → ARI**.
2. A later “QB hygiene” edit on the 100k candidate path swapped Kyler back to ARI
   and McCarthy to MIN — creating a dual truth vs FantasyPros / rookie-flag metadata.
3. Engine load preferred DB weekly/official over the pack when any rows existed,
   so stale DB could silently override SoT.

## Fix

1. Restored SoT pack:
   - **MIN QB:** Kyler Murray / J.J. McCarthy / Carson Wentz
   - **ARI QB:** Jacoby Brissett / Gardner Minshew II / Carson Beck
   - Kept legitimate ATL (Penix) / MIA (Tua) corrections
2. `load_universe_from_db` now prefers packaged depth whenever the pack exists;
   DB weekly/official are ignored for identities (noted in universe `rosters`).
3. Intel depth/roster endpoints are pack-primary when SoT is available.
4. `CANONICAL_QB1_BY_TEAM` / `repair_qb_team_labels` derive from the pack.
5. Continuity `fetch_current_qb1` prefers packaged SoT.
6. Packager applies `SOT_QB_OVERRIDES` so re-packaging cannot reintroduce Kyler→ARI.

## Before / after (high-impact)

| Player | Before (broken hygiene) | After (SoT) |
|--------|-------------------------|-------------|
| **Kyler Murray** | ARI QB1 | **MIN QB1** |
| Jacoby Brissett | MIN QB2 | **ARI QB1** |
| J.J. McCarthy | MIN QB1 | **MIN QB2** |

Other pack QB SoT (unchanged this pass): Penix→ATL1, Tua→MIA1, Willis→ATL2.

## Confirmation gates

- Tests: `services/model-service/tests/test_nfl_roster_source_of_truth.py`
  - Engine QB/team for Kyler is MIN
  - ARI QB depth has no Kyler
  - Stale DB weekly Kyler→ARI is ignored when pack exists
- Existing SoT smoke (`test_nfl_depth_coaching_sot.py`) again aligns (ARI Brissett)
- Conservation: pass/rush pools and win-sum rules untouched; only roster identities
  moved. Re-sim refreshes ARI/MIN volume/shares/PF/wins under the corrected map.

## Re-sim (2026-08-09)

Bundle: `data/ops/nfl-preseason-sim-2026-roster-sot-20260809`  
(`--force-packaged`, 5k team / 200 player)

| Check | Result |
|-------|--------|
| Universe roster source | `packaged_nflverse_depth_2026` |
| Kyler | `MIN-QB1-KylerMurray` (~3254 pass yds mean) |
| ARI QB depth | Brissett / Minshew / Beck — **no Kyler** |
| MIN QB depth | Kyler / McCarthy / Wentz |
| Wins sum (team W/L) | **272.0** |
| ARI expected wins | ~6.41 (p50 6) |
| MIN expected wins | ~8.23 (p50 8) |

Locked pass-pool / alpha / other settled constraints were not modified; only the
roster map SoT path changed.

## Explicit statement

The season engine now has **zero reliance on stale packaged or DB player-team
maps that diverge from the depth SoT**. When
`nfl_depth_chart_2026_w1.json` is present for the season, it is the only
player→team identity source for sim start and refresh.
