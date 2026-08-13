# NFL Week-1 depth + props perfect — 2026-08-13

Branch: `feat/nfl-week1-depth-props-perfect`  
Depends on: #226 (`20260813T151800Z` role-aware shape)  
Web bundle (this pass): `nfl-preseason-sim-2026-20260813T161500Z`

## What shipped

1. **League-wide depth identity audit** vs 2025 pack + ADP. Walker/Charbonnet applied through **one** `SOT_SKILL_OVERRIDES` path. Other 2025→2026 star moves flagged, not auto-moved (ADP agrees with pack). See `nfl-depth-identity-audit-20260813.md`.
2. **SEA/KC production realloc only** (team rush/pass/TD budgets conserved). Gibbs/Allen/Lamar/Puka untouched except rank slots.
3. **JSN / Puka** measured, not ADP-copied.
4. **Weekly props:** `PROPS_PATH_COHERENT=gated` — hard UI banner, fetch short-circuits so stale Railway box-sim rows cannot render.

QB1 SoT unchanged → **no 100k team re-sim**. KEI Week 1 untouched.

## Before / after (Half-PPR, points sort)

| Player | #226 (151800Z) | This pass (161500Z) |
|--------|----------------|---------------------|
| Walker | KC RB — 601 rush, overall ~75-class | **SEA RB6 / overall 41 / 266 pts / 1395 rush / ADP 18** |
| Charbonnet | SEA RB1 / RB9 / overall 59 / 240 pts / 1188 rush / ADP 124 | **SEA RB2 / RB13 / overall 68 / 225 pts / 982 rush** |
| Gibbs | DET RB4 / overall 23 / 290 pts | **DET RB4 / overall 24 / 290 pts** (1 slot; Walker entered the board) |
| JSN | WR16 / overall 54 / 252 pts / 1276 rec / ADP 6 | **WR13 / overall 50 / 255 pts / 1293 rec** |
| Allen | QB8 / overall 10 / 324 pts | **QB8 / overall 10 / 324 pts** |
| Lamar | QB9 / overall 11 / 321 pts | **QB9 / overall 11 / 321 pts** |
| Puka | WR5 / overall 30 / 283 pts / 1450 rec | **WR6 / overall 31 / 283 pts / 1450 rec** |

Top-5 RB spread: CMC 369 → Henry 267 (**102 pts**, still ≫ blob).

## Part 3 — alpha WR

- **JSN:** WR1 share already ~24–25% of a run-heavy SEA pool. Rec 1276→1293 (SEA-only WR pin). Rank WR16→WR13. ADP 6 is a pass-budget ceiling, not a committee-flat role bug. Not forced to ADP.
- **Puka:** 1450 rec, LAR WR1 pin already at the cap. Overall 31 vs 30 is QB-flood + one SEA/KC slot, not a role bug.

## Part 4 — weekly props

`PROPS_PATH_COHERENT=gated` (not `partial`, not fake `yes`).

Weekly `/props/board` is Postgres box-sim (Railway), not the season CSV. Re-feeding it this pass would either divide season totals by 17 or serve pre-#226 magnet + KC-Walker rows. **Option C:** hard gate — “Weekly player props not live — season desk only.” `fetchNflPropsBoard` returns empty without hitting the API. Season fantasy + projections stay live.

Flip `NFL_WEEKLY_PROPS_LIVE` to `true` only after box-sim lineage matches `20260813T161500Z`.

## Hard gates

| Check | Result |
|-------|--------|
| Walker team | **SEA** |
| Charbonnet | **RB2**, not false RB1 |
| Charbonnet RB rank | **RB13** (outside top 8) |
| Gibbs | **RB4 / overall 24** (not worse than RB top 5; overall +1 vs #226) |
| Allen / Lamar | **overall 10 / 11** |
| JSN | **WR13** (right direction) + SEA budget note |
| Top-5 RB spread | **102 pts** |
| Weekly props | **gated** (honest not-live banner) |
| Checksum | Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler **PASS** |
| Edge Board W1 / KEI | untouched |

## Other “wrong team” names (do not merge-blind)

See audit note. Highest-visibility CSV leftover vs pack/ADP: **Mike Evans** (CSV TB vs pack/ADP SF) and **Emeka Egbuka** (CSV SF vs pack/ADP TB). Also on the fantasy list with 2025→2026 franchise moves that ADP agrees with: A.J. Brown NE, DJ Moore BUF, Etienne NO, Montgomery HOU, Waddle DEN, Pittman PIT, Pacheco DET.

## Pointer

`data/ops/nfl-web-launch-bundle.json` → `nfl-preseason-sim-2026-20260813T161500Z`. `locked_snapshot: false`.
