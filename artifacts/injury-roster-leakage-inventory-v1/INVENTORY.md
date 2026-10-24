# Phase 0 — season-level roster leakage inventory

Decision: Ryan t4344u OPTION B, sha8 `47afd7f6`
(`evidence/DECISION_RYAN_t4344u_OPTION_B_WEEK_AWARE_ROSTERS_v1_a03c.txt`).
IMV lock: `0feec57e` B-4b(n)-PIT.

Frozen script pin: `8d188da2` (`run_injury_residual_fit.py`).
Builder pin: `247744d2` (`holdout_frozen_row_builder.py`).
Writer pin: `9947b880` (`write_sealed_injury_export_ts_v1.py`).
Null-contract identity helper: `ff8e6527` `resolve_fit_player_identity`.
Fit object (downstream of this leak): `6a5490db`.
Path-1 export (downstream of this leak): `a38a55bb`.

## What the source file actually is

Pinned raw input `roster_YYYY.csv` (v6 package
`seeded/raw-le2023/rosters/`, years 2012–2023) is **not** a weekly panel.

Verified on 2013–2023 (approved development years only):

- exactly **one row per (team, gsis_id)** every year
  (`n_rows == n_unique_team_pid` for all 11 years)
- columns include `week`, `game_type`, `status`, `depth_chart_position`
- the `week` / `game_type` pair is the snapshot stamp, usually the
  player's last recorded week (week 17/18 REG or week 18–22 playoff)

2013–2023 totals (`evidence/empirical-lookahead-le2023.json`):

| count | n |
| --- | ---: |
| rows | 31123 |
| week-1 REG rows | 1565 |
| not week-1 REG | 29558 |
| playoff game_type (WC/DIV/CON/SB) | 11086 |
| starter-slot rows that are not week-1 REG | 13356 |

`load_rosters()` / `load_rosters_dir()` never read `week`, `game_type`,
or `status`. The collapse key is `(year, team, pid)`. Starter rule:
`d = 1` if `depth_chart_position in STARTER_SLOTS` else `2`; upgrade-only
to 1. That single late snapshot is then applied to **every** week of
the season.

Confirmed by extracting `def load_rosters` from script `8d188da2`:
the substring `week` does not appear in the function.

## How future information enters each feature

### 1. Membership / identity (season-union)

`roster_by_team[year][team]` and `roster_season[year]` are unions of
every snapshot row for that year. A week-19 wild-card active, a week-1
camp cut, and a November signing are all "on the team" for week 1.

`resolve_fit_player_identity` (`ff8e6527`, lines 658–688) consumes those
books:

- `TEAM_MATCH` if pid ∈ season-union of that team
- `SEASON_FALLBACK` if pid ∈ season-union of any team that year
- else `UNRESOLVED`

A week-1 listed player who only exists on a week-19 snapshot resolves
as if they were on the week-1 roster. That gates whether injury units
are applied or nulled.

**Future leak:** later-week / playoff membership.
**le2023 fit evidence invalidated:** yes, for any claim that depends on
identity resolution counts or on units that pass the identity gate.

### 2. Replacement quality (`player["value"]`, depth, QB1)

`precompute_games` (`8d188da2` 466–484):

```
meta = depth.get((season, team, row["player_id"])) or {}
depth_n = int(meta.get("depth") or 2)
value = _structural_index(pos, depth_n)
is_qb1_out_candidate = pos == "QB" and depth_n == 1
```

`depth` is the season-collapsed map. `_structural_index` maps
(position, depth 1 vs 2) to a replacement-quality weight. `side_units`
multiplies missing availability by that leaked `value`. QB1 floor uses
the leaked `is_qb1_out_candidate`.

Because `STARTER_SLOTS` includes the token `"QB"`, **every** player with
`depth_chart_position == "QB"` is depth 1. On the 2023 PIT week-19 WC
snapshot that makes Kenny Pickett, Mason Rudolph, Mitchell Trubisky, and
Trace McSorley all QB1 candidates at once.

**Future leak:** later-week starter slot and later-week membership.
**le2023 fit evidence invalidated:** yes, for `value`, depth, QB1 floor,
and every residual that uses them.

### 3. Continuity (`x_continuity`)

`continuity_for_team` (`8d188da2` 355–396):

- `prior` = season-union of `season-1` (prior year; temporally complete
  before current week 1 — not B-4b(n) look-ahead by itself)
- `current_ids` = season-union of **current** season (`precompute_games`
  489)
- a prior-year starter who is absent from `current_ids` and from this
  week's listings counts as a departure

A November signing or a week-19 playoff active is in `current_ids` at
week 1, so a real week-1 departure is hidden. Depth used to decide
"was a starter last year" is the prior-year collapse (any-week starter
wins). That prior-year collapse is crude but not current-season
look-ahead.

**Future leak:** current-season membership via `current_ids`.
**le2023 fit evidence invalidated:** yes, for `x_continuity` and for
Spec C selection that used it.

### 4. Injury status / `n_lag_out` (IMV judged safe)

Listings are keyed `(season, week, team)` and clipped by
`last_report_before_kickoff`. `n_lag_out` counts listing weeks in
`[week-5, week-1]`. IMV judged injury status / continuity-of-listing
safe. This inventory does not reopen that judgment.

Secondary coupling: leaked identity can still decide whether a
week-safe listing is applied or nulled. Treat listing-as-of as safe;
treat "listing units after identity/depth" as not safe.

### 5. Producer "pre-kickoff only" claim (false for rosters)

