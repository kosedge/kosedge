# KosEdge NFL Decision Engine (Edge Board Action Layer)

**Date:** 2026-08-09  
**Branch:** `feat/nfl-decision-engine-edge-board` → `deploy-vercel`  
**Locked baseline (unchanged):** `nfl-season-engine-v1.24-soft-piles-cleanup` / bundle `nfl-preseason-sim-2026-20260809T165350Z` / tag `nfl-2026-preseason-baseline-v1.24`

## Doctrine

> We bet prices, not teams.  
> The same game can be a PLAY, LEAN, or PASS depending only on the current market number.

This layer sits **on top of** locked model fair lines. It does **not** change true PR / season-engine math and does **not** unlock or alter the locked preseason baseline.

## Contract coexistence (Model vs KEI vs Edge)

| Layer | Meaning | Used for |
|-------|---------|----------|
| **Model research fair** | Pre-blend MC fair (`model_spread_home`, `model_total_mean`) | Decision Engine fair vs market |
| **KEI reprice** | Post-blend published handicap (`spread_home`, `total_mean`) | Edge Board KEI columns |
| **Edge / publish tags** (`publish_tag_*`) | **KEI vs market only** | Existing PLAY desk evidence bands |
| **Action layer** (this engine) | **Model fair vs market** | Action Labels + Play-To ladders |

Both systems coexist on the same fair-lines / Edge Board row. Action Labels are **not** collapsed into publish tags.

## Thresholds (exact)

### Sides — weeks 1–2 (default at season start)

| |edge| vs fair | Grade |
|----------------|-------|
| < 1.5 | PASS |
| 1.5 – 2.0 | LEAN |
| 2.5 – 3.0 | PLAY |
| 3.5+ | STRONG PLAY / investigate |

### Sides — weeks 6–12

| |edge| vs fair | Grade |
|----------------|-------|
| < 1.0 | PASS |
| 1.0 – 1.5 | LEAN |
| 2.0+ | PLAY |

### Cover probability (−110, break-even ≈ 52.38%)

| Cover prob | Grade |
|------------|-------|
| < 53% | PASS |
| 53 – 54% | LEAN |
| 54 – 56% | PLAY |
| 56 – 58% | STRONG PLAY |
| 58%+ | Exceptional — double-check |
| 60%+ vs mature markets | Model warning (not free money) |

### Totals

| |model − market| | Grade |
|-------------------|-------|
| < 1.5 | PASS |
| 1.5 – 2.0 | LEAN |
| 2.5 – 3.0 | PLAY |
| 3.5+ | STRONG PLAY |

Cover-prob path for totals activates when `over_prob` (score distribution) is present on the projection.

## Official Action Labels

| Label | Criteria | Action |
|-------|----------|--------|
| PASS | Small edge or high uncertainty | Nothing |
| LEAN | Mild edge | Watch list |
| PLAY | Numerical edge + confidence + price | Bet |
| BEST VALUE | Strict Best Bet gates | Highest priority |
| ALERT | Edge with material uncertainty / price gone | Wait |
| STAY AWAY | Conflicting inputs / bad market | No bet |

**PLAY triple:** (1) numerical edge (2) confidence OK (3) price still available.

**Best Bet** requires all of: large edge, high confidence, favorable number, limited unresolved info, matchup support, acceptable liquidity. Raw discrepancy alone never qualifies.

Edge Magnitude and Model Confidence are **never** combined into one score.

## Play-To ladders

Every LEAN / PLAY / BEST VALUE / ALERT emits an execution plan (play / lean / pass prices).

## Wire points

1. **Authoritative module:** `services/model-service/src/services/nfl_decision_engine.py`
2. **Fair-lines API:** `GET /nfl/fair-lines` emits `decision`, `action_label_spread`, `action_label_total`, confidence + magnitudes (`services/model-service/src/routes/nfl.py`)
3. **Web mirror:** `apps/web/lib/nfl-decision-engine.ts`
4. **Fair-lines client:** `apps/web/lib/nfl-fair-lines.ts` normalizes decision payload
5. **Edge Board assembly:** `apps/web/lib/nfl-edge-board-from-fair-lines.ts` attaches action fields (server-first, local fallback)
6. **UI:** `apps/web/components/EdgeBoard.tsx` — Action column + Play-To + Edge Mag vs Confidence
7. **Tests:** `services/model-service/tests/test_nfl_decision_engine.py`, `apps/web/__tests__/lib/nfl-decision-engine.test.ts`

## Market confirmation

Records Independent model → opening → current → closing. Movement confirms or weakens thesis; **never** updates the model fair line / power rating.
