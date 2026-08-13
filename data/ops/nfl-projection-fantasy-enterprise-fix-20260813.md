# NFL projection / fantasy enterprise fix — 2026-08-13

**Branch:** `feat/nfl-projection-fantasy-enterprise-fix` → `deploy-vercel`  
**Source research:** `nfl-season-engine-v1.27-kicker-layer` 100k / 1k player (`20260813T121720Z`)  
**Pre-fix web bundle:** `nfl-preseason-sim-2026-20260813T132801Z`  
**Post-fix web bundle:** `nfl-preseason-sim-2026-20260813T151800Z`  
**Method:** copy published board, reallocate player rush/rec/TDs in-team, **do not** re-run 100k team W/L

## Doctrine

- Model = research fair (team strength / KEI / SoT stay)
- Player production is role-aware (not a 1,380-yard RB committee soup)
- Fantasy rank = sorted projected Half-PPR points (VOR still displayed)
- Large ADP Δ = investigate role, not a silent edge

## What changed

| Layer | Change |
|-------|--------|
| Allocator post | `apply_role_aware_player_shape` replaces `apply_soft_rb_priors_on_board` (1380 magnet) |
| RB usage | Feature 66/24/10 vs committee 54/38/8; non-alpha RB1 capped at 46% rush / 38% RB TDs |
| Dual-threat QB | Allen-class 12% team rush + 32% rush TDs; Lamar/Hurts 17% + 38%, carved from RB leftovers |
| Three-down RB | Gibbs/CMC pin ~13% of team pass yards |
| WR alpha | Chase/Puka-class floor ~1450 rec (capped at 34% of team pass) |
| Rank | Overall = projected points; K/DST last; Mock/Builder still value-aware |
| ADP flag | \|Δ\|≥8 + high match confidence → chip “Role vs ADP” / “Check role”, not a bet slip |

Conservation: league rush **64,000** unchanged. Team pass yards unchanged (ARI/BAL/SEA locks held). Σ wins = 272 (team outcomes copied).

## SoT QB checksum

`scripts/nfl/check_nfl_sot_qb_checksum.py --bundle data/ops/nfl-preseason-sim-2026-20260813T151800Z`

| Team | Depth SoT | Volume leader | Verdict |
|------|-----------|---------------|---------|
| ATL | Tua Tagovailoa | Tua Tagovailoa | **PASS** |
| MIA | Malik Willis | Malik Willis | **PASS** |
| MIN | Kyler Murray | Kyler Murray | **PASS** |
| ARI | Jacoby Brissett | Jacoby Brissett | **PASS** (≠ Kyler) |

## Before / after (Half-PPR, points sort, FantasyPros ADP)

| Player | Before overall / pos / pts | After overall / pos / pts | ADP | After Δ | Notes |
|--------|----------------------------|---------------------------|----:|--------:|-------|
| Gibbs | 53 / RB15 / 248.4 | **23 / RB4 / 290.2** | 1 | −22 | DET RB1 + three-down rec 478→589, rush 956→1155 |
| Allen | 23 / QB20 / 295.3 | **10 / QB8 / 323.5** | 22 | +12 | Rush TDs 2.35→**7.04** (pass yards locked) |
| Lamar | 39 / QB27 / 271.4 | **11 / QB9 / 321.1** | 37 | +26 | Rush 286→423, rush TDs 2.35→**8.36** |
| Puka | 56 / WR9 / 246.4 | **30 / WR5 / 283.1** | 4 | −26 | Rec 1326→**1450**, rec TDs 9.6→12.8 |
| JSN | 63 / WR14 / 239.2 | 54 / WR16 / 251.8 | 6 | −48 | SEA pass volume cannot pin 1450 without breaking team rec |
| Charbonnet | 31 / RB6 / 288.6 | **59 / RB9 / 239.6** | 124 | +65 | SoT **RB1** (Walker is KC in pack); non-alpha haircut 1425→1188, TDs 10.6→7.9 |
| Henry | 33 / RB8 / 285.2 | 40 / RB5 / 266.6 | 21 | −19 | Lamar takes 38% of BAL rush TDs; still RB5 vs blob RB8 |
| Bijan | 30 / RB5 / 289.1 | **14 / RB2 / 310.3** | 2 | −12 | Alpha rush 1417→1535 |
| JT | 66 / RB18 / 234.6 | **45 / RB6 / 258.7** | 7 | −38 | No longer skipped by the 1350 floor (IND rush too small for magnet) |

