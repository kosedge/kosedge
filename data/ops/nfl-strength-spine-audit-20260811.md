# NFL Strength Spine Audit — all 32 — 2026-08-11

**Bundle:** `nfl-preseason-sim-2026-20260809T165350Z` (published / pointer active)  
**Power desk:** `data/ops/nfl-power-ratings-desk/latest.json` (Method B, #198, as_of_week 0)  
**#199 merge:** `ec0e8ccc56345f5e25b941bb368689a960faa1d3`  
**Live:** `https://www.kosedge.com/api/ping` → ok; season-engine status → `nfl-season-engine-v1.27-kicker-layer`

## Verdict

| Check | Result |
|-------|--------|
| Dual-path (board vs week-rate Σ vs win_dist.mean) | **32/32 clean** (±0.35) |
| Raw `LA` keys (outcomes / rates / dist / defense / players) | **None** — product id `LAR` only |
| Defense `expected_wins` vs board | **32/32 match** |
| Player season totals present per franchise | **32/32** (pass/rush/rec columns populated) |
| Truth sums | Σ wins=272, Σ playoff=14, Σ SB=1 |
| Dual-path bug requiring code fix | **None** |

**Soft dual-path class (pre-fix LAR/DET):** closed. Remaining DET note is division-context contradiction scanner noise, not a second strength path.

## Method

Compared, per canonical team:

1. Board `expected_wins` (`team_regular_season_outcomes.csv`)
2. Σ week win rates (`team_week_win_rates.json`)
3. `win_dist.mean` (`team_win_distributions.json`)
4. Playoff % / SB % (same outcomes board)
5. Model PR / Active PR (#198 desk)
6. Cheap production: defense PF/PA + `expected_wins`; player `pass_yards_total` / `rush_yards_total` / `receiving_yards_total` team sums

Flags (dual-path / id):

- `|board − rate| > 0.35` or `|board − dist.mean| > 0.35`
- Raw `LA` anywhere
- Wins vs SB incongruence of the dual-path class (`high_wins_thin_sb` / `high_playoff_thin_sb` after path-bracket SB)

Report-only (not dual-path):

- `flag_wins_playoff_sb_contradictions` (`low_wins_high_playoff`, etc.)
- Model PR rank ≠ win-pile rank (Method B margin vs soft-pile W/L)

## Dual-path / id results

| Metric | Flags |
|--------|-------|
| rate ≠ board | **[]** |
| win_dist.mean ≠ board | **[]** |
| raw `LA` | **[]** |
| defense ew ≠ board | **[]** |

## Contradiction scanner (report-only)

| Team | E[wins] | Playoff % | SB % | Reason | Dual-path? |
|------|--------:|----------:|-----:|--------|------------|
| **DET** | 7.05 | 57.7% | 2.19% | `low_wins_high_playoff` | **No** — board/rate/dist aligned at ~7.05; NFC North under CHI’s 12.7 pile (same note as `nfl-strength-coherence-det-20260811.md`) |

No `high_wins_thin_sb` / `high_playoff_thin_sb` / `high_wins_low_playoff` flags.

## Model PR vs board wins (Method B — not a path split)

Top-5 by board wins: BUF, SEA, CHI, JAX, NE  
Top-5 by Model PR: LAR, SEA, DEN, BUF, HOU  
Overlap: BUF, SEA

LAR leads Model PR (~5.13) with ~9.69 board wins and healthy playoff/SB (83% / 7.1%) — Method B points/margin spine, not a second win path. Soft-pile win histogram remains polarized (≤5:6, 5–7:10, 7–10:5, 10–12:1, ≥12:10); middle-class thinning is a known wait item, not an audit fail.

## Full 32 (board / rate / dist / playoff / SB / Model PR)

| Team | Board | Rate Σ | Dist μ | Δ rate | Δ dist | PO% | SB% | Model PR | Path |
|------|------:|-------:|-------:|-------:|-------:|----:|----:|---------:|------|
| ARI | 4.59 | 4.59 | 4.59 | 0.00 | +0.01 | 3.9 | 0.0 | -2.71 | OK |
| ATL | 12.65 | 12.65 | 12.66 | 0.00 | +0.01 | 85.7 | 7.7 | 0.52 | OK |
| BAL | 12.55 | 12.55 | 12.56 | 0.00 | +0.01 | 77.4 | 5.5 | 0.12 | OK |
| BUF | 12.83 | 12.83 | 12.83 | 0.00 | +0.00 | 85.2 | 9.1 | 3.56 | OK |
| CAR | 4.63 | 4.63 | 4.63 | 0.00 | -0.00 | 4.7 | 0.0 | -2.75 | OK |
| CHI | 12.73 | 12.73 | 12.70 | 0.00 | -0.02 | 78.8 | 5.8 | 0.74 | OK |
| CIN | 8.90 | 8.90 | 8.90 | 0.00 | +0.00 | 33.3 | 0.6 | -3.16 | OK |
| CLE | 5.91 | 5.91 | 5.91 | 0.00 | -0.00 | 15.4 | 0.2 | -0.93 | OK |
| DAL | 9.34 | 9.34 | 9.33 | 0.00 | -0.01 | 35.3 | 0.7 | -2.69 | OK |
| DEN | 8.80 | 8.80 | 8.80 | 0.00 | +0.00 | 66.2 | 3.6 | 4.00 | OK |
| DET | 7.05 | 7.05 | 7.05 | 0.00 | +0.01 | 57.7 | 2.2 | 3.03 | OK* |
| GB | 6.73 | 6.73 | 6.72 | 0.00 | -0.01 | 35.3 | 0.7 | 2.05 | OK |
| HOU | 12.58 | 12.58 | 12.60 | 0.00 | +0.01 | 79.6 | 7.3 | 3.34 | OK |
| IND | 11.66 | 11.66 | 11.67 | 0.00 | +0.01 | 73.4 | 5.0 | 2.49 | OK |
| JAX | 12.72 | 12.72 | 12.71 | 0.00 | -0.01 | 73.3 | 5.3 | 2.65 | OK |
| KC | 12.59 | 12.59 | 12.61 | 0.00 | +0.02 | 78.9 | 6.4 | 1.67 | OK |
| LAC | 5.87 | 5.87 | 5.87 | 0.00 | -0.01 | 14.2 | 0.2 | 0.47 | OK |
| LAR | 9.69 | 9.69 | 9.73 | 0.00 | +0.04 | 83.1 | 7.1 | 5.13 | OK |
| LV | 4.49 | 4.49 | 4.48 | 0.00 | -0.01 | 2.3 | 0.0 | -3.90 | OK |
| MIA | 4.40 | 4.40 | 4.40 | 0.00 | +0.01 | 1.6 | 0.0 | -4.12 | OK |
| MIN | 6.02 | 6.02 | 6.03 | 0.00 | +0.02 | 20.7 | 0.3 | -0.13 | OK |
| NE | 12.66 | 12.66 | 12.66 | 0.00 | -0.00 | 82.9 | 7.9 | 2.53 | OK |
| NO | 6.17 | 6.17 | 6.15 | 0.00 | -0.02 | 29.5 | 0.5 | -0.30 | OK |
| NYG | 6.69 | 6.69 | 6.69 | 0.00 | +0.00 | 17.4 | 0.2 | -2.87 | OK |
| NYJ | 4.54 | 4.54 | 4.55 | 0.00 | +0.01 | 1.8 | 0.0 | -7.68 | OK |
| PHI | 12.63 | 12.63 | 12.61 | 0.00 | -0.01 | 88.3 | 9.3 | 2.94 | OK |
| PIT | 6.15 | 6.15 | 6.14 | 0.00 | -0.01 | 13.5 | 0.2 | -0.29 | OK |
| SEA | 12.75 | 12.75 | 12.75 | 0.00 | +0.00 | 91.1 | 12.9 | 4.46 | OK |
| SF | 6.87 | 6.87 | 6.86 | 0.00 | -0.01 | 30.0 | 0.6 | -0.03 | OK |
| TB | 6.81 | 6.81 | 6.80 | 0.00 | -0.01 | 32.6 | 0.6 | -0.13 | OK |
| TEN | 4.44 | 4.44 | 4.46 | 0.00 | +0.01 | 1.1 | 0.0 | -5.14 | OK |
| WAS | 5.57 | 5.57 | 5.57 | 0.00 | +0.01 | 5.8 | 0.0 | -2.90 | OK |

\*DET: scanner `low_wins_high_playoff` only; strength spine aligned.

## Production spot-check (cheap)

| Team | Board ew | Def ew | PF / PA | Player pass / rush / rec yds |
|------|---------:|-------:|---------|------------------------------|
| LAR | 9.69 | 9.69 | 440.9 / 421.9 | 4861 / 1744 / 4861 |
| DET | 7.05 | 7.05 | 320.2 / 328.5 | 4406 / 1655 / 4406 |
| BUF | 12.83 | 12.83 | 410.4 / 329.5 | 3821 / 2714 / 3821 |
| SEA | 12.75 | 12.75 | 410.9 / 330.1 | 4259 / 2639 / 4259 |
| NYJ | 4.54 | 4.54 | 310.3 / 422.5 | 3193 / 1833 / 3193 |

No LA/LAR production fork.

## Summary counts

- **Clean (dual-path / id):** 32  
- **Dual-path bugs left:** 0  
- **Report-only flags:** 1 (DET division context)

See also: `nfl-enterprise-spine-lock-20260811.md`, `nfl-strength-coherence-lar-20260811.md`, `nfl-strength-coherence-det-20260811.md`.
