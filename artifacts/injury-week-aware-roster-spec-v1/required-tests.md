# Required NFL automated tests

Ryan: historical roster membership and player-role around trades,
injuries, starter replacements, and practice-squad promotions,
including synthetic cases that would have failed B-4b(n)-PIT.

All tests use synthetic years 2098 / 2099 or approved pre-2024
development data. Tests must not read 2024 / 2025 / 2026 bytes.
Expected answers are committed before the runner sha.

## L-0 Permanent cutoff

For every fixture game, every contributing roster / depth / listing /
transaction / QB / odds / weather row has
`availability_ts <= kickoff_utc`. A single violation fails the suite.

## L-1 Season snapshot cannot masquerade as weekly

A one-row-per-player file with `week=19 game_type=WC` and no weekly
panel → those rows are ineligible for REG week 1. Builder must not
emit `TEAM_MATCH` / depth / value from them. Current `load_rosters`
fails this test (that is the point).

## L-2 B-4b(n)-PIT (synthetic)

See `synthetic-cases/b4bn-pit.md`. Week-1 REG must not see week-19
WC membership, depth, or QB1. Current collapse fails. Rebuild must
pass.

## L-3 Trade membership

See `synthetic-cases/trade.md`. Player on Team A weeks 1–7, Team B
weeks 8–18. Week 3 of Team B: not a member. Week 10 of Team A: not
a member. Season-union of both clubs is a fail.

## L-4 Injury replacement / starter change

See `synthetic-cases/starter-replacement.md`. Week 1 starter QB-A.
Week 6 injury. Week 7 eligible buddy QB-B is QB1. Week 1 must still
have QB-A as the only QB1. Week 7 must not treat both as QB1.

## L-5 Practice-squad promotion

See `synthetic-cases/practice-squad.md`. Player is DEV / practice
squad through week 8; promoted week 9. Week 4: not a 53-man member,
not a starter, no replacement-quality weight. Week 9+: member only
if the promotion row's `availability_ts <=` that week's kickoff.

## L-6 Look-back allowed, look-ahead forbidden

Week 5 depth missing; week 4 eligible depth may be used if
`availability_ts(week 4) <= kickoff(week 5)`. Week 6 depth must not
be used for week 5 even if it is the only depth on disk.

## L-7 Missing → ineligible, not invented

No weekly source for a year → roster-derived fields missing /
UNKNOWN, game incomplete if the NULL contract requires it. Default
`depth=2` is a fail. `x_continuity=0` on missing prior book is a
fail (existing E-1).

## L-8 Identity season-fallback

A player on another team's week-18 snapshot must not resolve
`SEASON_FALLBACK` onto this team's week 1. Preferred: the fallback
rule is gone.

## L-9 Producer claim matches implementation

Any "pre-kickoff only" assertion must include roster / depth
`availability_ts`, not only `listing_as_of`.

## L-10 Holdout unread

Suite fails if a path under test reads a 2024 / 2025 / 2026 roster,
listing, or outcome byte. `holdout-once.lock` must remain absent.

## Development-data tests (after weekly sources exist)

Replay approved pre-2024 weeks around known trades / injuries /
promotions **only if** the weekly source has an eligible row. If
the weekly source is missing, the case is skipped as ineligible,
not filled from the season snapshot. Do not use 2024–25 events.
