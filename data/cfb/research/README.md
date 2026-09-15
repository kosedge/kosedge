# CFB research restores (gitignored bulk)

Current-season SportsDataverse files are **versioned separately** from the
historical Aug 13 lake.

| Role | Path |
| --- | --- |
| Historical CANONICAL (2014–2025) | `/Volumes/KosEdgeData/raw/cfb/pbp/play_by_play_{year}.parquet` |
| Current-season HD target | `/Volumes/KosEdgeData/raw/cfb/pbp_current/as_of_YYYYMMDD/` |
| This VM (gitignored) | `data/cfb/research/pbp_current/as_of_YYYYMMDD/` |

Do not overwrite the historical directory. Committed summaries live under
`data/ops/cfb-2026-current-season-proof-YYYYMMDD/`.
