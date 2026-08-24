# Edge Current — simple book-line gate (unblank) — 2026-08-24

**Branch:** `cursor/edge-current-unblank-e929` → `deploy-vercel`  
**Baseline:** post-#288 (`73e8ecd`) over-tight Current hygiene

## Rule

Spread valid iff number in **[-20, 20]** and integer / `*.0` / `*.5`.  
Total valid iff number in **[30, 65]** and integer / `*.0` / `*.5`.  
Else that market’s Current is `—`. Never round. Never reject because Current equals Open. Parse `−3.5` (U+2212) as `-3.5`.

## Ops line

**Before: 0/16 Current (all —). After: 16/16 valid.** Zero `3.8` / `2.4` / `−3.58` class.

## Before (user report post-#288)

Week 1 Current fully blank on the board (over-reject: PK `0`, unicode minus, `looks_like_*`). Junk AVG tenths were correctly rejected; standard snapshot consensus (`−3.5` / `44.5`) was not allowed through. Do not reject Current because it equals Open (NE@SEA / CLE@JAX snapshots are currently Current = Open).

## After (Railway snapshot consensus, 2026-08-24, then this gate)

| Game | Current spread | Current total | Gate |
|------|----------------|---------------|------|
| NE@SEA | −3.5 | 44.5 | keep (Current = Open; Action still allowed) |
| SF@LAR | −3.5 | 48.5 | keep |
| GB@MIN | −1.5 | 45.0 | keep |
| ATL@PIT | −3.0 | 42.5 | keep |
| MIA@LV | −3.5 | 40.5 | keep |
| BUF@HOU | +1.5 | 44.5 | keep |
| WAS@PHI | −4.5 | 46.5 | keep |
| NO@DET | −7.0 | 48.5 | keep |
| CHI@CAR | +2.5 | 47.5 | keep |
| BAL@IND | +3.5 | 48.5 | keep |
| NYJ@TEN | −2.5 | 39.5 | keep |
| CLE@JAX | −7.5 | 40.5 | keep (Current = Open; Action still allowed) |
| DAL@NYG | +2.5 | 48.5 | keep |
| ARI@LAC | −10.5 | 46.5 | keep |
| TB@CIN | −3.5 | 51.5 | keep |
| DEN@KC | −3.0 | 42.5 | keep |

Reject reasons for a blank Current live in `diagnostics.current_hygiene.week1[].spread_reason|total_reason` (`not_half_point` / `out_of_range` / `missing`). Open unchanged; no Open→Current copy.
