# Build — t4770u 2026 W1–W8 efficiency recovery

Offline only. No `DATABASE_URL`. No C10 / Railway. No paid data.

## Approved source

```
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
```

Same URL template CLEARed on t4696u S1 restage (2012–2022). Public HTTPS. Hash raw bytes before parse.

## Rebuild

From repo root:

```bash
python3 scripts/nfl/build_efficiency_2026_w1_w8_t4770u.py
python3 scripts/nfl/prove_if_consume_2026_w09_t4770u.py
cd services/model-service && python3 -m pytest tests/test_nfl_efficiency_2026_w1_w8_t4770u.py -q
```

`--skip-fetch` reuses `data/raw/nfl/pbp/t4770u/play_by_play_2026.parquet` (gitignored).

## Transforms (Alex contract 24600552 — existing only)

- T1 situational weekly from PBP pass/run (ingest.py semantics)
- T2 rolling 5g `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` per team-week
- T3 matchup diffs per ingest.py
- T4 `matchup_diff_success_rate_5g` = mean of both success terms
- T5 `team_strength_from_record` on 2026 W-L (ties recorded, excluded from wp denom)
- Rest days: `rest_days_from_schedule`
- W9 consume uses each team's latest rolling row with week ≤ panel cap (7 while W8 incomplete; 8 only when W8 is final).
`travel_*` / `info_velocity_*` / `hours_since_change_*` are written None (IMV d2587de7 D1). Contract bind stays NOT_FINAL until Alex v2 + IMV PASS_CONTRACT.

## Fail closed

Week 8 incomplete → `DATA_PARTIAL`. Do not declare through-W8. Do not fill with 2025 priors.
