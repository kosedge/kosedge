# NFL Adjusted Strength of Competition (Past SOS) — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Builds on merged **#140** (true PR blend) + **#141** (player regression).

Branch: `feat/nfl-adjusted-sos-past` → `deploy-vercel`.

PR: https://github.com/kosedge/kosedge/pull/142

## Goal

Replace crude opponent W% thinking with **Adjusted Strength of Competition**
for the prior season. Past SOS adjusts how we read 2025 (and prior) performance
before it enters the **prior side** of the true PR blend.

**Future / projected 2026 SOS is excluded** from Week 1 intrinsic PR.

## Formula

For each completed REG game in the prior season used for the prior package:

1. **Opponent intrinsic rating at time of game**
   - Prefer: opponent rolling EPA (`nfl_dp_team_rolling_features_weekly`) at
     week **W−1** (strict lag; no same-week leakage)
   - Fallback: season opponent package → labeled **`approximate`**
2. **Optional context when data exists**
   - Venue: modest HFA on effective opponent defense EPA faced
   - Rest: short-rest ease/hardness from schedule `game_date` gaps
   - Active-roster / injury-at-time depth: **stub** (`injury_at_time_depth`)
3. **Actual SOS**
   - Offense SOS = mean effective opponent **defense** EPA faced
     (higher = softer slate)
   - Defense SOS = mean effective opponent **offense** EPA faced
     (higher = harder slate)
4. **Schedule-adjusted performance** (dampen `_SOS_DAMPEN = 0.70`)

```
adj_off = raw_off + 0.70 × (league_def − mean_opp_def_faced)
adj_def = raw_def + 0.70 × (league_off − mean_opp_off_faced)
```

Soft slate (high opp.def EPA allowed) → schedule-adjusted offense **below** raw.  
Hard slate → schedule-adjusted offense **above** raw.

Primary metric is **opponent efficiency / power**, not opponents’ combined W%.

## Wiring

| Step | Path |
|------|------|
| Pure math | `nfl_season_engine/adjusted_sos.py` |
| Live prior load | `_load_team_strength_priors` → `_apply_past_sos_to_prior_packages` **before** blend |
| Packaged cold-start | `scripts/nfl/build_packaged_efficiency_backbone.py` bakes `past_sos` into JSON |
| Drivers | `drivers.past_sos` + stubs (`injury_at_time_depth`, `full_venue_model`) |

Blend weights (0 / 1 / 4 / 8 games) unchanged. Uncertainty still
`uncertainty_from_games(current_reg)` — this pass improves priors, not false
tight confidence.

## Data sources

| Source | Role | Quality |
|--------|------|---------|
| `nfl_dp_schedules` (prior season REG completed) | Game list + venue + rest dates | Real |
| `nfl_dp_team_rolling_features_weekly` week W−1 | Time-of-game opponent off/def EPA | Real (preferred) |
| Season package / prior package EPA | Approximate opponent book when lag missing | Approximate |
| HFA + short-rest scalars | Partial venue/rest | Partial |
| Active roster / injury at time of game | — | Stub |
| Full weather / travel / roof model | — | Stub (`full_venue_model`) |
| 2026 projected schedule | — | **Excluded** |

## Example teams (2025 prior → 2026 packaged, local rebuild)

From packaged artifact coverage (`time_of_game_share_mean ≈ 0.88`):

| Slate | Team | Raw off EPA | Schedule-adj off EPA | Δ | Note |
|-------|------|------------:|---------------------:|--:|------|
| Soft | **NE** | 0.090 | 0.046 | −0.044 | Soft slate → adj below raw |
| Soft | MIN | −0.115 | lower | − | Same polarity |
| Hard | **SF** | 0.061 | 0.111 | +0.050 | Hard slate → adj above raw |
| Hard | IND | 0.072 | higher | + | Same polarity |

Hierarchy after SOS (still football-plausible): top includes LA / SEA / DEN / HOU;
SEA composite ≫ ARI; NE remains top-10 after soft-slate deflation (not floor).

## Smell tests (automated)

File: `services/model-service/tests/test_nfl_adjusted_sos_past.py`
(+ existing true PR / backbone / player-regression suites)

| # | Check | Result |
|---|-------|--------|
| 1 | Soft slate → schedule-adj offense below raw | PASS |
| 2 | Hard slate → schedule-adj offense above raw | PASS |
| 3 | Packaged SEA ≫ ARI; NE still top-half | PASS |
| 4 | Blend 0 / 1 / 4 / 8 unchanged (no cliff) | PASS |
| 5 | Full-strength injury path + player regression healthy | PASS |
| 6 | Remaining stubs labeled | PASS |

Local venv run (2026-08-08): **45 passed** across SOS + true PR + backbone +
packaged EPA + player regression suites.

## Real vs approximate

**Real**

- Past SOS from schedules + lagged rolling opponent EPA
- Schedule-adjusted prior EPA on live load + packaged artifact
- Drivers: raw vs schedule-adj, Actual SOS, time-of-game share
- Future schedule excluded from intrinsic PR

**Approximate / partial**

- Week-1 (and missing lag) opponent ratings → season package
- One-pass dampened adjustment (not full iterative KAV rewrite)
- Venue = modest HFA only; rest = short-rest scalars only

**Stub**

- True injury / active-roster depth at time of game
- Full venue model (roof/travel/weather)
- Forward 2026 SOS product / UI
- Opponent-tier performance dashboard

## Remaining gaps (next passes — no scope creep)

1. Forward **2026 projected SOS** product — **shipped** as outlook-only layer
   (`nfl-projected-sos-2026-20260808.md`; never Week 1 intrinsic PR)
2. Opponent tiers UI / performance-vs-tier dashboard
3. Full active-roster / injury-at-time opponent adjustment
4. Richer venue model beyond HFA + short rest
5. Optional: wire KAV weekly tables when present as alternate time-of-game book
6. Continuity score / real QB premium — **shipped** (#143 / #144)

## Progress line

Past SOS landed: schedule-adjusted prior performance from time-of-game opponent
efficiency feeds the prior side of the true PR blend; soft/hard slate polarity
verified; #140 blend and #141 player stack preserved.
