# Synthetic case — starter replacement after injury

Years 2098 / 2099.

Weekly depth:

- weeks 1–5: QB `00-SYN-QBA` depth_order 1, `00-SYN-QBB` depth_order 2
- week 6 listing: QBA out (as_of before kickoff)
- weeks 7–18: QBB depth_order 1, QBA absent or depth_order 2

## Required

| week | QB1 pid | QBA is_qb1_out_candidate | QBB is_qb1_out_candidate |
| ---: | --- | --- | --- |
| 1 | QBA | yes if listed out | no |
| 6 | QBA (still eligible starter) | yes | no |
| 7 | QBB | no | yes if listed out |

Both QBs having `depth_chart_position=QB` must not make both QB1
in any week. That is the `STARTER_SLOTS` defect.

Week 1 must not use week-7 depth. Week 7 may look back to week 7
only (or week 6 if week 7 depth is missing and week 6 is eligible).
