# IMV PR #610 corrections (C-1..C-9)

**Filed:** 2026-10-22  
**Applies to:** `docs/research/NFL_MODEL_VALIDATION_TRACE_COMPLETE_2026-10-22.md` and `nfl_eval_prep` bytes.

| ID | Correction | Where |
| -- | ---------- | ----- |
| C-1 | Exec finding 5: no season is **proven** untouched. Pre-2013 unused by those scripts only. W8+ is a future population, not untouched. | TRACE exec §5 |
| C-2 | Buckets mapped to ruling A: (a) used in development, (b) PIT UNKNOWN, (c) untouched 0 proven, (d) W8+. | TRACE ruling A table + §2 |
| C-3 | CLEAN only in the defined sense (sealed list + as-of proofs + train-only). Zero CLEAN results. | TRACE header; removed “CLEAN as a count/join/grade/label” |
| C-4 | 2992 vs 2863: 129-game gap count-matches playoff slate on OOS CSV week-band. Rows are **not** identical (2863 ⊂ 2992). July 28 train identity **UNKNOWN**. | TRACE §1.2a |
| C-5 | Enterprise-gates floors labeled **transcription**, not frozen IMV criteria. | TRACE §1.7 |
| C-6 | Close/score columns refused as features; whole-row as-of fallback dropped; named `archive:<name>` source required; as-of **self-declared** on the hist path. | `asof.py`, `local_path.py`, `local_tree_check.py` |
| C-7 | Pre-2013 refused unless a Ryan-filed season list exists. | `splits.py` |
| C-8 | `runner_v2` / `PREP_VALIDATED` removed. Module is `local_tree_check`; status `LOCAL_TREE_CHECKED` is not a gate. | `local_tree_check.py` |
| C-9 | Prior searches are **asserted**, not reproduced in this correction. | TRACE header |

W8 capture is a **separate** package (`nfl_w8_capture`) and does not import `nfl_eval_prep` (AC-10).
