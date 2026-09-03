# CFB spread PLAY — sit (tagger only)

**Date:** 2026-09-03  
**Owner lock:** Ryan / CoS  
**Evidence:** unused 2025 close holdout — PLAY [4,7) ATS 49.4% ROI −5.7% (n=170); ≥7 ATS 48.0% ROI −8.3% (n=179) — both RED  
**Ops note:** `data/ops/cfb-spread-tag-close-holdout-20260903.md` / PR 438  
**Out of scope:** KEI pack, haircut, remat, mint, engine retune, 4.0 floor retune, cap7 lock. Totals sit unchanged (`docs/CFB_TOTALS_PLAY_SIT.md`).

---

## Product rule

CFB **Spread** rows may be **LEAN / PASS / untrusted** — **never PLAY** until an **unused close holdout** greens **and** Ryan/CoS explicitly flips eligibility.

- Spreads `|edge| ≥ 4.0` → **PASS** (not demoted to LEAN).
- LEAN ≥ 2.5 still fires (do **not** sit LEAN).
- Totals remain sat (`CFB_TOTALS_PLAY_ELIGIBLE = false`).
- `|12|` trust (`CFB_ABSURD_VS_KEI_PTS`) unchanged.
- One SoT: Edge Board Tag and publish/display tag agree after remap (`cfbEdgeTag` ≡ `cfbPublishTagFromEdge`).

---

## Flag

| Surface       | Constant                                                           | Value   |
| ------------- | ------------------------------------------------------------------ | ------- |
| Web           | `CFB_SPREAD_PLAY_ELIGIBLE` in `apps/web/lib/cfb-trusted-market.ts` | `false` |
| Model-service | `SPREAD_PLAY_ELIGIBLE` in `book_ledger/cfb_trusted_market.py`      | `False` |
| Dump twin     | `CFB_SPREAD_PLAY_ELIGIBLE` in `scripts/cfb/cfb_dump_edgeboard.py`  | `False` |

Tagger behavior when false: spreads `|edge| ≥ 4.0` → **PASS**. Spreads `|edge| ≥ 2.5` and `< 4.0` → **LEAN**.

---

## Re-enable (only)

1. Unused **close** holdout for CFB spread PLAY grades **GREEN**.
2. Explicit Ryan/CoS flip of `CFB_SPREAD_PLAY_ELIGIBLE` / `SPREAD_PLAY_ELIGIBLE` to `true` in the same PR across web + Python + dump.
3. Do **not** “mint” PLAY by raising/lowering thresholds, KEI haircut, remat, or locking a cap7 band from a red split.

Until then: numbers only on spread Tag — LEAN/PASS/untrusted chrome is fine; no PLAY.
