# NFL Futures Conservation + Win-Distribution Audit — 2026-08-11

**Status:** P0 gate green · PRESEASON/MODEL honesty on Futures  
**Branch:** `feat/nfl-futures-conservation` → `deploy-vercel` (+ Railway model-service)  
**Active board:** `nfl-preseason-sim-2026-20260809T165350Z`  
**Pass:** v1.24.1 consecutive pile-break reshape (PF/PA spine unchanged)

---

## Diagnosis (before knobs)

| Question | Answer |
|----------|--------|
| 1. Same production strength path as Model PR? | **Board wins = soft-pile PF/PA path** (same as Power *outlook* wins). Model PR Method B (margin vs league avg) is a **different surface** — LAR #1 on PR (~+5.1) vs ~9.7 wins is expected, not a dual-path bug. |
| 2. Broken WP→season wins transform? | **No.** Week-rate Σ = board E[wins] after #196/#197; STRENGTH_ALIGN green. |
| 3. Multiple teams sharing identical win draws? | **No.** Soft-pile week-rate fingerprints unique; values differ by ≤0.28. |
| 4. Single-path realistic but aggregate collapses? | **No.** Path MC conserves; aggregate Σ E[wins] = 272. |
| 5. Histogram (before) | **≤6: 9 · 7–9: 12 · 10–11: 1 · ≥12: 10** |

### One-sentence primary failure mode

Soft-ceiling win stretch + `_break_soft_piles` clustering **vs cluster-first** with width=0.04/spread=0.12 fragmented a 10-team 12.55–12.83 band into size-2 pairs that never received a residual micro-spread — so Futures looked like ten identical ~12.6 locks without matching Model PR spread.

### Fix path (lowest broken layer)

1. Consecutive-gap clustering in `_break_soft_piles`
2. `WIN_PILE_BREAK_WIDTH=0.15`, `WIN_PILE_BREAK_SPREAD=1.2`
3. Re-stretch wins from **existing** board PF/PA (no second futures model, no hand edits)
4. Re-run strength coherence (week rates + win_dist + playoff/SB)

---

## Before / after

| Metric | Before | After |
|--------|-------:|------:|
| Σ E[wins] | 272.000 | **272.000** |
| Ceiling cluster (≤0.35 of max) | **10** | **2** |
| Hist ≤6 / 7–9 / 10–11 / ≥12 | 9 / 12 / 1 / 10 | **10 / 11 / 4 / 7** |
| LAR E[wins] | 9.6938 | **9.6938** |
| DET E[wins] | 7.0459 | **7.0454** |
| Top band | 10 teams @ 12.55–12.83 | CHI 13.93 … NE 12.26 (spread) |

### Top 10 after reshape

CHI 13.93 · JAX 13.65 · BUF 13.38 · SEA 13.11 · ATL 12.83 · BAL 12.54 · NE 12.26 · PHI 11.96 · IND 11.66 · KC 11.66

---

## C1–C6 status

| ID | Rule | Status |
|----|------|--------|
| C1 | One winner + one loser per RS game (ties not modeled) | **PASS** (0/2000 fails) |
| C2 | Σ team RS wins = 272 per path | **PASS** |
| C3 | Exactly 7 AFC + 7 NFC playoff teams per path | **PASS** |
| C4 | Exactly 8 division winners per path | **PASS** |
| C5 | Exactly 1 SB winner per path | **PASS** |
| C6 | Aggregated E[wins] across 32 = 272 (±0.51) | **PASS** (271.9996) |
| CEILING_PILE | ≤3 teams within 0.35 of max | **PASS** (2) |

Truth Layer I1–I8 + STRENGTH_ALIGN + Week1: **PASS**.

LAR playoff/SB after coherence: ~80.9% / 6.9%. DET: ~53.5% / 2.0% (still report-only `low_wins_high_playoff` under CHI soft pile — spine aligned).

---

## Deliverables

| Item | Path |
|------|------|
| Conservation job | `scripts/nfl/check_season_sim_conservation.py` |
| Reshape job | `scripts/nfl/reshape_board_win_distribution.py` |
| Tests | `services/model-service/tests/test_nfl_season_sim_conservation.py` + stack smoke |
| Audit artifact | `data/ops/nfl-preseason-sim-2026-20260809T165350Z/win_distribution_reshape.json` |
| Futures UI | PRESEASON/MODEL label + `NflLineageBadge` (run_id / engine / as-of) |

---

## Publish honesty

Futures remains **PRESEASON / MODEL** research — conserved soft-pile W/L after v1.24.1 reshape, not a paid in-season futures market claim. Model PR (Method B) stays the strength desk; win totals remain the conserved season-total spine.

## Non-goals (held)

Awards % rename · Props filter · Fantasy ADP · Power redesign beyond shared spine

## Smoke

```bash
.venv/bin/python scripts/nfl/check_season_sim_conservation.py
.venv/bin/python scripts/nfl/check_nfl_invariants.py
```

*Locked by: agent · 2026-08-12*
