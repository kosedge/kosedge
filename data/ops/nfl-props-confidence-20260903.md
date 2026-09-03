# NFL props confidence — 2026-09-03

**Scoped fix:** prop `confidence` decoupled from edge magnitude; desk fair-lines confidence threaded.  
**PR:** reliability score in `nfl_prop_edge_policy.py` + `deskEdgesFromFairLine` inheritance.  
**No remat / no KEI mint / no calibration change / no threshold change.**

---

## Verdict split

| Bucket | Share | Notes |
|--------|-------|-------|
| Mapping bug | ~60% | `deskEdgesFromFairLine` hardcoded `confidence: null` on ML/spread/total while fair-lines already carried `decision.modelConfidence` |
| One-way book coverage | ~25% | 81 of 1,969 eligible rows joined; only 19 two-way; 62-of-81 joined cohort is `anytime_td` with Over-only pricing |
| Honest Week 1 uncertainty | remainder | `historical_fit` null, `gamesPlayed` 0/0, `qb_unresolved` / `conflicting_inputs` on game desk |

---

## Prop confidence failure (live 2026-09-03)

Old formula: `confidence = clamp(|z|/2.6 + (0.30 if both_sides else 0), 0.05, 0.99)` — monotone in edge magnitude, contradicting `ConfidenceAssessment` doctrine.

### Anytime TD one-way cohort (62 / 81 joined rows)

Bernoulli σ ≈ 0.49 at line 0.5 ⇒ |z| caps ~0.61 ⇒ old confidence capped ~0.234, usually floored to **0.05**.

| Player | Team | Mean | Line | Edge Over | z | Old confidence |
|--------|------|------|------|-----------|---|----------------|
| C.Sutton | DEN | 0.4055 | 0.5 | +0.1265 | ~−0.61 | **0.05** |
| J.Smith-Njigba | SEA | 0.5049 | 0.5 | +0.0026 | ~+0.01 | **0.05** |

+12.65pp and +0.26pp edges printed the same fake 5%.

**Fix:** `anytime_td` + one-way pricing ⇒ `confidence: null` (em dash in UI).

### Two-way contrast (yards)

| Player | Market | Line | Mean | z | Edge Under | Old confidence | Tag |
|--------|--------|------|------|---|------------|----------------|-----|
| G.Holani | rush_yds | 21.5 | 12.859 | −2.225 | +0.487 | **0.99** | WATCH / `extreme_z_watch_only` |

Edge magnitude inflated confidence to 0.99 while tag policy correctly refused PLAY on extreme z.

---

## Game desk rows (fair-lines decision layer)

| Game | Market | KEI vs market | Edge (pts) | Confidence | Flags | Label |
|------|--------|---------------|------------|------------|-------|-------|
| NE@SEA | Spread | −3.87 vs −3.5 | 0.37 | **0.72** MEDIUM | none | honest no-edge PASS |
| ATL@PIT | Spread | — | 0.71 | **0.50** LOW | `qb_unresolved` | — |
| GB@MIN | Spread | — | 2.41 (clears W1 `EARLY_SIDE.play_min` 2.25) | **0.47** LOW | `conflicting_inputs` | STAY AWAY |
| DAL@NYG | Total | 47.2 vs 48.5 | 1.26 | **0.47** LOW | `conflicting_inputs` | — |

Edges desk showed blank confidence on all 37 side/total/ML rows while edge-board assemble showed 0.72 / 0.47 / 0.50 — mapping bug, not model doubt.

---

## New prop reliability formula (edge-independent)

```
score = PROP_RELIABILITY_BASE (0.48)
  − 0.18 if fallback_used
  − 0.14 × role_shortfall   (role < 0.50)
  − 0.12 × avail_shortfall  (availability < 0.50)
  − 0.08 if market_shrink ≥ 0.20
  − 0.05 if calibration_source ∉ {frozen, structure}
  + coverage(joined_book_count, two_way)
      coverage = 0.07 × min(1, books / 2) when two_way else 0
clamp to [0, 0.99]; anytime_td one-way ⇒ null
```

Clean two-way cap: 0.48 + 0.07 = **0.55** (at `CONFIDENCE_PLAY_MIN`, not near 1.0).

---

## Explicitly out of scope

- Unreachable HIGH band (`CONFIDENCE_TIER_BASE` 0.72 < 0.75 HIGH cut ⇒ `evaluate_best_bet` unreachable early season)
- Calibration retune, intercept changes, rematerialization, book adds/removals
- `PLAY_ABS_Z`, tag policy, stake gates, KEI reprice
