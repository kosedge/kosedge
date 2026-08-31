# CFB Engine Week 0 Scorecard

**as_of (after):** `2026-08-31` (unique across power / projections / futures / KEI)  
**sim:** seed=`20260831` n=`10000` (projections) / `2500` (futures)  
**wp_mapper:** `team_projection.win_prob_from_expected_scores` + `power_sot.frozen_home_wp`  
**shock:** `priors.SCORE_NOISE_SD` + `priors.STRENGTH_NOISE` (+ early mults)  
**kei_def:** `cfb_kei.apply_cfb_kei`  
**Dump:** `python3 scripts/cfb/cfb_dump_canaries.py`

Before numbers = Phase 0 audit dump from frozen artifacts (2026-08-14 / 08-17).  
After numbers = same artifact loaders after close + WP/shock/field rebuild.

| Metric | Before | After | Allowed | Function |
|---|---|---|---|---|
| `as_of` uniqueness | 4 values (08-13/14/17/roster) | **1** (`2026-08-31`) | exactly 1 | artifact `as_of` / `power_as_of` |
| OSU power | 1.6168 | 1.6168 | ≈ flat | `power_sot.build_power_sot` |
| Top-7 L2 / max-abs | OSU…ND vector | identical order; max-abs 0 | noise only | same |
| OSU E[wins] | 8.883 | 9.537 | small/ok | `power_sot.build_season_projection_artifact` |
| OSU win-total width | p90−p10=4.0 / std=1.460 | 3.0 / **1.309** | may stay wide | same |
| USF power | 1.2601 | 1.2601 | ≈ flat | `build_power_sot` |
| USF E[wins] | 8.884 (≈OSU) | **8.382** (gap vs OSU opened) | must move a lot | projections artifact |
| USF win-total width | 4.0 / 1.474 | 3.0 / **1.118** | **std < OSU** | projections |
| Utah power | 1.4841 | 1.4841 | ≈ flat | `build_power_sot` |
| Utah title % | 6.6 | **6.2** | must move a lot **or blocker** | `cfb_futures.finalize_futures` → **BLOCKER** |
| Cupcake WP × 3+ | FRES 0.894, MASS 0.879, MOST 0.917 | FRES **0.928**, MASS **0.915**, MOST **0.947**, UTEP **0.953**, BALL **0.980** | real 90s | `project_game` → KEI board |
| KEI(OSU/USF/Utah) | game-line only | game-line only + `assert_kei_not_tail` | not a tail dump | `apply_cfb_kei` |
| Market column | n/a | comparison-only (unchanged) | comparison only | Edge Board trusted market |
| Lineage | absent | present on proj/futures | present | `lineage` object |

## Week 0 close

| Item | Value |
|---|---|
| Finals locked | UNC@TCU 15-10, SJSU@USC 26-42, NCSU@UVA 8-34, HAW@STAN 27-37, NMSU@FSU 17-34, MEM@UNLV 27-21 |
| Power refit from Week 0 | **No** |
| Idempotent close | re-run `scripts/cfb/close_week0.py` rewrites same scores |

## What we refused to do

- Retune top-7 / train on UNC–TCU
- Stretch Φ / `WIN_PROB_MARGIN_SD=15.2` / playoff logistic `2.1` to move Utah
- `if team == "Utah"` / `"USF"` branches
- Market inside research-fair numbers
- A second CFB stack (`cfb_v2/`)
- Touch NFL / CBB / MLB

## Blocker

See `docs/CFB_ENGINE_BLOCKER.md` — Utah `natty_pct` did not move a lot (6.6→6.2) after real WP + shock + power-aware field work.