`holdout_delta_producer.py` documents "pre-kickoff information only,
with as_of <= kickoff". `_pre_kickoff_only` rejects post-game scores.
`_assert_as_of_before_kickoff` checks `listing_as_of` only. Neither
function inspects roster `week` / `game_type` / availability. The
builder docstring claims frozen `precompute_games` is the source of
`value` / `x_continuity` — true — and that source is the leak.

## Site list

See `sites.json` for the machine-readable table. Narrative:

| id | path | leak | le2023 invalidated |
| --- | --- | --- | --- |
| F-LOAD | `run_injury_residual_fit.py` `load_rosters` L289–314 | week/game_type/status ignored; season-union + any-starter-wins | yes (root) |
| F-CONT | same file `continuity_for_team` L355–396 | `current_ids` is current-season union | yes (`x_continuity`) |
| F-IDENT | same file `precompute_games` L458–464 | identity against season-union books | yes (identity gate) |
| F-VAL | same file `precompute_games` L466–485 | depth / value / QB1 from collapsed map | yes (replacement quality) |
| F-CUR | same file `precompute_games` L489–497 | passes season-union `current_ids` into continuity | yes |
| F-UNITS | same file `side_units` L534–562 | consumes leaked value / QB1 | yes (downstream) |
| F-APPLY | same file `apply_params` / `residual_from_units` L565–718 | consumes leaked units + `x_continuity` | yes (deltas / Spec C) |
| F-MAIN | same file `main` L774–778 | wires load → precompute | yes |
| B-LOAD | `holdout_frozen_row_builder.py` `load_rosters_dir` L267–302 | identical collapse | yes (same rows) |
| B-BUILD | same file `build_rows` L327–329 | calls `precompute_games` with leaked maps | yes |
| W-MAIN | `write_sealed_injury_export_ts_v1.py` L338–345 | `fit.load_rosters()` + `precompute_games` | yes (export `a38a55bb`) |
| P-CLAIM | `holdout_delta_producer.py` `_pre_kickoff_only` / `_assert_as_of_before_kickoff` | claim does not cover roster timestamps | claim false |
| I-IDENT | `nfl_injury_null_contract.py` `resolve_fit_player_identity` L658–688 | helper; leak is the books passed in | yes when books are season-unions |
| H-V3 | untracked leftover `run_injury_residual_holdout_v3.py` `load_holdout_rosters` L812–840 | same collapse; would read 2024/2025 if executed | not executed; do not run |

## B-4b(n)-PIT examples (≤2023 only)

These are rows in the **pinned** `roster_YYYY.csv` files. The fit applies
each row to every week of that season.

**2023 PIT QBs — snapshot week 19 WC** (wild-card; after REG week 18):

| name | week | game_type | status | slot | used as |
| --- | ---: | --- | --- | --- | --- |
| Kenny Pickett | 19 | WC | ACT | QB | season-long QB1 candidate |
| Mason Rudolph | 19 | WC | ACT | QB | season-long QB1 candidate |
| Mitchell Trubisky | 19 | WC | INA | QB | season-long QB1 candidate |
| Trace McSorley | 19 | WC | CUT | QB | season-long QB1 candidate |

Week-1 REG 2023 PIT rows in the same file are almost all `CUT` camp
bodies. The actual week-1 actives (Najee Harris, T.J. Watt, George
Pickens, …) appear only on the week-19 WC snapshot. Using them as
week-1 identity / depth is look-ahead. Using Rudolph's week-19 `ACT`
(he started after Pickett's late-season injury) as week-1 QB state is
the same class.

**2019 PIT QBs — snapshot week 17 REG** (end of regular season; Ben
injured, Hodges starting):

| name | week | game_type | status | slot |
| --- | ---: | --- | --- | --- |
| Ben Roethlisberger | 17 | REG | RES | QB |
| Devlin Hodges | 17 | REG | ACT | QB |
| Mason Rudolph | 17 | REG | RES | QB |

Applied to week 1 2019 this says Ben is already on reserve and Hodges
is active. That is end-of-season information.

**2022 PIT QBs — snapshot week 18 REG:** Pickett `ACT`, Trubisky `ACT`,
Rudolph `INA`. Pickett won the job mid-season; week 1 was Trubisky.
Both are season-union QB1 candidates.

2023 PIT: 101 snapshot rows, 85 not week-1 REG, 48 starter-slot rows
that are not week-1 REG.

A synthetic case that encodes this exact shape (week-19 WC snapshot
applied to week-1 REG) is specified in the Phase 1 package
`synthetic-cases/b4bn-pit.md`. The current builder would fail that
case; the week-aware rebuild must pass it.

## What le2023 evidence is superseded

Do **not** carry forward as evidence:

- Spec C parameter selection (theta / doubtful / questionable / limited /
  caps) from script `8d188da2`
- `fit_object.json` `6a5490db`
- Path-1 export `a38a55bb` and any field-wise rebuild compare against it
  (`8af44a7e`, `bc89721f`)
- F1 / F2 / pooled MAE or CLV computed from those deltas
- Opening-runner v6 "le2023 rebuild matches a38a55bb" as validation of
  a leakage-free builder
- Any claim that builder/producer inputs are "pre-kickoff information
  only" while they call `load_rosters` / `load_rosters_dir`

May still be cited, with the identity-gate caveat:

- listing `date_modified` vs kickoff (`last_report_before_kickoff`)
- `n_lag_out` from listing weeks

Untouched and not reopened here: frozen HEAD `8e2a15ac`, config
`0d491abe`, bound `049f97d6`, injury_paths QB1 constants, overlays off,
holdout sealed.

## What this package does not do

- no `holdout-once.lock`
- no 2024 / 2025 / 2026 roster or listing bytes
- no production refit
- no merge / deploy / publish
- no change to the frozen fit script on disk (inventory only)
