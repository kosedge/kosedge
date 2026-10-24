# Week-aware roster + depth reconstruction

## Problem the spec solves

Pinned `roster_YYYY.csv` is one row per `(team, gsis_id)` with a
`week` / `game_type` stamp that is usually last-week or playoff. The
frozen fit ignores that stamp and applies the row to every week.
See inventory `INVENTORY.md` and `evidence/pit-examples.md`.

Those files **cannot** be sliced into a true weekly panel. There is
no week-1 depth for a player whose only row is week 19 WC. Inventing
that depth from the later row is the defect.

## Sources (proposed; IMV must accept or name a substitute)

In priority order. A lower source may not overwrite a higher source
that is eligible at the cutoff.

1. **Weekly roster membership** — nflverse weekly rosters
   (`nflreadr` / `nflreadpy` `load_rosters_weekly` or the equivalent
   table with `season, week, game_type, team, gsis_id, status,
   depth_chart_position`). One row per `(season, week, game_type,
   team, gsis_id)`.
2. **Weekly depth / official depth** — nflverse `load_depth_charts`
   or `nfl_dp_official_depth_charts` / a *true* weekly depth table
   keyed by `(season, week, team, player_id, pos, depth_order)`.
3. **Look-back only** — the latest eligible row of (1) or (2) whose
   availability timestamp is `<=` the prediction cutoff. Never a
   later week. Never a playoff row for a REG game.

Rejected as a week-aware source:

- current pinned `roster_YYYY.csv` season snapshots
- `nfl_dp_rosters` season grain (`WHERE season = :season` with no week)
- `materialize_depth_chart_weekly` output that was stamped from
  season-level rosters + same-week usage (usage is post-game)
- any file that has one row per player-season

If (1) and (2) are unavailable for a development year, that year is
**ineligible** for features that need roster/depth. It is not filled
from a season snapshot.

## Availability timestamp

Every time-sensitive input row must carry `availability_ts` (UTC,
aware). Construction:

| source | `availability_ts` |
| --- | --- |
| injury listing | existing `date_modified` parsed as today (`last_report_before_kickoff`) |
| weekly roster row with a publisher timestamp | that timestamp |
| weekly roster / depth row with only `(season, week, game_type)` | **conservative default**: start of that NFL week's first scheduled kickoff in UTC. The row is not available before that instant. |
| transaction / QB change | announcement timestamp from the same source; if missing → row ineligible |
| odds / close | book timestamp; close must not enter a pre-close prediction |
| weather | forecast issued-at; observed weather after kickoff is ineligible |

Playoff `game_type` ∈ {WC, DIV, CON, SB, POST} has an availability
no earlier than that playoff week's first kickoff. It is ineligible
for every REG game.

## Prediction cutoff

For historical residual-fit rows:

```
prediction_cutoff = kickoff_utc
```

already computed by `parse_fit_kickoff_utc`. Same cutoff for listings
and for roster/depth/transactions/QB/odds/weather.

A row is eligible for that game iff

```
availability_ts <= prediction_cutoff
```

Ryan's permanent rule: **no historical model input may have
`availability_ts > prediction_cutoff`.** See `leakage-controls.md`.

## Week-aware membership

Player `pid` is on `team` for game `(season, week, home, away)` iff
there exists an eligible weekly-roster row with

- `season` match
- `game_type == REG` for REG games
- `week` of the row `<=` game week
- `team` match after the existing alias map
- `availability_ts <= kickoff_utc`

If multiple eligible rows exist, take the latest `week` (look-back).
If none exist: **not a member**. Do not infer membership from a later
week or from a season snapshot.

## Week-aware depth / role / replacement quality

Depth for a listed player is the `depth_order` (or equivalent rank)
on the latest eligible weekly depth row for `(season, team, pid)`
with `availability_ts <= kickoff`.

Rules:

