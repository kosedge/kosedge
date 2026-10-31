# CoS note t4890u — Card A C2/C3 soft follow-ups

- tip `49eb0c270ffec9ef712df69d5ae32b8df51b0996` (INVOKE HEAD = execution tip)
- path `data/ops/nfl-offline-if-caller-t4838u/eval_w8_t4871u_coherence_v2/`
- parent packet `eval_w8_t4871u_coherence/` tip `aa9605dc` seal `1f4ffde3` Alex RO `b5de5df1` — left sealed
- verdict `CONDITIONAL` · CONDITIONAL(#4 IF-only; scope: spread/total/wp/ML; ATS/OU NOT EMITTED, NOT TESTED)
- #4 remains CONDITIONAL. PASS_RO not claimed. No forecast math change. No tolerance retune. No spec change.

## What C2 / C3 now prove

- **C2 wp:** `test_16` second-seed home_wp overlay → J3 FAIL → BLOCKED. Same-wp overlay PASSes.
- **C2 joint ST+ML:** `test_c2_joint_st_ml_fail_closed` overlays second-seed spread_home + total_mu + fair ML on draw-1 stats. Frozen J1/J2/J5 FAIL → BLOCKED. Same-draw overlay PASSes. Expected fail-closed of existing checkers, not a new contract.
- **C3:** `PYTEST.txt` / `PYTEST.json` sealed (coherence + caller/eval suite, exit 0). Evidence of tests ≠ #4 PASS.

## Unchanged from parent (honest)

- A FAIL: none · B FAIL: none
- B COND: CLE@PIT J7_S; MIN@DET J7_S; LAC@LAR J7; LAC@LAR J9
- J14 `NOT_APPLICABLE_NOT_EMITTED`

NFL NO-GO · CERT=0.
