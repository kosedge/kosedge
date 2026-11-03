# OWNED 2020/21 selected-187 / missingness-400 / clock — UNAVAILABLE

CERT=0. Worker B on THIS Cursor host only. Cos DISK-1 HELD.
`owned_completion_claimed=false`. Related dumps are **not** this source.

Probe host: `cursor` (`bc-02a716be-429a-56c8-ab0f-5f262aa479df`)
Probe UTC: 2026-11-03T16:40:00Z
DATABASE_URL: unset. No local postgres listener.

## Required SoT (worker-visible) — all UNAVAILABLE

| id | path | field | status |
|---|---|---|---|
| selected_187 | `data/ops/nfl_owned_market_v1/owned_2020_21_selected_187.json` | `quotes[187].quote_id` | **UNAVAILABLE** |
| missingness_400 | `data/ops/nfl_owned_market_v1/missingness_400.json` | `rows[400].missing_enum` | **UNAVAILABLE** |
| clock_provenance | `data/ops/nfl_owned_market_v1/clock_provenance.json` | `quotes[].available_at\|observed_at\|captured_at_utc` | **UNAVAILABLE** |

Also absent: `data/ops/nfl-t5119u-r2-owned-coverage`,
`data/ops/nfl-owned-quote-trace-2020-21`,
`/workspace/ops/nfl_enterprise_green_t4359u`,
`/data/nfl/odds_snapshots`.

## Related but NOT the source (do not treat as owned completion)

| path | field | reason |
|---|---|---|
| `apps/web/data/raw/odds/open/2020-*.json` (46 files) + `2021-*.json` (161 files) | Odds-API historical date dump (`timestamp`/`data`) | no selected-187 identity; no missingness-400; no owned clock-provenance contract |
| `apps/web/data/raw/odds/close/2020-*.json` + `2021-*.json` | same dump family | same |
| `data/ops/nfl-owned-data-20260705T201049Z/*.ndjson` | `nfl_dp_*` season=2025 | 2025 warehouse export; no 2020/21 quote rows |
| `DATABASE_URL` / `odds_snapshots` / `nfl_market_history_snapshots` | Postgres owned open/close | env unset; no Cos-host staging under DISK-1 |

No Cos-host run. No invented selected-187. No fictional trace labeled owned-source completion.
Ryan may stage the three required files onto worker-visible storage; B will bind them then.
