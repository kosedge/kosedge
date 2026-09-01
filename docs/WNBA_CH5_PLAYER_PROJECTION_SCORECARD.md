# WNBA Chapter 5 — PlayerProjection scorecard

**Stamp:** `wnba-season-engine-v0.1` · as_of `2026-09-01`  
**Object:** `PlayerProjection`  
**Pack:** `wnba_player_projection_2026.json`  
**Players:** 135 (15 × 9)  
**Brief:** [`docs/WNBA_CH5_PLAYER_PROJECTION_BRIEF.md`](./WNBA_CH5_PLAYER_PROJECTION_BRIEF.md)

---

## Formula

```text
rate_y = stat_per_g / mp_per_g
rate   = Σ_y w_y · rate_y          # w = 0.20 / 0.30 / 0.50 (2024/2025/2026)
raw    = rate × MIN × (team_pace / league_pace)
PTS_i  = raw_PTS_i × (implied_ppg / Σ raw_PTS)
σ_rate = pstdev(season rates) if n≥2 else 0.15·|rate|
σ_stat = σ_rate × MIN × pace_scale   # PTS σ also × identity scale
```

Vector: `MIN USG PTS REB AST STL BLK TOV 3PM PRA PR RA` + σ each.  
`PRA = PTS+REB+AST`, `PR = PTS+REB`, `RA = REB+AST`.  
Combo σ = √(component σ²).

---

## Identity

| Check                    | Result                                |
| ------------------------ | ------------------------------------- |
| `Σ MIN` per team         | **200** (Ch2 grid)                    |
| `Σ PTS` vs `implied_ppg` | identity-scaled; max drift **≪ 3.0**  |
| Residual cap             | `WNBA_TEAM_REBASE_RESIDUAL_CAP = 3.0` |
| `WNBA_TEAM_CARRY_SHRINK` | **0.85** unchanged                    |
| σ hardcoded 4?           | **No** — season-rate dispersion       |

---

## Reads (only)

- `wnba_minutes_grid_2026.json`
- `wnba_player_talent_3y_2026.json`
- `wnba_team_prior_rebased_2026.json`
- BR WNBA per_game + advanced USG (2024 / 2025 / 2026)

---

## Does not

Board emit · props PLAY/LEAN · new minute grid · NBA means as prior · team if · retune 0.85 · leftover KEI blend · NBA/CFB/NFL packs

---

## Cross-sport gates

| Gate             | Status                          |
| ---------------- | ------------------------------- |
| Leftover KEI ids | `401857105`, `401857106` listed |
| CON@ATL market   | untouched (no board write)      |
| NBA HOU@OKC      | `kei_spread_home ≈ −4.16`       |
| CFB BALL@OSU     | **−40.51**                      |

---

## Next

Chapter 3 situation (WNBA-point coeffs + paper-sim). Then Chapter 4 emit. **Not** props yet.