- Do not use `depth_chart_position in STARTER_SLOTS` as a proxy for
  depth 1. That token set treats every `QB` slot as a starter and
  created four PIT QB1 candidates from one week-19 snapshot.
- Starter = `depth_order == 1` for that position group on that week,
  or an explicit starter flag from the weekly depth source.
- If no eligible depth row: `depth` is missing. `_structural_index`
  is not called with a default of 2. The player's replacement-quality
  contribution is missing; `side_units` already knows how to NULL a
  component when identity is unresolved — extend that to missing depth
  rather than inventing backup weight 2.
- QB1-out candidate: the single eligible week-aware QB with
  `depth_order == 1` on that team, and only if that row is eligible.
  Multiple QB-slot players must not all be QB1.

## Week-aware identity

`resolve_fit_player_identity` must receive week-keyed books:

- `TEAM_MATCH` iff `pid` is a member of `team` at the cutoff
  (rule above)
- `SEASON_FALLBACK` is **removed** for historical fit, or is
  rewritten so it cannot resolve via a later-week or other-team
  season-union. Preferred: drop it. A player who is not on this
  team's eligible week book is `UNRESOLVED`.
- `UNRESOLVED` → that player's units do not enter; existing NULL
  contract applies.

## Week-aware continuity

`x_continuity` for game week W:

- **Prior-year side:** members / starters from the prior season's
  last REG week (or last eligible prior-season weekly snapshot).
  Prior-season completion is available before current week 1. Do
  not use a current-season snapshot.
- **Current side:** week-aware membership at the cutoff (not the
  current-season union).
- A prior starter who is not on the current week-aware book and not
  on this week's usable listings is a departure.
- If the prior-year weekly book is missing: `continuity_source =
  UNKNOWN`, `x_continuity = None` (existing E-1). Never fill 0.
- If the current week-aware book is missing: same — UNKNOWN, not
  "no departures".

## Missing evidence → missing / ineligible (never invented)

| missing thing | result |
| --- | --- |
| no eligible weekly roster for (season, week, team) | identity books empty; listed players UNRESOLVED unless a look-back row exists; game may be incomplete |
| no eligible depth for a listed, identity-resolved player | that player's `value` is missing; do not default depth=2 |
| no eligible prior-year weekly book | `x_continuity` UNKNOWN / None |
| season snapshot is the only roster file on disk | that season is ineligible for roster-derived features |
| timestamp missing or naive | row refused (existing B-4c), not coerced |

No "carry last known starter forward across a missing month" beyond
the explicit look-back of eligible rows. If IMV wants a maximum
look-back window (e.g. 2 weeks), that is an acceptance parameter
defaulting to **unlimited look-back, zero look-ahead**.

## Provenance required on every rebuilt row

Each game side must carry:

- `roster_source` (uri / pin)
- `roster_as_of` (availability_ts of the membership book used)
- `depth_source` / `depth_as_of`
- `n_members_week_aware`
- `n_listed_unresolved`
- `n_listed_missing_depth`
- `continuity_source` (existing) plus `continuity_as_of`
- `prediction_cutoff`

A rebuild without these fields is not week-aware under this spec.

## Refit (Phase 2 only, after IMV accepts)

- Reconstruct week-aware inputs with the provenance above.
- Fit only on approved pre-2024 development data (existing
  `FIT_YEARS` ∩ years with eligible weekly sources).
- Years without weekly sources are dropped, not snapshot-filled.
- Reevaluate earlier pre-2024 / le2023 findings. Mark leakage-
  invalidated results superseded (inventory list). Do not compare
  a new fit to `a38a55bb` as a correctness target.
- Test on synthetic cases in `synthetic-cases/` plus approved
  development data. Holdout stays sealed.
- Frozen C-1 pins stay untouched until IMV accepts a new fit object.

## Out of scope until IMV accepts

- production refit
- holdout open
- writing `holdout-once.lock`
- merging / deploying / publishing
- un-disabling injury overlays
