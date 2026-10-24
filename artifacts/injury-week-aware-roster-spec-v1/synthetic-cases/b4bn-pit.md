# Synthetic case — B-4b(n)-PIT

Years 2098 / 2099 only. Mirrors 2023 PIT: the only roster file is a
week-19 WC snapshot; week-1 REG actives are absent from week-1 rows.

## Input (builder must accept this shape and treat it as ineligible)

`roster_2098.csv` — one row per player, same columns as nflverse
season snapshots:

| season | team | gsis_id | full_name | position | depth_chart_position | week | game_type | status |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- |
| 2098 | PIT | 00-SYN-QB1 | Syn Pickett | QB | QB | 19 | WC | ACT |
| 2098 | PIT | 00-SYN-QB2 | Syn Rudolph | QB | QB | 19 | WC | ACT |
| 2098 | PIT | 00-SYN-RB1 | Syn Harris | RB | RB | 19 | WC | ACT |
| 2098 | PIT | 00-SYN-CUT | Syn CampCut | WR | WR | 1 | REG | CUT |

Listings for 2098 week 1 PIT include `00-SYN-QB1` out, timestamp
before kickoff.

Game: 2098 week 1 REG, kickoff before any week-19 instant.

## Current collapse (must fail)

`load_rosters` / `load_rosters_dir`:

- `00-SYN-QB1` and `00-SYN-QB2` both depth 1, both
  `is_qb1_out_candidate`
- `00-SYN-RB1` on the week-1 team book
- `00-SYN-QB1` `TEAM_MATCH` on week 1
- out-QB applies leaked QB1 value at week 1

## Week-aware required result

- no eligible weekly REG row for QB1 / QB2 / RB1 at week 1
- identity UNRESOLVED (or not a member)
- no QB1-out floor
- no `value` from the WC snapshot
- `00-SYN-CUT` is a week-1 REG row with status CUT: not an active
  member, not a starter
- provenance records `roster_as_of` empty / ineligible, not week 19

A rebuild that "passes" by dropping PIT week 1 from the sample
without marking it ineligible is not a pass.
