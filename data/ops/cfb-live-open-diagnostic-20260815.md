# CFB Live 2026 Open Diagnostic — model fair vs opens

**Date:** 2026-08-15  
**Branch:** `feat/cfb-live-open-diagnostic-2026` → `deploy-vercel` (stacked on #242)  
**Diagnostic id:** `cfb-live-open-diagnostic-v0.15.1-20260815`  
**Doctrine:** Research fair only. `used_in_spread` stays **false**. No KEI. No Edge tags. No blend. **Not a release gate.**

Script: `python scripts/cfb/cfb live-open --repo-fallback`  
Tables: `data/ops/cfb-live-open-diagnostic-20260815.json`

Open rule: first pre-kick snap; prefer DraftKings, then FanDuel, then any other book. Not consensus. Not lock.

---

## Bias one-liner

**Cold / short-favorite vs 2026 open.** Mean(model − open) **+6.35**, MAE **9.40**, median |err| **8.18**. Model is more favorite than the open on only **18%** of games (short-favorite rate **82%**). Same sign as hist. Not KEI.

---

## Join

| | |
| --- | ---: |
| Opens in lake (W0–2) | 55 |
| **n_matched** | **55 / 55** |
| Match rate | **100%** |
| n_closes | 0 |
| Unmatched dropped | 0 |

Model side: v0.15 power SoT / `project_game_preview` (same desk compose). No hist backfill. No invented opens.

---

## Overall vs open

| Metric | Value |
| --- | ---: |
| n | 55 |
| mean (model − open) | **+6.35** |
| MAE | **9.40** |
| median \|err\| | 8.18 |
| model more favorite than open | 18.2% (10/55) |
| short-favorite (model less favorite) | **81.8%** (45/55) |
| home fav / home dog (by open) | 47 / 8 |
| total side n | 55 |
| total mean (model − open) | +3.76 |
| total MAE | 4.97 |

Positive spread error = model **less home/favorite** than the book. Totals: model a bit higher than open (not the headline).

---

## Hist vs live

| Window | Mean err | MAE | Notes |
| --- | ---: | ---: | --- |
| Hist W0–1 vs **close** (2020–25 prior) | +4.13 | 8.36 | Program-prior walk-forward |
| Hist overall vs close | +2.04 | 7.48 | |
| **Live 2026 vs open** | **+6.35** | **9.40** | v0.15 project-game |

Same **sign**. Live magnitude is larger — expected: early-week tanh + open-QB honesty vs posted favorites, and this sample is heavy \|open\|≥14. Same engine family, not the same harness. Do not read live MAE as “worse hist.”

---

## Slices (n≥15 published; else thin)

### Week

| Slice | n | Status |
| --- | ---: | --- |
| W0 | 6 | **thin** |
| **W1** | 43 | mean **+7.00** / MAE 9.77 / short-fav 81% |
| W2+ | 6 | **thin** |

### \|open\|

| Bucket | n | Status |
| --- | ---: | --- |
| \|o\|<3 | 6 | **thin** |
| 3–7 | 8 | **thin** |
| 7–14 | 12 | **thin** |
| **≥14** | 29 | mean **+11.87** / MAE **13.65** / short-fav **100%** |

### Home / favorite (by open)

| Slice | n | Status |
| --- | ---: | --- |
| **Home favorite** | 47 | mean **+8.40** / MAE 9.83 / short-fav 83% |
| Home dog | 8 | **thin** |

### Conference (extra; same n≥15 rule)

| Slice | n | Status |
| --- | ---: | --- |
| **P4–G5** | 22 | mean **+12.50** / MAE **14.12** |
| P4–P4 | 15 | mean **−1.25** / MAE **5.44** (mixed / not cold) |
| G5–G5 | 6 | **thin** |
| Indep mix | 10 | **thin** |

**Worst slice:** \|open\|≥14 and P4–G5 cupcakes — model refuses the posted blowout. P4–P4 is the counterexample (do not overfit the cupcake side into a global prior).

---

## Gate — KEI **design** brief

| Checklist | Met? |
| --- | --- |
| n_matched ≥ 25 | Yes (55) |
| Bias readable vs 2026 open | Yes — cold / short-favorite |
| Closes + held-out CLV | **No** (`n_closes=0`) |
| More than one week band with n≥15 | **No** (only W1) |
| Mid-range \|line\| published | **No** (3–7 and 7–14 thin) |
| Scaffold “ready for KEI design when…” | **No** |
| `used_in_spread` still false | Yes |

**Go/no-go for designing an open-line prior: NO.**  
**Recommendation: hold through Week 3.** Re-pull as books add W0/W2 and after kickoffs create closes. Enough to *see* the bias; not enough to *sketch* a blend. A prior that only “fixes” \|open\|≥14 / P4–G5 is rank=market on cupcakes.

This diagnostic is **not a release gate**.

---

## Product honesty

- Fair-line generation unchanged.
- Edge Board CFB stays markets-only.
- No tags. No PLAY. No KEI write.
- `used_in_spread` false on every row.
