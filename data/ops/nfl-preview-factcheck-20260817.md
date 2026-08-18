# NFL preview market fact-check — 2026-08-17

**Editor:** Riley Nash  
**Live board:** DraftKings via RotoWire (August 2026)  
**Model SoT:** `nfl-preseason-sim-2026-20260813T214500Z` (N=100000) `expected_wins`  
**Status:** Mistakes reported below → fixed in same pass → re-audit **0 mismatches**.

## Mistake report (desk owner)

Found **15** primary-market mismatches (Δ ≥ 0.5) before fix. User catch: Rams previewed at **9.5**; live DK is **11.5**.

| Team | Stated (wrong) | Live DK | Δ | Model E[wins] | Post-fix lean |
|------|---------------:|--------:|--:|--------------:|----------------|
| LAR | 9.5 | 11.5 | −2.0 | 11.08 | **Pass** (thin vs 11.5; kill old Over-9.5) |
| NYG | 5.5 | 7.5 | −2.0 | 7.02 | **Pass** |
| SEA | 8.5 | 10.5 | −2.0 | 10.79 | **Pass** |
| BAL | 10.5 | 11.5 | −1.0 | 8.97 | **Pass** (Model↔market conflict) |
| CAR | 6.5 | 7.5 | −1.0 | 6.47 | **Pass** / soft Under scrutiny |
| DAL | 8.5 | 9.5 | −1.0 | 7.10 | **Pass** (Model↔market conflict) |
| DET | 9.5 | 10.5 | −1.0 | 10.71 | **Pass** |
| JAX | 7.5 | 8.5 | −1.0 | 9.76 | Soft **Over 8.5** if juice OK (conf ≤2) |
| MIN | 7.5 | 8.5 | −1.0 | 8.38 | **Pass** |
| NE | 9.5 | 10.5 | −1.0 | 9.98 | **Pass** |
| NO | 6.5 | 7.5 | −1.0 | 8.96 | Soft **Over 7.5** if juice OK (conf ≤2) |
| SF | 9.5 | 10.5 | −1.0 | 8.53 | **Pass** (Model↔market conflict) |
| TEN | 5.5 | 6.5 | −1.0 | 5.86 | **Pass** / soft Under scrutiny |
| IND | 8.5 | 7.5 | +1.0 | 10.30 | **Pass** (Model↔market conflict) |
| WAS | 8.5 | 7.5 | +1.0 | 6.32 | **Pass** / soft Under scrutiny |

## Also stamped (already matched live)

ARI, ATL, BUF, CHI, CIN, CLE, DEN, GB, HOU, KC, LAC, LV, MIA, NYJ, PHI, PIT, TB — added Editor market fact-check + Model SoT stamp; Handicapper notes aligned to Model E[wins] where updated.

## Fixes applied

- Primary win total corrected in title / Market line / Handicapper’s Note / Monday Bottom line for all mismatches.
- Leans recalibrated with Edge Threshold Discipline against Model SoT (thin gaps and material conflicts → **Pass**).
- Every preview stamped: `Market fact-check: August 17, 2026 · DraftKings via RotoWire · Editor Riley Nash`.

## New employee / cadence

- **Riley Nash — Editor** (`riley-nash.md`)
- Weekly SOP: `docs/writers/EDITOR_WEEKLY_FACTCHECK.md`
- Script: `python scripts/writers/preview-market-factcheck.py --as-of YYYY-MM-DD --write-ops`
- Wired into Writer Team OS (`.cursor/rules/ai-writer-team.mdc`)

## Re-audit

```text
Fact-check 2026-08-17: 0 mismatches / 32 teams
```
