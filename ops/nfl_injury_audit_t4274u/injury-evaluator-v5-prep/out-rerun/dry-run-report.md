# Evaluator v4 dry-run report (acceptance 54bc78ec / ruling 1a090e3b)

**Frozen-fit HEAD:** `8e2a15ac581277ecda71ea745c3b3477185d733b`
**Expected-answers commit:** `ffe0f88b59fb0315724298d78d7ede5e8c3c6d3a`
**SoT spec:** `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`
**Acceptance:** `54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574`
**Ruling:** `88da5f42d918a9462da01ac01fd8260f7a0d9c2cad6a587492e5b9caf41cca6b`
**Expected answers:** `656d61ec2e9c3a5e8774bbcb02f384a78eaf21fb5e000614ba1f3e6b263b0179` (filed before run)
**Seed:** `20261023` n_boot=10000 rng=numpy.default_rng
**σ_margin:** 13.5 (C-10 services/model-service/src/services/nfl_injury_null_contract.py L339-341; L410 at HEAD `8e2a15ac581277ecda71ea745c3b3477185d733b`)
**σ_total:** 14.0 (pre-registered `inputs/sigma_preregistration.md`)
**Close:** nflverse REG spread_line — comparative research, not certified CLV
**Metric label:** close vs outcome
**Holdout:** STOPPED. No CLEAR.

Command (package-relative, no secrets):

```
python3 run_injury_residual_evaluator.py --mode tests
```

## T-1..T-10

- `T-1`: **PASS** {"delta": 1.5, "mirror": -1.5, "label": "close vs outcome", "ats_base": null, "ats_adj": 1.0, "n_nopick_spread_ats_base": 3, "p_half_ats_none": true}
- `T-2`: **PASS** {"significant": ["spread_clv_delta"], "rejection_means": "SIGNIFICANT"}
- `T-3`: **PASS** {"ci": [0.01, 0.01], "bit_identical": true}
- `T-4`: **PASS** {"brier": 0.16333333333333333, "logloss": 0.49870307570903244, "bins": [3, 6, 8], "perfect_slope": 1.0000000000000002, "clip_count": 0}
- `T-5`: **PASS** {"phi": 0.5912529568183097}
- `T-6`: **PASS** {"n_pass": 501, "i2_pass": "MET", "i2_499": "INCONCLUSIVE", "i2_partial": "INCONCLUSIVE"}
- `T-7`: **PASS** {"n_missing_close": 2, "n_identical": 8}
- `T-8`: **PASS** {"flags": ["FLAG_MISSING_delta_margin", "FLAG_MISSING_delta_total", "FLAG_MISSING_baseline_margin", "FLAG_MISSING_baseline_total", "FLAG_MISSING_close_spread_home", "FLAG_MISSING_close_total", "FLAG_MISSING_actual_margin", "FLAG_MISSING_actual_total"]}
- `T-9`: **PASS** {"detected": "LEAKAGE", "kinds": ["source_after_as_of", "as_of_equals_kickoff", "as_of_after_kickoff", "unparseable", "missing"], "et_naive": true, "b3_carry": true}
- `T-10`: **PASS** {"a": "VALUE PROVEN", "b": "NO CLAIM", "b_ci": [-0.6176470588235294, 0.4411764705882353], "b_n_unique_deltas": 2, "c": "NO CLAIM", "c_ll_uci": 0.0020999999999999908, "c_k4_computed": false}

## Folds (DRY RUN - NOT A RESULT)

Folds not scored: B-3 STOP (export missing source_ts/as_of_ts). Close/outcome join was not performed.

## Hard rules

- No 2024/2025/2026 scored.
- No tokens created.
- Seed 20261023. VALUE PROVEN requires CI lo>0.
- Close vs outcome, not certified CLV.

