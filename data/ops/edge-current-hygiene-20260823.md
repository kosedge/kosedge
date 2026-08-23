# Edge Current hygiene — 2026-08-23

**Branch:** `cursor/edge-current-hygiene-e929` → `deploy-vercel`  
**Baseline:** post-#287 (`8519dfb`) snapshot Current restore  
**Scope:** Current on Edge must look like a posted NFL book line, or it is `—`. No new Odds key. No KEI / model / Fantasy. No invented nearby lines.

## Problem

#287 filled Current from latest-per-book `odds_snapshots` via **AVG**. Live Railway Week 1 (2026-08-23) painted 16/16 numeric Currents, but 14/16 spreads were non-book tenths (`−3.58`, `2.58`, `0.17`, `−4.75`, …). Action against those numbers is worse than honest empty.

## Fix

1. **Validators** (`nfl_market_line_hygiene` + web twin) before paint. Spread: half-point, `|n|` in `[0.5, 20.5]`, reject 0 / probs / ML / totals. Total: `[30, 65]`, `.0` or `.5`. ML: American `|n|≥100` (decimal ML only in the ML column; 3.8/2.4 never). Fail → `null`. **Never round** `−3.58` → `−3.5`.
2. **Consensus is mode of validator-passing latest-per-book samples**, not AVG. SQL `array_agg` replaces `AVG(spread_home)`. Tie → smaller abs, then more negative. If no sample passes → `—`.
3. Same sanitizer on live `_extract_book_market_prices`, snapshot merge, and the web overlay / Action path. Invalid overlay (`+3.8`) is ignored. Action only when painted Current is valid.
4. **Open unchanged.** Still no Open→Current copy.
5. Diagnostics: `diagnostics.current_hygiene` (`kept_*`, `rejected_*`, `reject_reasons`, `snapshot_*_rejected`) plus `nfl_current_hygiene …` log line.

## Examples rejected (live Week 1 AVG)

| Game | AVG Current | Reason | After |
|------|-------------|--------|-------|
| **NE@SEA** | −3.58 / 44.42 | `not_half_point` | **— / —** (Open stays −3.5 / 44.5) |
| **CLE@JAX** | −7.42 / 40.5 | spread `not_half_point` | **— / 40.5** |
| BUF@HOU | 0.17 / 44.5 | `looks_like_probability` | **— / 44.5** |
| ATL@PIT | −3.08 / 42.25 | `not_half_point` | **— / —** |
| WAS@PHI | −4.75 / 46.75 | `not_half_point` | **— / —** |
| GB@MIN | −0.92 / 45.08 | spread looks like a prob | **— / —** |
| 3.8 / 2.4 class | — | `not_half_point` / `looks_like_spread` | **—** |

Mode recovery (when samples exist): `[-3.5, -4.0, -3.5]` → **−3.5** (posted line). Scalar `−3.58` is **not** repaired.

## Before → after (Week 1 REG, 16 games)

Live `/nfl/fair-lines?season=2026&days_ahead=200` **before** this change (`current_source=odds_snapshots`, AVG):

| | Spread Current | Total Current | Open |
|--|--|--|--|
| **Before** | **16/16 numeric, 2 plausible** (SF@LAR, TB@CIN); 14 garbage tenths | **16/16 numeric, 7 plausible** | **16/16** posted half-points |
| **After (fail-closed on those AVGs)** | **2 kept / 14 —** | **7 kept / 9 —** | **16/16 unchanged** |
| **After (mode of posted samples)** | A posted book line when any latest-per-book sample passes; else — | same | unchanged |

Action: only when Current is valid. NE@SEA / CLE@JAX on the AVG snapshot are **—** (Open still real). If Railway samples are `−3.5`/`−7.5` (typical), mode paints those instead of tenths — still never `−3.58`.

Copied-Open: `false`. Empty preferred over fake precision.

## Smell tests

1. No 3.8 / 2.4 / −3.58 on the board — **fail-closed**.
2. NE@SEA / CLE@JAX: real-looking Current if a posted sample exists, else **—** + Action Edge **—**.
3. Open is not written into a rejected Current hole.

## Remaining

- Live Odds API is still 401. Hygiene does not mint a key. Snapshot Current is as-of last persist, now shape-checked.
- Mode needs per-book samples in `odds_snapshots`. If ingest stored only an average, that scalar still fails closed.
- Re-smoke production `/edge-board/nfl` after Railway picks up model-service + Vercel web overlay.
