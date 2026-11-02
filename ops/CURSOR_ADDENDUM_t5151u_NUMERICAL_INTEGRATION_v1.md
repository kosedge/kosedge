# CURSOR ADDENDUM t5151u — numerical output contract + integration owner

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5151u **d6aa1ef5** · Cos ORDER B+integration **d821fe61**
Cos ACCEPT scoped **96908853**
Reuse: R4 REG-only 496 tip **bc1b62fc** · #698 · Alex **274cf246**
Package A tip **42ff285c** · stamp **f7ec09ee** · PR **#699** (merged, not rewritten)
Implementation tip **ac35ed55a8aa1d11ecf742b9280e5483ebe95bfc**.
Starting points: #693 `eval_result_contract.py` + `metric_cohorts.py`; #698 `last_played_cohort.py`
Worker B = single integration owner. Package A cohort files are not rewritten here.

No merge. No prod default. No real EVAL. No GREEN. No self-ACCEPT.
**STOP — awaiting Alex independent RO.** CERT=0.

## Exact offline command

```
python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py
```

Receipt: `data/ops/nfl-t5151u-verify-integrate/RECEIPT.json`

The command is one path: verify pinned accepted artifacts → focused tests →
scoped research caller (A cohort gates then B numerical checks) → one receipt.
Nonzero failure prevents VERIFIED/final output (`verified: false`).

## Phase B — numerical contract

`eval_result_contract.py` is the #693 presence contract **strengthened**:

- required numerics must be finite (null / NaN / infinity fail)
- counts, season sums, and cohort IDs must agree
- achieved statistics are recomputed from the **same** saved per-game rows
- compare with tolerance `1e-9 * max(1, abs(expected))`
- recorded values are never rewritten to obtain PASS
- interval **metadata/points** are checked against the frozen contract
  (`B=10000`, seed `20261101`); intervals are not independently rerun

Profile-specific:

| Profile | Rule |
| --- | --- |
| `FEATURE_RECON_REG496` | feature/source lineage + 27-field completeness; no invented metrics |
| `DEV_IF437` | market explicitly unavailable; cannot satisfy `DEV_MARKET72` |
| `DEV_MARKET72` | candidate / IF / market MAE RMSE bias; paired signed mean abs-loss diffs vs both controls; per-season tables; saved game + week 95% interval metadata |

No performance threshold or scientific criterion change.
R2-C `DATA_COVERAGE_BLOCKED` / R3 STOP / Stage C / paid pauses unchanged.
Numeric-price normalization package is not reopened.

## Phase C — scoped caller

`verify_integrate.run_scoped_research_verify`:

1. A `check_cohort_before_feature_output_finalization`
2. A `check_cohort_before_target_outcome_loading` (never calls the outcome loader)
3. B `validate_profile_output` before receipt publication

Spies: cohort / hash / coverage refusal reads **zero** target scoring outcomes.
EVAL paths in this package are synthetic tests only.

## Required proofs (still green after integrate)

Complete command ran once after implementation tip `ac35ed55`. Result:
`CHECKS_PASSED_AWAITING_ALEX_RO` · `verified: false` · focused tests **42 passed**
(12 A + 14 numerical + 8 verify-integrate + 8 t5149u).

| Proof | Result |
| --- | --- |
| old 502 fails REG | GREEN |
| corrected 496 passes REG | GREEN |
| 2021 REG week 18 retained | GREEN |
| byte-change fails before outcome loader | GREEN |
| blocked coverage → spy ZERO target outcomes | GREEN |
| numerical failure cases (null/NaN/inf, missing market, inconsistent counts) | GREEN |
| positive controls (recon lineage, IF-only unavailable, MARKET72 consistency) | GREEN |
| A 12/12 cohort proofs | GREEN |

## Preserve

| Pin | sha8 / tip |
| --- | --- |
| Implementation tip | `ac35ed55a8aa1d11ecf742b9280e5483ebe95bfc` |
| Package A tip | `42ff285cc1be2459512af4761651ba6dfe17dc75` |
| R4 REG-only 496 | `bc1b62fc` |
| Original 502 historical | `e2f3fab5` |
| REG496 artifact | `282f979b` |
| Task manifest | `c61ca694` |
| Interval B / seed | `10000` / `20261101` |
| Cos ACCEPT scoped | `96908853` |
