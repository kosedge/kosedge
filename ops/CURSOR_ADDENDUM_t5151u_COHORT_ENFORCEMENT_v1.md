# CURSOR ADDENDUM t5151u — Package A cohort enforcement

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5151u **d6aa1ef5** · Cos ORDER A **78db0e76**
Parent: R4 REG-only 496 ACCEPTED tip **bc1b62fc** · stamp **c58ec422** · #698 DRAFT
Alex PASS_RO **274cf246** · Cos ACCEPT **12570bcb**
Window: Nov1 21:15→00:15 EST · HARD END 05:15Z
**STOP for integration owner (Worker B).** CERT=0. Not VERIFIED. Not ACCEPTED.

## What this is

Isolated **Package A** (cohort only). Worker A. Max 2 workers.

Freeze **one** versioned task manifest **before** verification. Named profiles
reuse accepted identity/hash records. Shared hooks are callable before
feature-output finalization and before target-outcome loading. Worker B wires
them and owns numerical strengthening of `#693` `metric_cohorts.py` /
`eval_result_contract.py`.

No new model fitting, predictions, accuracy experiment, EVAL execution,
raw-source reconstruction, NFL GREEN claim, merge, deploy, or secrets.

## Reuse (not rebuilt)

| Item | Pin |
| ---- | --- |
| `#698` `last_played_cohort.py` | reused; not rewritten |
| Original 502 (historical) | `e2f3fab5255430aa31232c7aa3b88e9001461595ef79a00fb3f1e505e51e23b9` |
| Frozen REG schedule | `schedule_results_2020_2023.csv` `0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479` |
| Membership rule | `season_type=REG` (not `week<=18`) |
| REG-only 496 artifact | `282f979b52890c7ed943eeb9c0836dd7f50b9a925cf3e82fdfc856834646402c` |
| DEV REG 437 identity | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| matched72 file | `9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6` |
| 2020 Wild Card exclusions | `metric_cohorts.WILDCARD_2020_W18` (exactly 6) |

Allowed lists are taken from the frozen task manifest. They are **not**
derived from the output under check. FEATURE_RECON_REG496 IDs are schedule
order (`2020_02_ATL_DAL` first), not the 496 artifact order
(`2020_02_CIN_CLE` first). Sets match; sources differ.

## Named profiles

| Profile | n | 2020 + 2021 | Identity sha256 |
| ------- | - | ----------- | --------------- |
| `FEATURE_RECON_REG496` | 496 | 240 + 256 | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| `DEV_IF437` | 437 | 210 + 227 | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| `DEV_MARKET72` | 72 | 35 + 37 | `bcf90863d8b5ffccd67c1d69e058e9174a9cdaa2a701aff9134a9ef6d9ab62b2` |

Substitution of 496 / 437 / 94 / 72 is refused (`0a49afa3` 94-DEV included).
2021 REG week 18 retained (16). Six 2020 Wild Cards rejected.

## Frozen manifest (before verification)

`data/ops/nfl-t5151u-cohort-enforcement/TASK_MANIFEST.json`

| Item | sha256 |
| ---- | ------ |
| Task manifest | `c61ca6948ecfd1ea79f785e63117cc3399725fc893be2ea398b4b91ece42bb14` |
| Accepted matched72 ID file | `9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6` |

`frozen_before_verification=true`.
`allowed_list_source=this_manifest_not_output_under_check`.

## Hooks (Worker B wires)

```
check_cohort_before_feature_output_finalization(...)
check_cohort_before_target_outcome_loading(...)
```

File: `services/model-service/src/services/nfl_t5107u/cohort_enforcement.py`

Checks: uniqueness; exact set membership vs manifest; season/type on the
frozen REG schedule; Wild Card exclusions; matching sample across requested
arms and actual joined rows. Reject extras, missing IDs, duplicates, changed
bytes. Changed frozen bytes and blocked coverage refuse **before** any
target-outcome loader is invoked. Hooks never call the loader.

Publication-time and RETRO_FIT limitations are explicit on the manifest and
on hook results (`publication_timestamp_status=unverified`,
`fit_label=RETRO_FIT`, `production_causal_claim=false`).

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_t5151u_cohort_enforcement.py \
  tests/test_nfl_t5149u_last_played_reg_cohort.py -q
```

Result: **20 passed** (12 Package A + 8 t5149u #698 positive controls).

| Proof | Result |
| ----- | ------ |
| old 502 fails REG profile | GREEN |
| corrected 496 passes REG | GREEN |
| 2021 REG week 18 retained | GREEN |
| mismatched arm IDs fail | GREEN |
| changed frozen bytes fail BEFORE outcome loader | GREEN |
| blocked coverage → spy ZERO target scoring outcomes read | GREEN |
| positive accepted 496 / 437 / 72 still pass | GREEN |
| uniqueness / extras / missing / duplicates | GREEN |
| forbid substitution 496 / 437 / 94 / 72 | GREEN |
| manifest frozen; not derived from 496 output | GREEN |
| original 502 bytes preserved (`e2f3fab5`) | GREEN |
| #698 t5149u identity tests still pass | GREEN |

Safe copies / temp only. Originals not rewritten.

## Not done (Worker B)

- Numerical strengthening of `metric_cohorts.py` / `eval_result_contract.py`
- Wiring hooks before feature-output finalization and target-outcome loading
- Combined verification / integration claim

## Holds

No merge / deploy / prod behavior change. No rewrite of frozen historical
runners/artifacts. No EVAL. No 2024–26 research. No NFL GREEN.
**STOP for integration owner (Worker B) to combine.**

CERT=0.

## Pins

| Item | Value |
| ---- | ----- |
| Implementation tip | _pending stamp_ |
| Task manifest | `c61ca6948ecfd1ea79f785e63117cc3399725fc893be2ea398b4b91ece42bb14` |
| FEATURE_RECON_REG496 identity | `6429f8596a1b605a9f1dc8aec21d81fc4454ff25e985dc77e691ec29d489c640` |
| DEV_IF437 identity | `92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49` |
| DEV_MARKET72 identity | `bcf90863d8b5ffccd67c1d69e058e9174a9cdaa2a701aff9134a9ef6d9ab62b2` |
| DEV_MARKET72 file | `9f754b0e1c7680a0051b119ec59e2f0603236be447c483491b90a70af61b81e6` |
| Original 502 preserved | `e2f3fab5255430aa31232c7aa3b88e9001461595ef79a00fb3f1e505e51e23b9` |
| REG schedule | `0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479` |
