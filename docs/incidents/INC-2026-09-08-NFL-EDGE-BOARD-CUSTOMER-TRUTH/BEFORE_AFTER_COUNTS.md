# Before / after affected-row counts — INC-2026-09-08

Live NFL fair-lines snapshot used for desk simulation (model-service `/nfl/fair-lines`, season 2026).  
**Before** = prior desk contract (consensus Book + signed edge).  
**After** = shared customer-truth contract (stake/compare market + positive magnitude + fail-closed).

## NFL Edges desk — spreads (min |edge| ≥ 1.0)

| Metric                                      |                                                         Before | After |
| ------------------------------------------- | -------------------------------------------------------------: | ----: |
| Spread rows painted                         |                                                             12 |    12 |
| Negative selected-side edge display         |                                             **7** (Home leans) | **0** |
| Fair/Book vs \|edge\| arithmetic mismatches | **2** (live transform; desk API earlier showed 5 vs consensus) | **0** |
| Fail-closed omissions (unreconcilable)      |                                                            n/a | **0** |

\*After uses stake/compare as Book; rows that cannot reconcile are omitted (fail closed). Live snapshot at fix time: all former mismatch rows reconcile once Book = stake close (e.g. ARI @ LAC Book −10.0 with Edge +1.7).

## NFL Edges desk — totals (min |edge| ≥ 1.0)

| Metric                                  | Before |                After |
| --------------------------------------- | -----: | -------------------: |
| Total rows painted                      |     17 |                   17 |
| Negative selected-side edge display     | **13** |                **0** |
| Fair/consensus vs stake-edge mismatches |  **4** | **0** (Book = stake) |

## NFL Edges desk — moneyline

| Metric                          | Before |                     After |
| ------------------------------- | -----: | ------------------------: |
| Signed negative pp on Away lean |    yes | **0** (positive `+X.Xpp`) |

## Edge Board assemble (`/edge-board/{sport}`)

| Sport | Before neg magnitude |      Before Fair/Mkt/Edge arith bad | After (contract scrub)             |
| ----- | -------------------: | ----------------------------------: | ---------------------------------- |
| nfl   |                    0 |   0 (internally consistent triples) | 0 unresolved; mismatch → hide edge |
| cfb   |                    0 | n/a (often no Action triple fields) | auditors + scrub in legacy path    |
| nba   |                    0 |                                 n/a | same                               |
| nhl   |                    0 |                                 n/a | same                               |
| mlb   |                    0 |                                 n/a | same                               |
| wnba  |                    0 |                                 n/a | same                               |
| ncaam |                    0 |                empty slate at trace | same                               |

## Unresolved after fix

**0** sign inconsistencies and **0** arithmetic inconsistencies on handicap/total rows that still paint an edge.
