# Synthetic case — mid-season trade

Years 2098 / 2099.

Player `00-SYN-TRD` is on AAA weeks 1–7 REG, BBB weeks 8–18 REG.
Weekly roster rows exist for both clubs with `availability_ts` =
that week's first kickoff.

## Required

| game | team | member? |
| --- | --- | --- |
| 2098w3 AAA | AAA | yes |
| 2098w3 BBB | BBB | no |
| 2098w10 AAA | AAA | no |
| 2098w10 BBB | BBB | yes |

Season-union (current collapse) would put the player on both clubs
for all weeks. That is a fail.

Identity `SEASON_FALLBACK` must not resolve the player onto the
wrong club at the wrong week.

If the week-8 BBB row's `availability_ts` is after week-8 kickoff
(announced Tuesday after a Monday game, etc.), week 8 BBB is not
yet a member; week 9 is.
