# CURSOR ADDENDUM t5151u / t5153u — numerical + integration RETURN-FIX

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5151u **d6aa1ef5** · Cos ORDER B+integration **d821fe61**
OWNER AMEND **cd253f7a** · Cos ORDER RETURN **42b6e832**
Alex RETURN **7057e5a9** ACCEPTED **ee23cc57**
Cos ACCEPT scoped **96908853**
Reuse: R4 REG-only 496 tip **bc1b62fc** · #698 · Alex **274cf246**
Package A tip **42ff285c** · stamp **f7ec09ee** · manifest **c61ca694** · PR **#699**
(not rewritten).

PARTIAL plumbing only (not integrated VERIFIED): tip **ac35ed55** · stamp
**bad20494**. RETURN-FIX implementation tip **12ccc482db54dd53bc6d79cea5f4af01c5540950**.

Starting points: #693 `eval_result_contract.py` + `metric_cohorts.py`; #698
`last_played_cohort.py`; A hooks in `cohort_enforcement.py`.
Worker B = single integration owner. Package A cohort files are not rewritten
here.

No merge. No prod default. No real EVAL. No GREEN. No self-ACCEPT.
**STOP — awaiting Alex independent re-RO.** CERT=0.

## Exact offline command

```
python3 scripts/nfl/run_nfl_t5151u_verify_integrate.py
```

Receipt: `data/ops/nfl-t5151u-verify-integrate/RECEIPT.json`

The command is one path: pin/hash accepted 496 + 502 + published DEV437
(`66c3bde1`) + matched72 (`#693` tip `316345fa`) + A manifest → A cohort
gates → B numerical checks on saved rows / saved intervals → focused tests →
one receipt. A payload flag cannot disable exact profile n/IDs. Synthetic
`n=2` substitutes are test-helper only. Nonzero failure prevents
VERIFIED/final output (`verified: false`). Failures cannot leave a success
receipt.

## Why RETURN (source-inspected; now fixed)

- Normal command previously used synthetic `n=2` (`if437[:2]`, `market72[:2]`)
  and disabled expected-ID checks when `payload["synthetic"]` was true.
- Helper invented intervals `point±.25`.
- Receipt code/spec/input/output hashes were salted with absolute paths (R1).
- Prettier failed on this addendum.

## Phase B — numerical contract

`eval_result_contract.py` is the #693 presence contract **strengthened**:

- required numerics must be finite (null / NaN / infinity fail)
- counts, season sums, and cohort IDs must agree
- exact profile counts/IDs are always enforced: 437 = 210+227, 72 = 35+37
- `synthetic=true` is refused on the normal validators
- achieved statistics are recomputed from the **same** saved per-game rows
- compare with tolerance `1e-9 * max(1, abs(expected))`
- recorded values are never rewritten to obtain PASS
- interval **metadata/points** are checked against the frozen contract
  (`B=10000`, seed `20261101`); intervals are not independently rerun
- MARKET72 joins saved 437 per-game rows to the exact saved 72 market
  points/IDs and checks identity + actual-margin consistency
- no new forecasts, fit, scoring look, fabricated intervals, or rewritten
  historical results

Profile-specific:

| Profile                | Rule                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| `FEATURE_RECON_REG496` | feature/source lineage + 27-field completeness; no invented metrics                                        |
| `DEV_IF437`            | market explicitly unavailable (`NOT_READY`); cannot satisfy `DEV_MARKET72`                                 |
| `DEV_MARKET72`         | candidate / IF / market MAE RMSE bias; paired signed mean abs-loss diffs vs both controls; saved intervals |

No performance threshold or scientific criterion change.
R2-C `DATA_COVERAGE_BLOCKED` / R3 STOP / Stage C / paid pauses unchanged.
Numeric-price normalization package is not reopened.

## Phase C — scoped caller

`verify_integrate.run_scoped_research_verify`:

1. A `check_cohort_before_feature_output_finalization` (and
   `guarded_finalize_feature_output` writes only after that gate; protected
   originals are never written)
2. A `check_cohort_before_target_outcome_loading` (never calls the outcome
   loader)
3. B `validate_profile_output` before receipt publication
4. Optional synthetic-positive `invoke_outcome_after_gates` invokes the spy
   **after** gates pass (ordering proof). Normal command leaves this false —
   no real EVAL.

Spies: cohort / hash / coverage / numerical refusal read **zero** target
scoring outcomes. The scoped path always receives a loader; a wrapper that
never calls a loader on any path is not the proof.

Receipt binds every consumed real artifact’s bytes (repo-relative POSIX path

- per-file sha256) and each profile’s joined-row / cohort hash. Interpreter
  path and HEAD are recorded separately and excluded from `output_sha256`.

## Required proofs

Complete command re-ran at tip `12ccc482db54`. Result:
`CHECKS_PASSED_AWAITING_ALEX_RO` · `verified: false` · focused tests **58
passed** (12 A + 20 numerical + 18 verify-integrate + 8 t5149u). Do **not**
treat `ac35ed55` / `bad20494` as integrated VERIFIED.

| Proof                                                      | Result |
| ---------------------------------------------------------- | ------ |
| valid original 496 / 437 / 72 artifacts                    | GREEN  |
| old 502 fails REG                                          | GREEN  |
| corrected 496 passes REG                                   | GREEN  |
| 2021 REG week 18 retained                                  | GREEN  |
| full cohorts + two numerical rows → fail                   | GREEN  |
| forged synthetic flag → fail                               | GREEN  |
| mutated real metric / missing interval field → fail        | GREEN  |
| feature finalization actually guarded; originals preserved | GREEN  |
| spy after gates = 1; negatives = 0                         | GREEN  |
| repo-relative POSIX hashes; cross-root identical digest    | GREEN  |
| output hash excludes interpreter / HEAD                    | GREEN  |
| A 12/12 cohort proofs                                      | GREEN  |
| t5149u 8 last-played REG proofs                            | GREEN  |

## Preserve

| Pin                                 | sha8 / tip                                                         |
| ----------------------------------- | ------------------------------------------------------------------ |
| RETURN-FIX implementation tip       | `12ccc482db54dd53bc6d79cea5f4af01c5540950`                         |
| PARTIAL plumbing tip (not VERIFIED) | `ac35ed55a8aa1d11ecf742b9280e5483ebe95bfc`                         |
| PARTIAL plumbing stamp              | `bad2049446168f009b54b89f45d522fc803a4d7f`                         |
| Package A tip                       | `42ff285cc1be2459512af4761651ba6dfe17dc75`                         |
| Package A stamp                     | `f7ec09ee2ffcce7b130c9b858304bbe8006a4428`                         |
| Task manifest                       | `c61ca6948ecfd1ea79f785e63117cc3399725fc893be2ea398b4b91ece42bb14` |
| R4 REG-only 496                     | `bc1b62fc`                                                         |
| Original 502 historical             | `e2f3fab5`                                                         |
| REG496 artifact                     | `282f979b`                                                         |
| DEV437 result                       | `66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50` |
| matched72 result                    | `88d63eb7f6b09e967fcf60122f525c2873072aaada93bb0dab3d8c3ff17fd9ea` |
| matched72 source tip                | `316345fa`                                                         |
| Interval B / seed                   | `10000` / `20261101`                                               |
| Cos ACCEPT scoped                   | `96908853`                                                         |
| OWNER AMEND / Cos ORDER RETURN      | `cd253f7a` / `42b6e832`                                            |
| Alex RETURN / ACCEPTED              | `7057e5a9` / `ee23cc57`                                            |
