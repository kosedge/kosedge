# CFB totals PLAY — sit (tagger only)

**Date:** 2026-09-03  
**Owner lock:** Ryan / CoS  
**Related audit:** `docs/CFB_TOTALS_HOT_AUDIT.md` (why Overs look hot — KEI total ≡ model total)  
**Out of scope:** KEI pack, haircut, remat, mint, engine retune. Spreads untouched.

---

## Product rule

CFB **Total** rows may be **LEAN / PASS / untrusted** — **never PLAY** until an **unused close holdout** greens **and** Ryan/CoS explicitly flips eligibility.

- LEAN ≥ 2.5 still fires (do **not** sit LEAN).
- Spreads unchanged: PLAY ≥ 4.0 / LEAN ≥ 2.5 / `|12|` trust (`CFB_ABSURD_VS_KEI_PTS`).
- One SoT: Edge Board Tag O/U and publish/display tag agree after remap (`cfbEdgeTag` ≡ `cfbPublishTagFromEdge`).

---

## Flag

| Surface | Constant | Value |
| ------- | -------- | ----- |
| Web | `CFB_TOTALS_PLAY_ELIGIBLE` in `apps/web/lib/cfb-trusted-market.ts` | `false` |
| Model-service | `TOTALS_PLAY_ELIGIBLE` in `book_ledger/cfb_trusted_market.py` | `False` |
| Dump twin | `CFB_TOTALS_PLAY_ELIGIBLE` in `scripts/cfb/cfb_dump_edgeboard.py` | `False` |

Tagger behavior when false: totals `|edge| ≥ 4.0` → **PASS** (not demoted to LEAN). Totals `|edge| ≥ 2.5` and `< 4.0` → **LEAN**.

---

## Re-enable (only)

1. Unused **close** holdout for CFB totals PLAY grades **GREEN**.
2. Explicit Ryan/CoS flip of `CFB_TOTALS_PLAY_ELIGIBLE` / `TOTALS_PLAY_ELIGIBLE` to `true` in the same PR across web + Python + dump.
3. Do **not** “mint” PLAY by raising/lowering thresholds, KEI haircut, or remat.

Until then: numbers only on totals Tag O/U — LEAN/PASS/untrusted chrome is fine; no PLAY.
