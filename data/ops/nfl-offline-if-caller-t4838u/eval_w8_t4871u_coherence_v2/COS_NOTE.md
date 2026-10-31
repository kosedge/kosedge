# CoS note t4890u — Card A C2/C3 soft follow-ups

- tip `e603edbaa38c7d74ed2a445184a4583fda9cc1ed` (INVOKE HEAD = execution tip)
- path `data/ops/nfl-offline-if-caller-t4838u/eval_w8_t4871u_coherence_v2/`
- parent packet `eval_w8_t4871u_coherence/` tip `aa9605dc` seal `1f4ffde3` Alex RO `b5de5df1` — left sealed
- verdict `CONDITIONAL` · CONDITIONAL(#4 IF-only; scope: spread/total/wp/ML; ATS/OU NOT EMITTED, NOT TESTED)
- clarification `fe4dc220` · parent paper `05222939` · SOURCE ONLY `52d9e909` unedited
- #4 remains CONDITIONAL. PASS_RO not claimed. No forecast math change. No tolerance retune.

## What C2 / C3 now prove

- **C2:** `test_16` invokes the same game at predeclared `SECOND_SEED_C2=148500` (not a packet seed), overlays that foreign home_wp on the original same-draw stats, and runs `table_a` + `verdict_from_tables`. J3 FAIL and packet BLOCKED. Same-wp overlay still PASSes J3 (checker discriminates). Prior test only compared numbers and never drove FAIL.
- **C3:** `PYTEST.txt` / `PYTEST.json` sealed in this packet (79 passed, exit 0). Written as `.txt` because `*.log` is gitignored. Evidence of tests ≠ #4 PASS.

## Unchanged from parent (honest)

- A FAIL: none · B FAIL: none
- B COND: CLE@PIT J7_S; MIN@DET J7_S; LAC@LAR J7; LAC@LAR J9
- J11 NOT_DECISIVE: ATL@TB, LV@NYJ, KC@DEN, CHI@SEA
- J14 `NOT_APPLICABLE_NOT_EMITTED`

## Still open (not this ticket)

1. Four B-class COND items at N=4000 — sampling noise; not a model-correction proposal.
2. ATS/OU not emitted — scope-limited.
3. Operational caller BLOCKED (through-W8 DATA ACCEPT absent).
4. #4 ≠ enterprise ≠ FREE_PUBLIC ≠ betting ≠ E1. NFL NO-GO · CERT=0.
