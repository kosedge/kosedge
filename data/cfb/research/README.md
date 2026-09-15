# CFB research restores (gitignored bulk)

Current-season SportsDataverse files are **versioned separately** from the
historical Aug 13 lake.

| Role | Path |
| --- | --- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{year}.parquet` |
| Current-season HD target | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/` |
| This VM current-season (gitignored) | `data/cfb/research/pbp_current/as_of_YYYYMMDD/` |
| This VM historical research restore | `data/cfb/research/pbp_hist/as_of_YYYYMMDD/` |
| Historical research HD mirror (documented) | `/Volumes/KosEdgeData/raw/cfb/pbp_research/as_of_YYYYMMDD/` |

Do not overwrite the historical directory.

Per as_of folder (gitignored):

| File | Role |
| --- | --- |
| `play_by_play_2026.parquet` | SDV current-season PBP restore |
| `cfb_schedule_2026.parquet` | SDV schedule restore |
| `eligibility_manifest.json` | completed ∩ PBP ∩ week &lt; W include/exclude |
| `team_game_raw_unadjusted.json` | research team-game metrics (`opponent_adjusted=false`) |

These are **raw unadjusted team-game metrics**, not KE Ratings.

Phase 1 KE measurement may also cache nflverse / SDV parquet under
`ke_football_pbp/` (gitignored). That cache is research-only and must not
write 2026 into `raw/cfb/pbp/`.

Committed summaries live under `data/ops/cfb-2026-w1-raw-team-game-YYYYMMDD/`
(and the #558 proof folder).
