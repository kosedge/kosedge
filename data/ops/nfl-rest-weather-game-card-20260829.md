# Rest + weather game-card fields on remat (2026-08-29)

**Branch:** `cursor/rest-weather-game-card-7d1e` → `deploy-vercel`  
**Depends on:** #302 unit shock table (merged; e253 `a3256176d717`)  
**Doctrine:** Game-card / cheap handicap fields only on remat. Deterministic modifiers. **Missing weather ⇒ no KEI change.** Notes / camp / sleeper / DepthSot notes **cannot write** these fields.

## Fields

| Field | Role |
|-------|------|
| `days_rest_home` / `days_rest_away` | Rest advantage (≥3 day Δ) |
| `short_week` | Side ≤5 days rest (or explicit flag) |
| `timezone_shift` | Absolute TZ bands (1/2/3) — visitor weaker |
| `roof` | Indoor/dome → weather not applied |
| `wind_mph` / `precip` / `temp_f` | Totals-first weather bands (Gate B.1 magnitudes) |

## Wiring

| Piece | Path |
|-------|------|
| Module | `services/model-service/src/services/nfl_rest_weather_game_card.py` |
| Remat / KEI | `apply_week1_kei_reprice(..., game_card=...)` |
| Notes guard | `ALLOWED_FIELDS` excludes game-card keys; `reject_note_game_card_write`; `assert_notes_cannot_touch_lines` |

When `game_card` is omitted, legacy Week 1 TZ-from-teams + weather_obs path is unchanged.

## Magnitudes (deterministic)

| Factor | Spread (home convention) | Total |
|--------|--------------------------|-------|
| Rest advantage ≥3 days (home rested) | −0.50 | +0.15 |
| Short week (away) | −0.75 | −0.25 |
| TZ ≥3 / ≥2 / ≥1 | −1.00 / −0.75 / −0.35 | −0.50 / −0.30 / −0.15 |
| Wind ≥25 / ≥20 | 0 | −1.5 / −1.0 |
| Temp ≤20°F | 0 | −0.5 |
| Precip ≥2 | 0 | −0.5 |
| Weather stack cap | — | ±1.5 |

## Out of scope (explicit)

- Snap-share priors
- `shock_table_v1` edits
- Live desk accepts
- Confirmation / variance
- Invented climatology when weather missing

## Tests

`services/model-service/tests/test_nfl_rest_weather_game_card.py`
