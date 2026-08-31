# CFB Engine Blocker — Week 0 close pass

**Status:** STOP on Utah title % (successful use of the one-pass brief).  
**Date:** 2026-08-31  
**Branch:** `cursor/cfb-week0-close-wp-shock-gates-3ca1`

## What passed before the stop

| Gate                                                                                         | Result |
| -------------------------------------------------------------------------------------------- | ------ |
| One spine restored (`power_sot` + official schedule)                                         | OK     |
| Single `as_of=2026-08-31` on power / proj / futures / KEI                                    | OK     |
| Week 0 FBS finals locked (6/6) without power refit                                           | OK     |
| Top-7 power unchanged (OSU…ND)                                                               | OK     |
| Cupcake model WP ≥ 0.90 on large gaps (BALL@OSU, UTEP@OU, MOST@TAMU, FRES@USC, MASS@RUT)     | OK     |
| USF win-total **std** < OSU **std** (1.118 < 1.309) after SCORE_NOISE shrink + WP saturation | OK     |
| USF E[wins] separated from OSU (8.884≈OSU → 8.382 vs OSU 9.537)                              | OK     |
| KEI remains game line (`apply_cfb_kei`); `assert_kei_not_tail`                               | OK     |
| Futures field = P4 autos + one G6 auto + power-aware at-larges                               | OK     |
| No team-id branches; NFL/CBB/MLB untouched                                                   | OK     |

## Blocker: `UTAH_TITLE_TAIL_UNMOVED`

| Metric             | Before (audit dump) | After (same functions)  |
| ------------------ | ------------------- | ----------------------- |
| Utah `power_index` | 1.4841              | 1.4841 (flat — correct) |
| Utah `natty_pct`   | **6.6**             | **6.2**                 |

Change is noise (6.6 → 6.2), not “moved a lot” off the ~5% tail.

### What we already changed (honest levers)

1. **WP saturation** — `team_projection.win_prob_from_expected_scores` + `power_sot.frozen_home_wp` cupcake SD application (`WP_CUPCAKE_Z`).
2. **Year-shock / variance** — `priors.SCORE_NOISE_SD` 12.5→10.5; early score/margin mults compressed; `STRENGTH_NOISE` 0.014→0.010.
3. **Field constructor** — `cfb_futures.select_cfp_field` power-aware at-larges + P4 + one G6 auto.

### What we refuse to do (laws)

- Stretch `_playoff_wp` logistic coefficient `2.1` (or OSU’s `1.6168` power index) to look like Vegas.
- `if team == "Utah"` clamp / haircut.
- Blend market into research-fair natty %.
- Refit power from UNC–TCU or any Week 0 result.
- Invent `cfb_v2/`.

## Operator choice

Accept this blocker and ship the WP/shock/`as_of`/gates work as-is, **or** open a separate approved futures-bracket investigation that does not stretch the WP scale. Do not beauty-pass Utah in this PR.
