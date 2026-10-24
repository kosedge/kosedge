# Leakage controls (Ryan permanent rule)

Verbatim requirement (decision `47afd7f6`):

> No historical model input may contain information with an
> availability timestamp later than the prediction cutoff.
> Applies to: injuries, rosters, depth charts, transactions,
> quarterback changes, odds, weather, and every other
> time-sensitive feature.

## Control

For every historical row `x` used to predict game `g`:

```
availability_ts(x) <= prediction_cutoff(g)
```

`prediction_cutoff(g)` is `kickoff_utc` for the residual fit.

If `availability_ts` is missing, naive, or unparseable: refuse the
row (do not coerce). Existing B-4c for listings already does this.

## Feature table

| feature | current source | current timestamp | required change |
| --- | --- | --- | --- |
| injury listing status | listings_YYYY.csv `date_modified` | parsed; clipped by `last_report_before_kickoff` | keep; IMV judged safe |
| `n_lag_out` | listing weeks | listing week < game week | keep |
| roster membership | `roster_YYYY.csv` season snapshot | **none used** | week-aware book + `availability_ts` |
| depth / starter / `value` | same snapshot, `STARTER_SLOTS` | **none used** | weekly depth_order + `availability_ts`; no STARTER_SLOTS proxy |
| identity TEAM_MATCH / SEASON_FALLBACK | season-union books | **none used** | week-aware membership; drop season-union fallback |
| `x_continuity` current_ids | current-season union | **none used** | week-aware current membership |
| `x_continuity` prior starters | prior-season union | prior year (ok temporally) | prior last-REG weekly book |
| transactions / practice-squad | not in current fit | n/a | if added: announcement `availability_ts` |
| QB changes | implied by leaked QB slot | n/a | week-aware QB1 only |
| odds / close | oos close columns | used as descriptive CLV, not as a fit target under C-2 | must not enter features |
| weather | not in current fit | n/a | if added: forecast issued-at |

## Automated assertion (must ship with Phase 2, not now)

A checker walks every feature cell on every development game and
fails if any contributing source row has `availability_ts > kickoff`.
The current producer check (`listing_as_of` only) is not sufficient.

## Cross-sport intent

Same predicate for NBA / MLB / CFB when those models take
time-sensitive inputs. This spec does not implement those sports.

## What the control is not

- It is not "pin the season snapshot sha." A pinned leaky file is
  still leaky.
- It is not "refuse 2026." Year gates do not fix week look-ahead.
- It is not "listings as_of <= kickoff" alone.
