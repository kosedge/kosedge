# Prod feature export spec (v2.3 / ccecea74)

Parity is **NOT_RUN_NO_PROD_EXPORT** until Platform Reliability or Ryan
supplies a genuine sealed prod export. Do **not** author samples. The v2.2
file `fixtures/parity-prod-w6-sample.jsonl` is **not** an export.

## What to export

One directory, three files:

| File               | Role                                                          |
| ------------------ | ------------------------------------------------------------- |
| `features.jsonl`   | One JSON object per matchup row                               |
| `EXPORT.meta.json` | Provenance (required keys below)                              |
| `EXPORT.sha256`    | Optional copy of the jsonl sha (meta.sha256 is authoritative) |

`EXPORT.meta.json` **must** contain:

```json
{
  "kind": "sealed_prod_feature_export",
  "source": "railway-prod / nfl_dp_matchup_features_weekly",
  "query": "<exact SQL that produced features.jsonl>",
  "sha256": "<sha256 of features.jsonl>",
  "weeks": [3, 4, 5, 6, 7],
  "columns": ["season", "week", "game_id", "home_team", "away_team", "..."],
  "captured_utc": "2026-10-22T..Z",
  "captured_by": "platform-reliability|ryan",
  "window_sql": "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW",
  "db": "production warehouse (not reconstructed)"
}
```

Any other `kind`, missing query/sha/weeks/columns, or sha mismatch →
`NOT_RUN_NO_PROD_EXPORT`.

## Query (copy this)

Prod rolling includes the current week (`ingest.py`:
`ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`). v2.3 therefore compares
**local week W** to **prod week W-1** on the **same team** (not `game_id`).
Export weeks **3–7** of 2026 REG so W4/W5/W6 local rows have a W-1 partner.
W8 plumbing can add week 7 (already) + week 8 only if needed later.

```sql
SELECT
  season,
  week,
  game_id,
  home_team,
  away_team,
  home_off_epa_5g,
  away_off_epa_5g,
  home_def_epa_allowed_5g,
  away_def_epa_allowed_5g,
  home_pass_rate_5g,
  away_pass_rate_5g,
  home_success_offense_5g,
  away_success_offense_5g,
  home_pressure_allowed_5g,
  away_pressure_allowed_5g,
  home_pressure_generated_5g,
  away_pressure_generated_5g,
  home_early_down_pass_rate_5g,
  away_early_down_pass_rate_5g,
  home_red_zone_td_rate_5g,
  away_red_zone_td_rate_5g,
  home_success_defense_allowed_5g,
  away_success_defense_allowed_5g,
  diff_off_epa_5g,
  home_rest_days,
  away_rest_days,
  roof_dome
FROM nfl_dp_matchup_features_weekly
WHERE season = 2026
  AND week BETWEEN 3 AND 7
  AND game_type = 'REG'  -- omit this predicate if the table has no game_type
ORDER BY week, game_id;
```

If rest / roof live on `nfl_dp_schedules` / `nfl_game_context`, LEFT JOIN
them on `(season, week, game_id)` and record the join in `query`.

Team-form columns above are the ones v2.3 diffs (tolerances in
`PARITY_TOLERANCES`). Extra columns are kept for audit.

## How v2.3 joins

`local.week = W`, team T (home or away) ↔ prod row at `week = W-1` where T
is home or away. Prod CURRENT ROW at W-1 includes through W-1, matching
local lag for game week W.

## How to hand it to the Mac worker

```bash
# after writing the dir (do this on a machine that may touch prod; not the seal)
sha256sum features.jsonl   # paste into EXPORT.meta.json
# copy the directory onto the Mac, then:
export IMV_PROD_EXPORT=/abs/path/to/export-dir
python3 scripts/nfl/imv/nfl_imv_v23.py parity \
  --local "$IMV_FEATURE_STORE/features.jsonl" \
  --prod-export "$IMV_PROD_EXPORT" \
  --week-cap 6
```

Unset `IMV_PROD_EXPORT` → `NOT_RUN_NO_PROD_EXPORT` (expected until supplied).
