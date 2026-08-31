# CFB Engine Unify Live API — Scorecard

**Tag baseline:** `cfb-week0-close-2026-08-31` (`bfe5b0b5`)  
**Pass:** stamp/universe honesty only — no WP / shock / power retune  
**Dump:** `PYTHONPATH=services/model-service/src:services/model-service:. python3 scripts/cfb/cfb_dump_canaries.py`

| Metric                   | Week 0 close (tag)                                                       | After unify                                       | Allowed                | Function                                          |
| ------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------- | ---------------------- | ------------------------------------------------- |
| Frozen engine stamp      | JSON still said `v0.9-inseason` (bug); power_version `v0.15-week0-close` | **`cfb-season-engine-v0.15-power-sot`**           | same string everywhere | `priors.ENGINE_VERSION` + artifact re-stamp       |
| Live engine stamp        | `v0.9-inseason`                                                          | **`v0.15-power-sot`**                             | must match frozen      | `DEFAULT_SEASON_ENGINE_VERSION` / `routes/cfb.py` |
| `as_of` live vs frozen   | artifacts `2026-08-31`; live status missing                              | both **2026-08-31** (status echoes `power_as_of`) | unique                 | `cfb_season_engine_status` + power SoT            |
| OSU / USF / Utah power   | 1.6168 / 1.2601 / 1.4841                                                 | same                                              | flat                   | frozen `cfb_power_sot_2026.json`                  |
| OSU / USF / Utah E[wins] | 9.537 / 8.382 / 9.634                                                    | same ±0.05                                        | no new board           | re-stamp only (no re-sim)                         |
| Utah natty %             | 6.2 + blocker                                                            | 6.2 + blocker                                     | untouched              | `docs/CFB_ENGINE_BLOCKER.md`                      |
| Cupcake WP               | 90s                                                                      | 90s (BALL 0.98 / FRES 0.9278 / MASS 0.9147)       | untouched mapper       | `project_game_preview`                            |
| KEI definition           | game line                                                                | game line                                         | untouched              | `apply_cfb_kei`                                   |
| Preview modelNote engine | already `v0.15-power-sot` prose                                          | matches `ENGINE_VERSION`                          | regen only             | `cfb-previews.ts`                                 |
| Official slate default   | already true on live                                                     | documented + gated                                | densify fallback only  | `loaders.build_packaged_universe`                 |

## Dump after unify (artifact path)

```
ENGINE_VERSION=cfb-season-engine-v0.15-power-sot
as_of=2026-08-31 (power/proj/futures/kei)
OSU power=1.6168 E[wins]=9.537
USF power=1.2601 E[wins]=8.382
UTAH power=1.4841 E[wins]=9.634
```

## What we refused to do

- Retune WP / `WIN_PROB_MARGIN_SD` / playoff logistic 2.1
- Change `SCORE_NOISE_SD` / `STRENGTH_NOISE`
- Re-sim a second 10k board
- Reopen Utah title beauty-pass
- Touch NFL / CBB / MLB or widen DepthSot mute
