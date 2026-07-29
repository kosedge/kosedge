# NFL owned open/close densify (2020–2023 + residual 2024–25)

Generated: `2026-07-28T15:16:30+00:00`  
DB: `127.0.0.1:5432/kosedge` (promoted restore warehouse)  
Branch: `nfl-kav-sharpen`  
Scope: odds ingest + CLV/open-close grading only (no game-model retrain/re-sim)

## Verdict

Owned open/close is now dense across **all 1693** final schedule games 2020–2025.  
CLV sample size: **spread 159 → 545**, **total 117 → 309** (both hundreds+).  
Credits used this workstream: **6,742** (~2.992M remaining).

## Coverage by season (schedule-final games with owned OC join)

| Season | Before `n_owned_oc` | After `n_owned_oc` | Schedule n | Still missing 2+ timestamps |
|--------|--------------------:|-------------------:|-----------:|----------------------------:|
| 2020   | 0                  | 269                | 269        | 0                           |
| 2021   | 0                  | 285                | 285        | 0                           |
| 2022   | 0                  | 284                | 284        | 0                           |
| 2023   | 0                  | 285                | 285        | 0                           |
| 2024   | 229                | 285                | 285        | 0                           |
| 2025   | 235                | 285                | 285        | 0                           |
| **All**| **724 owned games / 296 joined** | **1931 owned games / 1172 joined** | **1693** | **0** |

`odds_snapshots`: **60,183 → 80,995**.

## CLV n before → after

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| `n_clv_spread` | 159 | **545** | +386 |
| `n_clv_total`  | 117 | **309** | +192 |

CLV rates/avgs are reported in `nfl-odds-open-close-grading.json` for the densify workstream; overall model score remains owned by the parallel KAV retrain agent.

## Credits

| Phase | Credits |
|-------|--------:|
| NFL 2020–2023 mainline densify (`densify_owned_oc_2020_2023.py`) | 6,022 |
| Residual 12-date force pull | 720 |
| Orphan→schedule rematch | 0 |
| **Total** | **6,742** |

- Starting remaining: **2,999,276**  
- Ending remaining: **2,992,534**

## What we did

1. **DB-first densify** via `scripts/nfl/densify_owned_oc_2020_2023.py` (wraps enterprise pull, NFL mainlines only, skip-if-owned, no props). 244 slate dates scanned; 144 skipped as owned; 200 historical requests.
2. **Diagnosed false “missing OC”**: Odds API persist created duplicate `games` rows (Odds event ids) while grading joins `nfl_dp_schedules.game_id → games.external_id` (nflverse ids). Odds were present but unjoined.
3. **Rematched orphans** with `scripts/nfl/rematch_orphan_odds_to_schedule.py` (date±1 + home/away unique match) — 11k+ snapshot relinks, no API burn.
4. **Force-pulled 12 residual dates** (~720 credits), rematched again → **0 schedule gaps**.
5. **Re-ran** `scripts/nfl/odds_open_close_grading.py`.

## Residual / follow-ups

- **Schedule OC gaps:** none remaining for 2020–2025 finals.
- **CLV n ceiling:** still limited by projection coverage + edge thresholds (`|model−open| ≥ 0.5` spread / `≥ 1.0` total), not missing opens/closes.
- **Persist hygiene:** prefer binding historical Odds API events to nflverse schedule game rows so rematch is unnecessary.
- **User/ops:** local API key OK; local warehouse already promoted. Prod promote still separate if needed. No commit/push from this workstream.

## Artifacts

- `data/ops/nfl-oc-densify-2020-2023-report.md` / `.json` (this report)
- `data/ops/nfl-odds-open-close-grading.json` / `.md`
- `data/ops/odds-enterprise-training-pull/{checkpoint,summary,pull}.json|log`
- `data/ops/nfl-oc-orphan-rematch.json`
- `data/ops/nfl-oc-residual-gap-pull.json`
- `scripts/nfl/densify_owned_oc_2020_2023.py`
- `scripts/nfl/rematch_orphan_odds_to_schedule.py`
