# CURSOR ADDENDUM t5160u — loader-boundary RETURN-FIX

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5160u supersedes Cos ONE DEV **5d029306**.
OWNER t5162u RECONCILE CLOSED Cos **3c978ef9**. Same draft **#701**.
STOP for Alex append-preflight ORDER **b8cc05b2**. Cos binds after
append-GO. HARD END 02:30 EST / 07:30Z.

Implementation tip **79341557deac522b7b939d4c394590d21b6d8a3a**.

## Reconcile (actual)

| Item | State |
| --- | --- |
| `data/ops/nfl-t5155u-r5-phase2/ONE_RUN.json` | **MISSING** — never created |
| `ONE_RUN.json.claim.*` / `.result.*.json` | **none** |
| Claim **4fa6d856** | UNSPENT / never machine-CLAIMED / CONSUMED |
| `--score --cos-bind` after 5d029306 | **not run** |
| Target labels READ | **0** |
| Metrics COMPUTED / result WRITTEN | **no** |
| Base tip / stamp | `05fbb36e` / `a1d7182c` |

Do not create / reset / rebind ONE_RUN. Do not run `--score`.

## Protocol deviation

Prior FOCUSED_TESTS at `255adf78` used `schedule_outcome_loader(ROOT)`
for IF-only + market∩96 (write=False; metrics inspected). Not a clean /
unseen / first-look claim.

- Seal: `ops/CURSOR_PROTOCOL_DEVIATION_t5160u_REAL_LABEL_EXPOSURE_v1.md`
- JSON: `data/ops/nfl-t5155u-r5-phase2/PROTOCOL_DEVIATION.json`
- Later synthetic switch: `bfd3cbdc0`

## Loader boundary

Real `schedule_outcome_loader` requires **both** `claimed_bind` and
`bind_path`, then live `load_one_run` status **IN_PROGRESS**, claim
file present, and live code/input/spec/forecast/cohort hash match.
Env flags (`T5157U_ALLOW_REAL_LOADER`, `T5151U_SKIP_NESTED_TESTS`)
cannot authorize. Unbound default / CLI `--score` without valid bind /
direct real loader / forged bind / unclaimed BOUND record → 0 schedule
opens.

Bound positive proof in FOCUSED_TESTS = **synthetic fixture only**.

## Append B1 / B2 (Cos `b33cf2a0` · Alex `d6adeece` · ACCEPT `3206fd15`)

B1: if `outcome_loader is not None` OR `invoke_outcome_after_gates=True`
and `cos_bind_path is None` → refuse **before** any loader call (0
reads). OutcomeReadSpy and bare callable both refuse.

B2: bound caller-supplied `outcome_loader` refused unless explicit
test-only synthetic marker (`synthetic_outcome_loader` /
`mark_test_synthetic`). Real labels only via `schedule_outcome_loader`
after verified claimed hash-matching bind. Env flags never authorize.

## Frozen bytes (unchanged)

IF `96d3aa6f` · Q2 `eeb6fff7` · CANDIDATE `2f9a73e6` · IDENTITY
`561ae3e1` · market∩96 `072e99e0` / `558fbfe5` · REG496 `6429f859`.

No regenerate / retune / cohort / weight / selection. CERT=0. Not EVAL.
Not GREEN.

**STOP for Alex append-to-existing-preflight (ORDER b8cc05b2).**
