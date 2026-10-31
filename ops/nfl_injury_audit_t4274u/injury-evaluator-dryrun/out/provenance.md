# Provenance — injury residual evaluator dry-run

No secrets. Command line below is the complete invocation.

## Decisions / messages

- Ryan t4315u / decision `d6fca6f0`: holdout STOPPED. No CLEAR. No 2024–25.
- Ryan t4317u / decision `5c4e6578`: submission-readiness gate (a)–(e).
- Standing principle t4320u: reusable automated package checker.
- Spec: IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt sha `a156459b` (v2 unused).

## Code

- Frozen-fit HEAD (C-1): `8e2a15ac581277ecda71ea745c3b3477185d733b`
- Run HEAD: `2241af8e9dcc1b6446ba4b0b9e73ab159762b05a`
- Evaluator: `/workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/run_injury_residual_evaluator.py`

## Inputs (seeded; checker dies if missing or wrong sha)

- Spec store: `/cursor/stores/self/imv-inputs/IMV_SPEC_NFL_INJURY_ADJUSTMENT_TESTS_v1.txt` sha256 `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`
- Sealed export: `/opt/cursor/artifacts/injury-fit-le2023/sealed_injury_export.json` sha256 `d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8`
- Fit object: `/opt/cursor/artifacts/injury-fit-le2023/fit_object.json` sha256 `6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657`
- Fit script (not executed): `/opt/cursor/artifacts/injury-fit-le2023/run_injury_residual_fit.py` sha256 `8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c`
- OOS (season<=2023 only; 2024+ skipped before store): `/workspace/data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv`
- Seed: `2708041115` (`int("a156459b", 16)`)
- n_boot: `10000`
- Unshrunk σ: `9.8`

## Command (no secrets)

```
python3 /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/run_injury_residual_evaluator.py --out /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-dryrun/out --cohorts synthetic_inconclusive,synthetic_fail,synthetic_pass,le2023
```

## Environment pins

- NFL_TOTALS_*: unset (none found)
- WEEK1_KEI_PUBLISH_MUTATE_FAIR: not set by this runner
- Overlays: off (this runner does not enable any overlay)
- Close proxy label: comparative research, not certified CLV
- Tokens: none created (no RYAN_CLEAR, no IMV_PASS)

## Cohort decisions (this run)

- `synthetic_inconclusive`: **INCONCLUSIVE** (expected INCONCLUSIVE)
- `synthetic_fail`: **NO CLAIM** (expected NO CLAIM)
- `synthetic_pass`: **VALUE PROVEN** (expected VALUE PROVEN)
- `le2023`: **NO CLAIM** (expected legal I-4 outcome only)

## I-5

No product claim. VALUE PROVEN on synthetic_pass is a known-answer fixture only.
le2023 is comparative research, not certified CLV, not the sealed holdout.

