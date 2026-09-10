# MLB fairTotal / KEI total — nearest half-run (2026-09-10)

**PR target:** `deploy-vercel` (agent does not merge)  
**Separate from:** ML pts→pp, #516, DFS, Line Curve, #517/#519/#521 identity gates  
**Incident:** 2026-09-10 slate — every fair-lines row had `fairTotal` / `handicapTotal` = 9 while `totalMean` ≈ 9.09–9.11 (`mlb-v1-pa-sim`). Looked like a stub constant.

## Smoking gun

Quantization lives in the model-service simulators, not the web mapper:

```
services/model-service/src/services/mlb_simulator.py
services/model-service/src/services/mlb_pitch_simulator.py
```

was inline:

```python
"fair_fg_total": round(fg_mean * 2.0) / 2.0
"fair_f5_total": round(f5_mean * 2.0) / 2.0
```

`9.09 * 2 = 18.18` → `round` → `18` → `/ 2` → **9.0**. Same for 9.10 / 9.11.

`fg_total_mean` and `f5_total_mean` stay continuous and distinct. Web
`mlb-kei-from-fair-lines` / `edge-board-kei` paint the published fair/handicap
total; they do not invent a second grain.

## Locked policy (not invented this PR)

| Field | Meaning |
| ----- | ------- |
| `*_total_mean` | Continuous sim mean (research / provenance) |
| `fair_*_total` / KEI total | **Nearest half-run** of that mean |
| Token | `nearest_half_run` |

Python 3 `round` is half-even at exact .25 / .75. FG and F5 are quantized
independently. A clustered slate may share one KEI total; means that cross a
half-run boundary must not collapse (8.24→8.0, 8.26→8.5, 9.26→9.5).

If published `fair_*_total` is missing, the web fallback applies the same
rule to the mean — it does **not** put the raw 9.09 on the board as KEI.

## Out of scope

- ML pts→pp label
- #517 / #519 / #521 identity gates (do not weaken)
- #516 polish, DFS, Line Curve
- Changing the half-run tick to something else

## Verify `/edge-board/mlb` + `/pro/mlb/fair-lines`

1. KEI total equals published `fair_fg_total` / `handicapTotal` (half-run).
2. `totalMean` / mean provenance still shows the continuous ~9.09 when present.
3. A slate of 9.09-ish means sharing KEI 9.0 is **honest rounding**, not a stub.
4. Games whose means sit on different sides of a 0.5 boundary show different KEI totals.
5. Identity gates unchanged: live remaining / missing period still fail closed.