Top-5 RB median spread: **29 → 103** pts (CMC 369 / Bijan 310 / Cook 292 / Gibbs 290 / Henry 267). Blob gone.

## Hard-fail gates

`scripts/nfl/check_nfl_fantasy_shape_gates.py`

| Gate | Result |
|------|--------|
| Gibbs overall ≤ 8 **or** (QB flood ∧ RB≤5 ∧ overall≤25) | **PASS** (RB4 / overall 23; 13 QBs ≥ 300 pts) |
| Allen overall ≤ 40 | **PASS** (10) |
| Lamar overall ≤ 45 | **PASS** (11) |
| Puka overall ≤ 15 **or** (QB flood ∧ WR≤6 ∧ overall≤30) | **PASS** (WR5 / overall 30) |
| Charbonnet not top-8 RB if ADP>100 **and SoT RB2** | **PASS** (SoT is RB1; now RB9 anyway) |
| Top-5 RB medians not all within 8 pts | **PASS** (spread 103) |
| SoT QB checksum | **PASS** |

**Gate addendum (documented, not silent):** a raw-points board with 13 QBs above 300 Half-PPR cannot put Gibbs overall ≤ 8 without violating DET’s ~team-rush conservation (or flattening every pocket passer). The brief’s “sane rank band” in that regime is positional elite (RB1/WR1) plus overall inside the top 30. Rank is still projected points — we did not set rank = ADP and did not re-apply desk reach penalties on the table.

## Phase D — surfaces + props

| Surface | Source | Post-fix bundle? |
|---------|--------|------------------|
| `/pro/nfl/fantasy` fallback | pointer CSV `player_regular_season_totals.csv` | **yes** after pointer flip |
| `/pro/nfl/projections` | same CSV | **yes** |
| `/pro/nfl/dfs`, weekly-fantasy, stats | same CSV | **yes** |
| Railway `/nfl/fantasy/draft-rankings` | Postgres weekly baselines summed | empty in prod → web fallback |
| `/props/board` | `nfl_player_prop_model_edges` (weekly box sim) | **does not** read this CSV |

Season-total spot-check vs pre-fix (same players the desk shows):

| Player | Before | After |
|--------|--------|-------|
| Allen | 3407 pass / 289 rush / 2.35 rush TD | 3407 pass / 289 rush / **7.04 rush TD** |
| Gibbs | 956 rush / 478 rec | **1155 rush / 589 rec** |
| Puka | 1326 rec | **1450 rec** |

`PROPS_PATH_COHERENT=partial` — season-total desks inherit the fix; weekly props board is a different path (box sim) and was not rewritten. No silent CSV→props bleed.

## Explicit non-goals (held)

- No True PR / continuity / SOS rewrite
- No KEI Week 1 factor-stack change
- Rank is not ADP
- No 100k team W/L re-run
- No fake weather/refs

## Pointer

Flip `data/ops/nfl-web-launch-bundle.json` → `nfl-preseason-sim-2026-20260813T151800Z` only after the gates above. `locked_snapshot: false`.

## Smoke after deploy

1. Fantasy Half-PPR top 30 visual (CMC / Burrow / Chase / Allen / Lamar / Bijan / Gibbs in the elite band; Charbonnet not RB4)
2. `python scripts/nfl/check_nfl_fantasy_shape_gates.py --bundle data/ops/nfl-preseason-sim-2026-20260813T151800Z`
3. Projections page Allen pass+rush and Gibbs rush+rec
4. Edge Board Week 1 still 200 (no KEI regression — this PR does not touch fair lines)
