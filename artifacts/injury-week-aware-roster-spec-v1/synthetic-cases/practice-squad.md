# Synthetic case — practice-squad promotion

Years 2098 / 2099.

Player `00-SYN-PS` :

- weeks 1–8 REG: status DEV (practice squad), no 53-man membership
- week 9 REG: promoted, status ACT, availability_ts = Tuesday 12:00 UTC
  before week-9 Sunday kickoff
- week 10+: ACT

## Required

| week | member of 53? | eligible starter? | `value` applied if listed |
| ---: | --- | --- | --- |
| 4 | no | no | no |
| 9 (kickoff after Tuesday ts) | yes | only if weekly depth says so | only if depth eligible |
| 9 (if a fixture kickoff is before Tuesday ts) | no | no | no |

A season snapshot that lists the player as ACT at week 18 must not
make them a week-4 member.

`STARTER_SLOTS` must not turn a DEV running-back slot into depth 1
for the whole season.
