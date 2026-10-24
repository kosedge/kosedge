# B-4b(n)-PIT named rows (≤2023)

Source: pinned `roster_YYYY.csv` on
`origin/cursor/nfl-injury-holdout-opening-runner-v6-1a07`
`artifacts/injury-holdout-opening-runner-v6/seeded/raw-le2023/rosters/`.
Holdout years were not read.

These rows are the only PIT-QB rows in those files. The fit applies
each one to every week of that season because `week` is ignored.

## 2023 (file sha `f98283e6`) — snapshot week 19 WC

| name | gsis_id | week | game_type | status | slot |
| --- | --- | ---: | --- | --- | --- |
| Kenny Pickett | 00-0038102 | 19 | WC | ACT | QB |
| Mason Rudolph | 00-0034771 | 19 | WC | ACT | QB |
| Mitchell Trubisky | 00-0033869 | 19 | WC | INA | QB |
| Trace McSorley | 00-0035146 | 19 | WC | CUT | QB |

Week-1 REG 2023 PIT rows in the same file are camp `CUT`s (Aron
Cruickshank, B.T. Potter, …). Actives such as Najee Harris
(`00-0036893`), T.J. Watt (`00-0033886`, status `INA` on the week-19
row), George Pickens (`00-0037247`) exist only on the week-19 WC
snapshot.

2023 PIT: 101 rows, 85 not week-1 REG, 48 starter-slot rows not
week-1 REG.

## 2019 (file sha `b00259cf`) — snapshot week 17 REG

| name | gsis_id | week | game_type | status | slot |
| --- | --- | ---: | --- | --- | --- |
| Ben Roethlisberger | 00-0022924 | 17 | REG | RES | QB |
| Devlin Hodges | 00-0035577 | 17 | REG | ACT | QB |
| Mason Rudolph | 00-0034771 | 17 | REG | RES | QB |

End-of-season state (Ben on reserve, Hodges active) applied to week 1.

## 2022 (file sha `86471959`) — snapshot week 18 REG

| name | gsis_id | week | game_type | status | slot |
| --- | --- | ---: | --- | --- | --- |
| Kenny Pickett | 00-0038102 | 18 | REG | ACT | QB |
| Mitchell Trubisky | 00-0033869 | 18 | REG | ACT | QB |
| Mason Rudolph | 00-0034771 | 18 | REG | INA | QB |

Pickett won the job mid-season. Week 1 2022 was Trubisky. Both are
season-union QB1 candidates under the current rule.
