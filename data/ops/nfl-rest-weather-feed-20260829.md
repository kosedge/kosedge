# Rest + weather feed (source game-card fields) — 2026-08-29

**Branch:** `cursor/rest-weather-feed-7d1e` → `deploy-vercel`  
**Depends on:** #303 rest/weather game-card remat (`af9ea4c`); live after #306 on e253 (`b5b1241`)  
**Doctrine:** This PR **feeds** `days_rest_*` / `short_week` / `timezone_shift` / `roof` / wind/precip/temp. It does **not** redesign the modifier table. **No accepts.** Notes cannot write these fields. No defense pack edits, no new T1s.

## Sources

| Field | Source |
|-------|--------|
| `days_rest_home` / `days_rest_away` / `short_week` | Packaged `nfl_regular_schedule_2026.json` + canonical kickoff overlay |
| `timezone_shift` | Team TZ bands (west-of-ET), same as KEI |
| `roof` | Explicit `nfl_stadium_roof_table` (dome / retractable_closed / outdoor); venue overrides for internationals |
| `wind_mph` / `precip` / `temp_f` | **Open-Meteo or NWS only** (free). Cache under `data/ops/nfl-rest-weather-cache/` with `as_of` (gitignored, TTL 6h) |

## Contracts

- Timeout / missing weather → leave weather fields `None` → **no KEI weather modifier** (same as #303).
- Do **not** invent `wind=0` for outdoor.
- Indoor / `retractable_closed` → skip weather fetch (roof blocks bands).
- Notes / camp / DepthSot still blocked via `GAME_CARD_FIELDS` + `reject_note_game_card_write`.

## Modules

| Piece | Path |
|-------|------|
| Feed | `services/model-service/src/services/nfl_rest_weather_feed.py` |
| Stadium roof table | `services/model-service/src/services/nfl_stadium_roof_table.py` |
| Remat modifiers (unchanged) | `nfl_rest_weather_game_card.py` |
| Print Week cards | `scripts/nfl/print_rest_weather_week_modifiers.py` |

```bash
cd services/model-service && python -m src.services.nfl_rest_weather_feed
# or
python scripts/nfl/print_rest_weather_week_modifiers.py --week 1
```

## Out of scope

- Defense pack edits / new T1s / accepts
- Snap-share or shock_table rewrites
- Visual Crossing / climatology weather
- Secrets

## Tests

`services/model-service/tests/test_nfl_rest_weather_feed.py` — rest from schedule; timeout weather = no modifier; notes cannot write; stadium roof table; cache `as_of`.

## Week 1 print (2026-08-29) — STOP, no accepts

`n_week=16` / `n_with_modifier=8`. Rest blank (no prior REG). Weather either indoor-skipped, outside Open-Meteo 16d window (DEN@KC Mon), unavailable, or below KEI bands — **only `timezone_shift` applied**.

| Game | Roof | Rest H/A | TZ | Weather | Applied | Spread Δ | Total Δ |
|------|------|----------|----|---------|---------|----------|---------|
| CHI@CAR | outdoor | —/— | 1 | w4,t81F,p0.0 | timezone_shift | -0.35 | -0.15 |
| NO@DET | dome | —/— | 1 | indoor roof=dome | timezone_shift | -0.35 | -0.15 |
| BUF@HOU | retractable_closed | —/— | 1 | indoor roof=retractable_closed | timezone_shift | -0.35 | -0.15 |
| DEN@KC | outdoor | —/— | 1 | outside_forecast_window | timezone_shift | -0.35 | -0.15 |
| MIA@LV | dome | —/— | 3 | indoor roof=dome | timezone_shift | -1.00 | -0.50 |
| DAL@NYG | outdoor | —/— | 1 | unavailable | timezone_shift | -0.35 | -0.15 |
| NE@SEA | outdoor | —/— | 3 | w5,t76F,p0.0 | timezone_shift | -1.00 | -0.50 |
| NYJ@TEN | outdoor | —/— | 1 | w7,t89F,p0.0 | timezone_shift | -0.35 | -0.15 |
