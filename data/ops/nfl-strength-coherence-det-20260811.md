# NFL Team Strength Coherence — DET win_dist dual path — 2026-08-11

Branch: `feat/nfl-strength-coherence-det` → `deploy-vercel`  
Depends on: #196 LAR strength coherence (`f3a0b8c3948e03373a39a26a5782f661bdbedf65`)  
Locked board: `nfl-preseason-sim-2026-20260809T165350Z`

## Root cause (DET)

#196 aligned **week rates** + playoff/SB to soft-pile board `expected_wins`, but left
`team_win_distributions.json` on the **hierarchical MC** path (id canonicalize only).

| Surface | DET strength | Path |
|---------|-------------:|------|
| Board / defense / Power (E[wins]) | **7.0459** | Soft-pile / production PF/PA |
| Aligned week rates Σ | **7.0459** | Post-#196 rescale |
| Playoff / SB (Truth Layer) | 57.7% / 2.19% | From aligned rates |
| **Season Model / Futures win_dist.mean** | **10.5716** | Stale hierarchical hist |

Same dual-path class as LAR (board vs hierarchical), but the leftover artifact for DET
was **win distributions**, not week rates. Healthy peer SF (~6.87 board) also had a
stale dist μ (~8.60); DET’s gap (+3.53) was the largest among NFC North and the
only post-#196 `low_wins_high_playoff` contradiction flag.

Amplifier: `leaders.json` still labeled some Rams rows `LA` (canonicalized here).

## Fix

1. Rebuild `team_win_distributions` from **aligned week-rate marginal Bernoullis**
   so `mean ≈ Σ week p = board expected_wins` (do not use schedule-renormalized MC
   for dist means — that drifts off Σ p).
2. Sync outcome `wins_p10` / `wins_p90` from the rebuilt histograms.
3. Canonicalize `LA`→`LAR` on leaders rows.
4. Extend `STRENGTH_ALIGN` to require `win_dist.mean ≈ board` (±0.35) as well as
   week-rate Σ.

Scripts: `scripts/nfl/apply_nfl_strength_coherence.py`,
`build_win_distributions_from_marginal_rates` in `nfl_playoff_from_week_rates.py`.

## Before / after — DET

| Metric | Before | After |
|--------|-------:|------:|
| Expected wins (board / production) | 7.0459 | **7.0459** (unchanged) |
| Week-rate Σ wins | 7.0459 | **7.0459** |
| **win_dist.mean** (Season Model path) | **10.5716** | **7.0523** |
| Playoff % | 57.66% | **57.66%** |
| Division title % | 27.03% | **27.03%** |
| Super Bowl % | 2.185% | **2.185%** |
| Defense PF / PA | 320.2 / 328.5 | unchanged (production path) |
| Goff pass yards | 4114 | unchanged (same budget path) |

Playoff stays elevated vs SF/TB peers at ~7 wins because NFC North under CHI’s 12.7
soft pile is weak — report-only `low_wins_high_playoff`, **not** an eye-test win edit.

## Before / after — LAR (still healthy)

| Metric | Value |
|--------|------:|
| Expected wins | 9.6938 |
| win_dist.mean | **9.7311** (was 11.1074 hierarchical) |
| Playoff % | 83.14% |
| SB % | 7.08% |

## Invariant sums (after)

| Check | Value |
|-------|------:|
| Σ expected wins | 272.000 |
| Σ SB | 1.000 |
| Σ AFC playoff | 7.000 |
| Σ NFC playoff | 7.000 |
| Teams (canonical) | 32 (`LAR`, no `LA`) |
| STRENGTH_ALIGN (rates + win_dist) | PASS |
| win_dist_mismatch_flags | **[]** |

## Production linkage

- Soft-pile finalize sets team pass/rush budgets, PF/PA, and `expected_wins` together.
- DET player yards/TDs (Goff ~4114 pass, Gibbs ~1026 rush, St. Brown ~1118 rec) remain
  on that budget path; team key **DET**.
- Week rates were already rescaled to board wins in #196; this PR points Season Model /
  Futures histograms at the **same** production strength.

Smoke: Power Ratings (board E[wins]), Futures/Season Model (`win_dist.mean`), and
Truth Layer playoff/SB all tell the 7.05-win DET story; LAR remains coherent.

## Tests

`services/model-service/tests/test_nfl_strength_coherence.py` — DET win_dist flag,
histogram rebuild helpers, percentile sync, prior LAR coverage.

## Non-goals (held)

- Hand-setting DET wins or SB%
- Smoothing soft-pile polarization
- Redesigning Power Ratings away from wins
- Path A player-yard sculpture / tag policy
