# PROTOCOL DEVIATION t5160u — real schedule-label exposure

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5160u supersedes Cos ONE DEV ORDER **5d029306**.
Same draft **#701**. Base tip **05fbb36e** / stamp **a1d7182c**.

This is a protocol-deviation seal. Not a clean / unseen / first-look
claim. Link eventual authorized DEV result here when it lands. Claim
**4fa6d856** remains UNSPENT on this box. No `data/ops/nfl-t5155u-r5-phase2/ONE_RUN.json`
was created for ORDER 5d029306. No `--score --cos-bind` ran.

OWNER t5162u RECONCILE CLOSED (Cos sha8 **3c978ef9**): machine ONE_RUN
for tip **05fbb36e** NEVER CREATED; claim **4fa6d856** never
machine-CLAIMED/CONSUMED; no labels READ / metrics COMPUTED / result
WRITTEN. Next: Alex append-preflight ORDER **b8cc05b2**. Cos binds
after append-GO.

## Offending path

Engineering-path real IF-only + market∩96 scoring inside FOCUSED_TESTS.

| Item | Value |
| --- | --- |
| Offending commit | `255adf7802830bc25814a739d62f65f095216203` |
| Author time | 2026-11-01 22:45:05 −0500 |
| Stamp | `df0743697` 2026-11-01 22:45:24 −0500 |
| Test | `test_phase2_positive_invokes_loader_once_if_only_and_market96` |
| Command | `python -m pytest services/model-service/tests/test_nfl_t5155u_r5_phase2_one_exec.py -q` (also via `run_focused_tests` in verify_integrate) |
| Reader | `schedule_outcome_loader(ROOT)` → `data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv` sha `08533423` |
| write | False — no scored RECEIPT committed |
| Inspected | Yes — pytest asserted `mae_if` / `rmse_if` / `bias_if` and market bootstrap B=10000 seed 20261101 |

## Cohorts / arms

- full496 IF-only
- old437 IF-only
- new59 IF-only
- market∩96 paired IF vs market (bytes `072e99e0` / identity `558fbfe5`)
- Q2 / candidate were HOLD at that tip (IF-only contract)

R2-a `bfd3cbdc0` (2026-11-01 22:59:13 −0500) switched the positive test to
`synthetic_outcome_loader`. Real metrics from 255adf78 were already seen.

## Eventual DEV result

Bound EXEC landed under Cos ORDER **b319c428** (Alex GO **da9668eb** ·
ACCEPT **d0cc1ed6**). Machine bind_id `4eef5d1f…` · status **CONSUMED**.
Receipt: `data/ops/nfl-t5155u-r5-phase2/RECEIPT.json`.
Result seal: `ops/CURSOR_ONE_EXEC_RESULT_t5160u.md`.
This does not convert the 255adf78 exposure into a clean first-look.

## Frozen bytes (must remain)

IF `96d3aa6f` · Q2 `eeb6fff7` · CANDIDATE `2f9a73e6` · IDENTITY `561ae3e1`
· market∩96 `072e99e0` / `558fbfe5` · REG496 `6429f859`.
