# NFL KEI Gate B.1 — weather + refs — 2026-08-13

**Module:** `services/model-service/src/services/nfl_kei_week1_reprice.py`  
**Doctrine:** Model frozen. KEI = model + desk factors. Caps unchanged: spread ±4 / total ±2. Weather subcap **±1.5 total**. Ref subcap **±0.5 total**. Weather/ref never move the spread.

## Weather

| Situation | Behavior |
|-----------|----------|
| Indoor / dome / typically-closed retractable | `weather not applied (indoor)` — mock wind ignored |
| Forecast already in frozen model | not restacked |
| Kickoff missing | `weather not applied (no kickoff for forecast)` |
| Open-Meteo / VC in 16-day window | bands on **real** wind/temp/precip only |
| Beyond 16-day horizon (Week 1 as of 2026-08-13) | `weather not applied (beyond forecast horizon)` |
| Climatology heuristic | **never used** for KEI |

Bands (totals first, pass-heavy tax via the total):

- wind ≥ 25 mph → −1.5 total
- wind ≥ 20 mph → −1.0 total
- temp ≤ 20°F → −0.5 total
- precip ≥ 2 mm → −0.5 total
- stacked weather clamped at ±1.5

Source: existing `fetch_game_weather_context` (Open-Meteo, optional Visual Crossing). No stadium microclimate. Tests inject `weather_obs`.

## Refs

Pack: `services/model-service/src/services/nfl_season_engine/data/nfl_week1_officials_2026.json`

**Crews: []** — no Week 1 assignments loaded. Driver log: `ref not applied (no Week 1 crew assignment)`. Do not invent officials.

If a real row is added later (`home`, `away`, `crew`, `total_tendency`), KEI applies a tiny total move capped at ±0.5. Refs cannot dominate injury/QB/travel.

## Tests

- Outdoor mock 28 mph wind → KEI total −1.5, spread unchanged
- Dome + extreme obs → indoor, total flat
- Missing crew → not applied
- Crew tendency 1.5 → clamped to +0.5 total

## Caps

Unchanged global ±4 / ±2. Weather/ref sit inside the total cap and have their own subcaps so they cannot swamp WAS OL / travel.
