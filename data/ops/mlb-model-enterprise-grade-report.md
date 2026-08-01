# MLB Model — Enterprise Grade Report

**Generated:** 2026-08-01  
**Model version:** `mlb-v1-pa-sim`  
**Focus:** Moneyline edgeboard + model/props health  
**Evidence base:** `data/ops/mlb-enterprise-holdout/` (sprint + latest quality / CLV / walkforward)

## Executive status

MLB is a **moneyline** sport. The public Edge Board now shows **Moneyline + Total** (not run line ±1.5). KEIMLB merges fair home/away Americans and `fg_home_win_prob`; ML edge is **model home win prob − market no-vig home**, displayed in **percentage points** (same LEAN ≥1.0 / PLAY ≥2.5 cut as other sports’ point edges).

Model health is **split**: run line and totals show useful closing-line value; moneyline calibration sits near the coin-flip Brier floor and fails the enterprise Brier gate. Props remain **research_only** with stake marketing blocked until unused-holdout clearance.

**No model-code nudge shipped in this change** — ML Brier/CLV do not justify a cosmetic reprice. Improvements below are evidence-based recommendations.

## Edgeboard change (shipped)

| Before | After |
|--------|--------|
| Odds `markets=spreads,totals` | Odds `markets=h2h,totals` for MLB |
| Market label `Spread` (canonical ±1.5) | Market label `Moneyline` |
| KEI = fair run-line home | KEI = fair home/away ML + `homeWinProb` |
| Edge = spread-point gap (with American flip) | Edge = no-vig **prob points** (no flip) |
| UI “Spread edge” | UI “ML edge” / Open·Best **ML** |

Wiring matches `/mlb/edges/today` semantics (model − no-vig market), computed client-side from the best-away book’s two-way prices so the board does not require an extra edges API hop.

## Moneyline health

| Metric | Value | Gate / note |
|--------|-------|-------------|
| Walkforward Brier (base) | **0.249–0.252** | Gate **0.24** → **fail** (`latest_report` / sprint) |
| Calibrated Brier | ~0.252–0.255 | Calibration barely moves Brier (+1.5e-5 sprint; sometimes worse) |
| ECE | **~0.025** | Decent bin calibration; still not stake-ready on Brier |
| Avg ML CLV | **~+0.023–0.024** | Positive but weak vs RL/totals |
| Board ML coverage | **100%** | Fair ML always present when projections exist |

**Grade: C+** — Liveable for research tags and desk display; not yet a stake-marketing moneyline product. Near-0.25 Brier means win probs are only marginally sharper than a well-priced market prior.

## Run line health

| Metric | Value | Note |
|--------|-------|------|
| Avg spread/run-line CLV | **~+0.19–0.23** | Stronger than ML |
| DK-first firewall | Active | Alt spreads dropped from CLV |
| Canonical band | ±1.5 (max abs 2.5) | Unchanged for Fair Lines / CLV |

**Grade: B** — Best “side” signal in the stack today. Remains on Fair Lines / Run Line desk; removed from public Edge Board because MLB bettors price ML first.

## Totals health

| Metric | Value | Gate / note |
|--------|-------|-------------|
| Avg total CLV | **~+0.25–0.33** | Strongest CLV family |
| MAE total runs | **~3.35–3.58** | Gate **3.5** — borderline / often **fail** |
| Total coverage | **100%** on board health | |

**Grade: B** — CLV is the bright spot; absolute level (MAE) still needs work before aggressive Over/Under staking.

## Props posture

| Item | Status |
|------|--------|
| `props_play_stake_eligible` | **false** |
| Research / publish | **research_only** |
| Stake marketing | Blocked until unused-holdout pass |
| Unused holdout | Frozen (`2026-07-18`–`2026-08-10`, 23 dates) — **not yet graded for stake** |

**Grade: C** — Correctly honest (no fake PLAY stake). Not a shipping defect; a gated research surface.

## Letter grades

| Area | Grade | Notes |
|------|-------|-------|
| Moneyline | **C+** | Brier ~0.25 fails gate; CLV weak |
| Run line | **B** | CLV +0.19–0.23; desk retained |
| Totals | **B** | CLV strong; MAE near/over 3.5 |
| Props | **C** | research_only; stake gates off |
| Edgeboard product fit | **A−** | ML + total matches how MLB is bet |
| Publish honesty | **A** | No stake claims without unused-holdout pass |
| **Overall** | **B−** | Strong RL/total CLV + honest props; ML is the weak link |

## What shipped vs recommended

### Shipped (this PR)

- MLB Edge Board: moneyline + totals (web odds fetch, KEI merge, UI, fallback snapshot, tests)
- Prob-point ML edge aligned with no-vig home (same idea as `/mlb/edges/today`)
- Desk copy: public board describes moneylines

### Not shipped (recommended only)

1. **Grade unused holdout** for ML / RL / totals stake gates — do not market until pass.
2. **ML sharpness levers (evidence-first):** PA / matchup features, SP + lineup shock already exist — prefer holdout-evaluated feature ablations over ad-hoc ML nudges.
3. **Totals level:** attack MAE (park, weather, bullpen) while protecting total CLV.
4. **Wire optional server `ml_edge_prob`** onto board rows if client/book mismatch appears in prod.
5. **Props:** keep research_only until a separate props holdout clears.
6. **Do not densify** Odds historical for this work (credit floor policy).

## Architecture touchpoints

| Layer | Path |
|-------|------|
| Odds → board | `apps/web/lib/odds-api.ts` (`h2h,totals` for MLB) |
| Fair → KEI | `apps/web/lib/mlb-kei-from-fair-lines.ts` |
| Merge / seed | `apps/web/lib/edge-board-kei.ts` |
| Edge UI | `apps/web/components/EdgeBoard.tsx` |
| Edges desk (ML) | `GET /mlb/edges/today` → `ml_edge_prob` |
| Holdout registry | `data/ops/mlb-enterprise-holdout/unused_holdout_registry.json` |

## Verify

```bash
# Web unit tests (edgeboard / MLB)
pnpm --filter @kosedge/web exec vitest run \
  __tests__/lib/odds-api.test.ts \
  __tests__/lib/edge-board-kei.test.ts \
  __tests__/lib/edge-board-side.test.ts \
  __tests__/lib/mlb-kei-from-fair-lines.test.ts

# Model health (Railway)
curl -sS "$MODEL_SERVICE_URL/mlb/health"
curl -sS "$MODEL_SERVICE_URL/mlb/fair-lines"
curl -sS "$MODEL_SERVICE_URL/mlb/edges/today"
```
