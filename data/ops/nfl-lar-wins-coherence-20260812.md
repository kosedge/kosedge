# LAR 9.7 wins — stuck vs schedule vs path bug — 2026-08-12

**Status:** Fixed (path-align) · not a cache bug · not a hard-schedule story  
**Branch:** `feat/nfl-lar-wins-path-align` → `deploy-vercel`  
**Run:** `nfl-preseason-sim-2026-20260809T165350Z` (same `active_run_id`; wins/playoff/SB rewritten from one complementary MC)

## One sentence

LAR 9.7 was the locked PF/PA Pythagorean pin — not a frozen UI cache and not a hard slate — while playoff ~81% came from the same files’ 7-seed MC after `hp/(hp+ap)` renormalization, which already gave LAR and CHI ~10.8 path wins; we now publish that game-graph number (LAR **11.08**).

## Trace — what emitted 9.7

| Layer | Value | Source |
|-------|------:|--------|
| Pointer | `nfl-preseason-sim-2026-20260809T165350Z` | `data/ops/nfl-web-launch-bundle.json` (`locked_snapshot: true`) |
| Board E[wins] | **9.6938** | `team_regular_season_outcomes.csv` ← PF/PA Pythagorean + stretch + #201 pile-break |
| Week-rate Σ | 9.6938 | `team_week_win_rates.json` after #196 independent rescale to board |
| Path E[wins] (pre-fix) | **10.82** | complementary `hp/(hp+ap)` on the wall chart (not displayed) |
| Playoff / Div / SB | 80.88% / 34.0% / **6.88%** | 7-seed + strength-bracket MC on those rates — **same CSV row** |
| Model PR | **+5.13 (#1)** | Power desk Method B (`latest.json`) — different surface |

**6.88 is Super Bowl %** (`super_bowl_win_prob` 0.0688) on the same outcomes row as 9.6938. Not Model PR, not a second run.

**Stuck?** Same 9.6938 on every look because the bundle is locked and #201 explicitly did not touch LAR wins. A fresh hierarchical / PR-slate calc was already ~11.1–11.4. Not a CDN/cache miss.

## Schedule does not explain 9.7 vs CHI 13.9

Model PR + 2026 wall chart, logistic WP with HFA +2.5 / spread 15:

| Team | Model PR (rank) | SOS (mean opp PR+HFA, higher=harder) | E[wins] vs avg slate | E[wins] vs actual slate | Schedule tax |
|------|----------------:|-------------------------------------:|---------------------:|------------------------:|-------------:|
| **LAR** | **+5.13 (#1)** | 0.19 (13th-hardest) | 11.67 | 11.39 | **−0.28** |
| CHI | +0.74 (#13) | **0.53 (4th-hardest)** | 9.06 | 8.59 | **−0.47** |
| BUF | +3.56 (#4) | 0.03 | 10.60 | 10.50 | −0.10 |
| JAX | +2.65 (#8) | 0.08 | 10.06 | 10.04 | −0.02 |

CHI’s slate is **harder** than LAR’s. Schedule predicts LAR **ahead** of CHI by ~2.8 wins, not 4.2 behind.

PF/PA on the production stack was inverted vs Model PR (not opponent-adjusted SOS):

| Team | PF | PA | PD | Board wins (pre-fix) | Def PR |
|------|---:|---:|---:|---------------------:|-------:|
| CHI | 411.7 | **329.3** | +82.5 | 13.93 | −0.21 |
| LAR | 440.9 | **421.9** | +19.0 | 9.69 | +1.48 |

Two PA piles (~329 vs ~422), not a Rams-specific schedule tax. Do not hand-set LAR to 12 because Power is #1; the bug was publishing Pythagorean stretch instead of realizable path wins.

## Playoff coherence (pre-fix)

Same run, two statistics:

| Team | Board E[wins] (PF/PA) | Path E[wins] `hp/(hp+ap)` | Playoff % |
|------|----------------------:|--------------------------:|----------:|
| CHI | 13.93 | **10.84** | 82.9% |
| JAX | 13.65 | 10.97 | 80.8% |
| BUF | 13.38 | 11.58 | 89.4% |
| **LAR** | **9.69** | **10.82** | **80.9%** |

LAR was not making the playoffs as a 9-win team in-path. The MC already had LAR ~10.8. CHI’s 13.9 never showed up in-path either (0.98 week rates crushed against other inflated rates). NFC West cliff (SEA/LAR vs SF/ARI) still supports a high wild-card rate; the 13-win vs 9.7 playoff tie was the dual statistic, not a 7-seed rule bug.

## Fix (lowest layer — no franchise override)

1. After #196 rescale, **project week rates onto the complementary wall-chart graph** (iterate until Σp ≈ pairwise E[wins], tol 0.35).
2. Run 7-seed + SB MC on those rates.
3. **Publish path-MC `expected_wins` + win_dist from the same draws** (`rewrite_expected_wins=True`).
4. Leave PF/PA scoring budgets on the production stack (honesty: scoring ≠ path wins until a re-finalize rebuilds PA from Model PR).

Converged in 4 iterations (max |Σp − pairwise| 3.08 → 0.29).

## Before / after — same `run_id`

| Team | Wins before | Wins after | Playoff before | Playoff after | SB before | SB after |
|------|------------:|-----------:|---------------:|--------------:|----------:|---------:|
| **LAR** | 9.69 | **11.08** | 80.9% | **85.5%** | **6.88%** | **11.16%** |
| CHI | 13.93 | 8.78 | 82.9% | 43.9% | 7.72% | 2.28% |
| JAX | 13.65 | 9.91 | 80.8% | 65.6% | 6.92% | 4.46% |
| BUF | 13.38 | 10.42 | 89.4% | 76.8% | 10.76% | 7.26% |
| SEA | 13.11 | 10.81 | 90.3% | 80.2% | 13.16% | 10.04% |
| DET | 7.05 | 10.49 | 53.5% | 75.9% | 2.00% | 7.72% |

LAR 11.08 sits next to PR-slate 11.39 / hierarchical ~11.11. CHI 8.78 sits next to PR-slate 8.59. Power #1 with a slightly hard slate lands under the old 13-win pile — that is now the defendable sentence.

## Histogram (shape after #201 vs path-align)

| Band | After #201 (C1–C6 green) | After path-align |
|------|-------------------------:|-----------------:|
| ≤6 | 10 | **3** |
| 7–9 | 11 | **20** |
| 10–11 | 4 | **9** |
| ≥12 | 7 (6 at ≥12.5) | **0** |
| Ceiling cluster (0.35 of max) | 2 | **2** |

C1–C6 + STRENGTH_ALIGN + I1–I8 still **PASS**. Top-heavy 13.9/13.7/13.4 cluster is gone without hand-edits. PF/PA piles remain on the scoring CSV (next re-finalize item, not this PR).

## Gates

```
C1–C6 PASS · CEILING_PILE PASS (2) · STRENGTH_ALIGN PASS · I1–I8 PASS
Σ wins 272 · Σ AFC/NFC playoff 7/7 · Σ SB 1 · contradiction_flags []
```

## Non-goals (held)

- Do not set LAR to 12 because Power is #1
- Do not UI-normalize playoff %
- Do not rebuild PF/PA from Model PR in this pass (scoring dual-path documented, not silently overwritten)
