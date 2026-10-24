# Evaluator v3 dry-run report (acceptance 54bc78ec)

**Frozen-fit HEAD:** `8e2a15ac581277ecda71ea745c3b3477185d733b`
**Run HEAD:** `713817954719fe45dd6a1d70e42061a74dd6927b`
**SoT spec:** `a156459b545e3b7d6a483f1db34cda7a4d32fc3afc70ed499b3adc726b1b6881`
**Acceptance:** `54bc78ecc70e6a440481253b9c7eeef0e749690e893f501862f5dd5c54444574`
**Ruling:** `a0501d575a42cb4c05b2d1937753b36ca761f613e8c0d011d56fd3d05246d6e9`
**Expected answers:** `8319a63a674f22a52b1bce168c15de9e1a510429b14e78d1e4dd48f30fcd1b79` (filed before run)
**Seed:** `20261023` n_boot=10000 rng=numpy.default_rng
**σ_margin:** 13.5  **σ_total:** 14.0
**Close:** nflverse REG spread_line — comparative research, not certified CLV
**Metric label:** close vs outcome
**Holdout:** STOPPED. No CLEAR.

Command (no secrets):

```
python3 /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-v3/run_injury_residual_evaluator.py --out /workspace/ops/nfl_injury_audit_t4274u/injury-evaluator-v3/out --mode all
```

## T-1..T-10

- `T-1`: **PASS** {"delta": 1.5, "mirror": -1.5, "label": "close vs outcome"}
- `T-2`: **PASS** {"significant": ["spread_clv_delta"], "rejection_means": "SIGNIFICANT"}
- `T-3`: **PASS** {"ci": [0.01, 0.01], "bit_identical": true}
- `T-4`: **PASS** {"brier": 0.16333333333333333, "logloss": 0.49870307570903244, "bins": [3, 6, 8], "perfect_slope": 1.0000000000000002, "clip_count": 0}
- `T-5`: **PASS** {"phi": 0.5912529568183097}
- `T-6`: **PASS** {"n_pass": 501, "i2_pass": "MET", "i2_499": "INCONCLUSIVE", "i2_partial": "INCONCLUSIVE"}
- `T-7`: **PASS** {"n_missing_close": 2, "n_identical": 8}
- `T-8`: **PASS** {"flags": ["FLAG_MISSING_delta_margin", "FLAG_MISSING_delta_total", "FLAG_MISSING_baseline_margin", "FLAG_MISSING_baseline_total", "FLAG_MISSING_close_spread_home", "FLAG_MISSING_close_total", "FLAG_MISSING_actual_margin", "FLAG_MISSING_actual_total"]}
- `T-9`: **PASS** {"detected": "LEAKAGE"}
- `T-10`: **PASS** {"a": "VALUE PROVEN", "b": "NO CLAIM", "c": "NO CLAIM", "c_ll_uci": 0.0020999999999999908}

## Folds (DRY RUN - NOT A RESULT)

### `F1` — **DRY RUN - NOT A RESULT**

- I-2: `INCONCLUSIVE` n_nonzero=268 by_season={2022: 268} full=1
- I-4: INCONCLUSIVE holm=False lo>0=False k4=False
- Identical n=268 cvo-both=268 edge0 base/adj=0/0
- Missing: incomplete=3 close=0 actual=0 baseline=0
- Missing by season: incomplete={2022: 3} close={}
- Universe by season: {2022: 271}
- K-4: LLhi=0.03480947942922621 Bhi=0.017059275671194085 slope=-0.047850059564470554 pass=False ['logloss_CI_hi 0.03480947942922621 > 0.002', 'brier_CI_hi 0.017059275671194085 > 0.0005', 'slope -0.047850059564470554 outside [0.9,1.1]']

| metric | value |
|---|---|
| `spread_clv_delta` | -0.15298507462686567 |
| `spread_ats_delta` | 0.007462686567164179 |
| `spread_logloss_delta` | 0.013239128511571099 |
| `total_clv_delta` | 0.6305970149253731 |
| `total_ats_delta` | 0.014925373134328358 |
| `total_logloss_delta` | 0.027679762202454782 |
| `ml_clv_implied_prob_delta` | -0.005103637212005794 |
| `ml_ats_delta` | -0.03731343283582089 |
| `ml_logloss_delta` | 0.02171296031395593 |

Holm:

- `total_logloss_delta` p=0.0 sig=True
- `ml_logloss_delta` p=0.0018 sig=True
- `spread_logloss_delta` p=0.0154 sig=False
- `total_clv_delta` p=0.2296 sig=False
- `ml_ats_delta` p=0.3352 sig=False
- `total_ats_delta` p=0.5432 sig=False
- `spread_clv_delta` p=0.7322 sig=False
- `ml_clv_implied_prob_delta` p=0.7588 sig=False
- `spread_ats_delta` p=0.7858 sig=False
- primary CI [-1.0406017651594426, 0.7153291506055387] lo>0=False seed=20261023

#### M-1..M-5

```json
{
  "M-1": {
    "by_abs_close": [
      {
        "lo": 0,
        "hi": 3,
        "n": 72,
        "mean_base": -0.909463888888889,
        "sd_base": 11.95049838865598,
        "mean_adj": -1.128300694444445,
        "sd_adj": 12.356566428784364
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 130,
        "mean_base": 0.4401538461538462,
        "sd_base": 11.65179224786087,
        "mean_adj": 0.3749807692307694,
        "sd_adj": 12.027853365247946
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 30,
        "mean_base": 0.9626433333333334,
        "sd_base": 12.53543385188379,
        "mean_adj": 0.9772266666666664,
        "sd_adj": 12.75646715621297
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 36,
        "mean_base": 6.296483333333333,
        "sd_base": 12.267276386840841,
        "mean_adj": 6.865667361111111,
        "sd_adj": 12.596008295340205
      }
    ],
    "by_abs_delta": [
      {
        "lo": 0,
        "hi": 3,
        "n": 268,
        "mean_base": 0.9227287313432835,
        "sd_base": 12.053097732940197,
        "mean_adj": 0.9104129664179104,
        "sd_adj": 12.450430401942404
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      }
    ]
  },
  "M-2": {
    "mae_margin_base": 9.37373395522388,
    "mae_margin_adj": 9.689705130597016,
    "rmse_margin_base": 12.065923681911961,
    "rmse_margin_adj": 12.460483996867525,
    "ll_base": 0.6783938746656688,
    "ll_adj": 0.7001068349796248,
    "brier_base": 0.2425712791266551,
    "brier_adj": 0.2531568385716413,
    "mae_delta_ci": {
      "lo": 0.11295054698336851,
      "hi": 0.5104875150593008,
      "obs": 0.3159711753731343
    },
    "adj_beats_base": false,
    "null": "null"
  },
  "M-3": {
    "reliability": {
      "spread": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 1,
          "mean_p": 0.09182016538844762,
          "mean_y": 1.0,
          "nan_reason": null
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 8,
          "mean_p": 0.16996521281571614,
          "mean_y": 0.125,
          "nan_reason": null
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 28,
          "mean_p": 0.2609294336182289,
          "mean_y": 0.42857142857142855,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 57,
          "mean_p": 0.3608144639182473,
          "mean_y": 0.543859649122807,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 47,
          "mean_p": 0.4486153755338559,
          "mean_y": 0.44680851063829785,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 59,
          "mean_p": 0.5422786940116964,
          "mean_y": 0.4576271186440678,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 42,
          "mean_p": 0.6460437390254883,
          "mean_y": 0.42857142857142855,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 19,
          "mean_p": 0.7486382005597283,
          "mean_y": 0.631578947368421,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 7,
          "mean_p": 0.8337313007316081,
          "mean_y": 0.5714285714285714,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ],
      "total": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 1,
          "mean_p": 0.2996054163401123,
          "mean_y": 0.0,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 19,
          "mean_p": 0.35378800695352236,
          "mean_y": 0.42105263157894735,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 42,
          "mean_p": 0.45600018341827675,
          "mean_y": 0.42857142857142855,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 83,
          "mean_p": 0.5548616719219727,
          "mean_y": 0.4939759036144578,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 85,
          "mean_p": 0.6505828739521253,
          "mean_y": 0.4,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 35,
          "mean_p": 0.7373064752958225,
          "mean_y": 0.45714285714285713,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 3,
          "mean_p": 0.8301551084325215,
          "mean_y": 0.0,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ],
      "ml": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 1,
          "mean_p": 0.2905249292492693,
          "mean_y": 1.0,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 9,
          "mean_p": 0.38529801849262224,
          "mean_y": 0.5555555555555556,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 86,
          "mean_p": 0.46491666112308255,
          "mean_y": 0.5,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 128,
          "mean_p": 0.5500301964636254,
          "mean_y": 0.6015625,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 40,
          "mean_p": 0.6300402557506104,
          "mean_y": 0.525,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 4,
          "mean_p": 0.7331765182111385,
          "mean_y": 0.5,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ]
    },
    "slope": -0.047850059564470554,
    "intercept": {
      "note": "logistic intercept not a gate; slope is K-4"
    },
    "coverage_80": 0.8283582089552238,
    "v_note": "80% interval = pred_margin \u00b1 1.28155 \u03c3_margin; V gate reported, not a pass cut here"
  },
  "M-4": {
    "status": "NOT RUN",
    "reason": "no timestamped open for <=2023 in the deposited nflverse close table (earliest price is not a true open; pre7d absent)"
  },
  "M-5": {
    "status": "DEFERRED",
    "reason": "OOS edge survival deferred to the single holdout opening; le2023 is in-sample-adjacent and may not be cited as edge (I-5)"
  }
}
```

Baseline and adjusted used the same close-present set. Zero-edge drops CLV/ATS only.

### `F2` — **DRY RUN - NOT A RESULT**

- I-2: `INCONCLUSIVE` n_nonzero=271 by_season={2023: 271} full=1
- I-4: INCONCLUSIVE holm=False lo>0=False k4=False
- Identical n=271 cvo-both=271 edge0 base/adj=0/0
- Missing: incomplete=1 close=0 actual=0 baseline=0
- Missing by season: incomplete={2023: 1} close={}
- Universe by season: {2023: 272}
- K-4: LLhi=0.021462832035445082 Bhi=0.010546895580558336 slope=0.518638484330571 pass=False ['logloss_CI_hi 0.021462832035445082 > 0.002', 'brier_CI_hi 0.010546895580558336 > 0.0005', 'slope 0.518638484330571 outside [0.9,1.1]']

| metric | value |
|---|---|
| `spread_clv_delta` | 0.5498154981549815 |
| `spread_ats_delta` | 0.04797047970479705 |
| `spread_logloss_delta` | 0.007229004946995051 |
| `total_clv_delta` | 0.15867158671586715 |
| `total_ats_delta` | 0.0 |
| `total_logloss_delta` | 0.030427157582727696 |
| `ml_clv_implied_prob_delta` | 0.038148612755319146 |
| `ml_ats_delta` | -0.01845018450184502 |
| `ml_logloss_delta` | 0.006745745652908767 |

Holm:

- `total_logloss_delta` p=0.0012 sig=True
- `spread_ats_delta` p=0.0022 sig=True
- `ml_clv_implied_prob_delta` p=0.0118 sig=False
- `spread_clv_delta` p=0.1744 sig=False
- `ml_logloss_delta` p=0.368 sig=False
- `spread_logloss_delta` p=0.4068 sig=False
- `ml_ats_delta` p=0.5658 sig=False
- `total_clv_delta` p=0.78 sig=False
- `total_ats_delta` p=1.0 sig=False
- primary CI [-0.2362016988094409, 1.2899747840586047] lo>0=False seed=20261023

#### M-1..M-5

```json
{
  "M-1": {
    "by_abs_close": [
      {
        "lo": 0,
        "hi": 3,
        "n": 70,
        "mean_base": -1.0650357142857143,
        "sd_base": 12.299344017149219,
        "mean_adj": -1.4425982142857146,
        "sd_adj": 12.159830404298827
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 136,
        "mean_base": 2.2983838235294116,
        "sd_base": 15.021992552241139,
        "mean_adj": 2.380263419117647,
        "sd_adj": 15.298555930165348
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 38,
        "mean_base": 2.6137526315789477,
        "sd_base": 14.059383520619164,
        "mean_adj": 3.2767296052631583,
        "sd_adj": 13.738150184394609
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 27,
        "mean_base": 4.103329629629629,
        "sd_base": 14.777911158701455,
        "mean_adj": 4.2801583333333335,
        "sd_adj": 15.141270721523076
      }
    ],
    "by_abs_delta": [
      {
        "lo": 0,
        "hi": 3,
        "n": 271,
        "mean_base": 1.6536538745387455,
        "sd_base": 14.228910368382294,
        "mean_adj": 1.707800553505535,
        "sd_adj": 14.372175567380241
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      }
    ]
  },
  "M-2": {
    "mae_margin_base": 11.004528413284133,
    "mae_margin_adj": 11.126509409594096,
    "rmse_margin_base": 14.29857928474763,
    "rmse_margin_adj": 14.446930516526514,
    "ll_base": 0.6814678042239597,
    "ll_adj": 0.6882135498768686,
    "brier_base": 0.24419667757014232,
    "brier_adj": 0.24763339798862027,
    "mae_delta_ci": {
      "lo": -0.12161103509679434,
      "hi": 0.37138799562043817,
      "obs": 0.12198099630996319
    },
    "adj_beats_base": false,
    "null": "null"
  },
  "M-3": {
    "reliability": {
      "spread": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 7,
          "mean_p": 0.17102712120602273,
          "mean_y": 0.5714285714285714,
          "nan_reason": null
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 24,
          "mean_p": 0.25311252492604375,
          "mean_y": 0.375,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 59,
          "mean_p": 0.3613554456692789,
          "mean_y": 0.5423728813559322,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 64,
          "mean_p": 0.45426054041753255,
          "mean_y": 0.421875,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 50,
          "mean_p": 0.5506238434928341,
          "mean_y": 0.5,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 51,
          "mean_p": 0.6522763524506926,
          "mean_y": 0.49019607843137253,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 12,
          "mean_p": 0.7300942015341315,
          "mean_y": 0.4166666666666667,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 4,
          "mean_p": 0.821639787624737,
          "mean_y": 0.25,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ],
      "total": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 10,
          "mean_p": 0.35687036447544546,
          "mean_y": 0.2,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 41,
          "mean_p": 0.4682499607238759,
          "mean_y": 0.43902439024390244,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 69,
          "mean_p": 0.554982029823809,
          "mean_y": 0.4782608695652174,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 85,
          "mean_p": 0.6434307175395928,
          "mean_y": 0.49411764705882355,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 55,
          "mean_p": 0.7415956285606474,
          "mean_y": 0.45454545454545453,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 10,
          "mean_p": 0.8331951502356336,
          "mean_y": 0.4,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 1,
          "mean_p": 0.9069777509451635,
          "mean_y": 0.0,
          "nan_reason": null
        }
      ],
      "ml": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 2,
          "mean_p": 0.2941620770817184,
          "mean_y": 0.0,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 12,
          "mean_p": 0.3863231190632268,
          "mean_y": 0.5,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 83,
          "mean_p": 0.4624883810135488,
          "mean_y": 0.5421686746987951,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 133,
          "mean_p": 0.5515365659583279,
          "mean_y": 0.5488721804511278,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 38,
          "mean_p": 0.6338071393910526,
          "mean_y": 0.6052631578947368,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 3,
          "mean_p": 0.7189381010989969,
          "mean_y": 1.0,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ]
    },
    "slope": 0.518638484330571,
    "intercept": {
      "note": "logistic intercept not a gate; slope is K-4"
    },
    "coverage_80": 0.7822878228782287,
    "v_note": "80% interval = pred_margin \u00b1 1.28155 \u03c3_margin; V gate reported, not a pass cut here"
  },
  "M-4": {
    "status": "NOT RUN",
    "reason": "no timestamped open for <=2023 in the deposited nflverse close table (earliest price is not a true open; pre7d absent)"
  },
  "M-5": {
    "status": "DEFERRED",
    "reason": "OOS edge survival deferred to the single holdout opening; le2023 is in-sample-adjacent and may not be cited as edge (I-5)"
  }
}
```

Baseline and adjusted used the same close-present set. Zero-edge drops CLV/ATS only.

### `pooled` — **DRY RUN - NOT A RESULT**

- I-2: `MET` n_nonzero=539 by_season={2022: 268, 2023: 271} full=2
- I-4: NO CLAIM holm=False lo>0=False k4=False
- Identical n=539 cvo-both=539 edge0 base/adj=0/0
- Missing: incomplete=4 close=0 actual=0 baseline=0
- Missing by season: incomplete={2022: 3, 2023: 1} close={}
- Universe by season: {2022: 271, 2023: 272}
- K-4: LLhi=0.02430623563514729 Bhi=0.011948360682218759 slope=0.24282994807772681 pass=False ['logloss_CI_hi 0.02430623563514729 > 0.002', 'brier_CI_hi 0.011948360682218759 > 0.0005', 'slope 0.24282994807772681 outside [0.9,1.1]']

| metric | value |
|---|---|
| `spread_clv_delta` | 0.20037105751391465 |
| `spread_ats_delta` | 0.027829313543599257 |
| `spread_logloss_delta` | 0.010217340967971639 |
| `total_clv_delta` | 0.39332096474953615 |
| `total_ats_delta` | 0.0074211502782931356 |
| `total_logloss_delta` | 0.029061105705337823 |
| `ml_clv_implied_prob_delta` | 0.01664285581423736 |
| `ml_ats_delta` | -0.027829313543599257 |
| `ml_logloss_delta` | 0.014187700252464684 |

Holm:

- `total_logloss_delta` p=0.0 sig=True
- `ml_logloss_delta` p=0.0048 sig=True
- `spread_ats_delta` p=0.0316 sig=False
- `spread_logloss_delta` p=0.0512 sig=False
- `ml_clv_implied_prob_delta` p=0.1648 sig=False
- `ml_ats_delta` p=0.2438 sig=False
- `total_clv_delta` p=0.2926 sig=False
- `spread_clv_delta` p=0.499 sig=False
- `total_ats_delta` p=0.6484 sig=False
- primary CI [-0.39518385166084924, 0.7837401081520186] lo>0=False seed=20261023

#### M-1..M-5

```json
{
  "M-1": {
    "by_abs_close": [
      {
        "lo": 0,
        "hi": 3,
        "n": 142,
        "mean_base": -0.9861542253521128,
        "sd_base": 12.080867829470616,
        "mean_adj": -1.2832360915492962,
        "sd_adj": 12.217463379852125
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 266,
        "mean_base": 1.3902263157894736,
        "sd_base": 13.487553160025447,
        "mean_adj": 1.4002380639097747,
        "sd_adj": 13.808090315646064
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 68,
        "mean_base": 1.8853220588235293,
        "sd_base": 13.336254626906507,
        "mean_adj": 2.2622430147058825,
        "sd_adj": 13.265938681093001
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 63,
        "mean_base": 5.356560317460318,
        "sd_base": 13.331551107048703,
        "mean_adj": 5.757592063492063,
        "sd_adj": 13.688308952362197
      }
    ],
    "by_abs_delta": [
      {
        "lo": 0,
        "hi": 3,
        "n": 539,
        "mean_base": 1.2902254174397032,
        "sd_base": 13.184824383569905,
        "mean_adj": 1.3113258348794063,
        "sd_adj": 13.444450650055549
      },
      {
        "lo": 3,
        "hi": 7,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 7,
        "hi": 10,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      },
      {
        "lo": 10,
        "hi": 1000000000.0,
        "n": 0,
        "mean": null,
        "sd": null,
        "nan_reason": "empty bucket"
      }
    ]
  },
  "M-2": {
    "mae_margin_base": 10.193669573283858,
    "mae_margin_adj": 10.412105797773656,
    "rmse_margin_base": 13.235624398398878,
    "rmse_margin_adj": 13.495831929267185,
    "ll_base": 0.6799393939797632,
    "ll_adj": 0.6941270942322278,
    "brier_base": 0.24338850172069046,
    "brier_adj": 0.2503797469241483,
    "mae_delta_ci": {
      "lo": 0.05876133097627729,
      "hi": 0.3786169867231902,
      "obs": 0.21843622448979597
    },
    "adj_beats_base": false,
    "null": "null"
  },
  "M-3": {
    "reliability": {
      "spread": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 1,
          "mean_p": 0.09182016538844762,
          "mean_y": 1.0,
          "nan_reason": null
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 15,
          "mean_p": 0.17046077006452587,
          "mean_y": 0.3333333333333333,
          "nan_reason": null
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 52,
          "mean_p": 0.2573216296064511,
          "mean_y": 0.40384615384615385,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 116,
          "mean_p": 0.36108961842954784,
          "mean_y": 0.5431034482758621,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 111,
          "mean_p": 0.45187024537669646,
          "mean_y": 0.43243243243243246,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 109,
          "mean_p": 0.5461067442324018,
          "mean_y": 0.47706422018348627,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 93,
          "mean_p": 0.6494616238070519,
          "mean_y": 0.46236559139784944,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 31,
          "mean_p": 0.7414598783562715,
          "mean_y": 0.5483870967741935,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 11,
          "mean_p": 0.8293343868745641,
          "mean_y": 0.45454545454545453,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ],
      "total": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 1,
          "mean_p": 0.2996054163401123,
          "mean_y": 0.0,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 29,
          "mean_p": 0.3548508888576338,
          "mean_y": 0.3448275862068966,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 83,
          "mean_p": 0.46205127823188596,
          "mean_y": 0.43373493975903615,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 152,
          "mean_p": 0.55491630807478,
          "mean_y": 0.4868421052631579,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 170,
          "mean_p": 0.6470067957458591,
          "mean_y": 0.4470588235294118,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 90,
          "mean_p": 0.7399276245132155,
          "mean_y": 0.45555555555555555,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 13,
          "mean_p": 0.8324936021272232,
          "mean_y": 0.3076923076923077,
          "nan_reason": null
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 1,
          "mean_p": 0.9069777509451635,
          "mean_y": 0.0,
          "nan_reason": null
        }
      ],
      "ml": [
        {
          "bin": 0,
          "lo": 0.0,
          "hi": 0.1,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 1,
          "lo": 0.1,
          "hi": 0.2,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 2,
          "lo": 0.2,
          "hi": 0.3,
          "n": 3,
          "mean_p": 0.292949694470902,
          "mean_y": 0.3333333333333333,
          "nan_reason": null
        },
        {
          "bin": 3,
          "lo": 0.3,
          "hi": 0.4,
          "n": 21,
          "mean_p": 0.3858837902472534,
          "mean_y": 0.5238095238095238,
          "nan_reason": null
        },
        {
          "bin": 4,
          "lo": 0.4,
          "hi": 0.5,
          "n": 169,
          "mean_p": 0.4637240738503529,
          "mean_y": 0.5207100591715976,
          "nan_reason": null
        },
        {
          "bin": 5,
          "lo": 0.5,
          "hi": 0.6,
          "n": 261,
          "mean_p": 0.5507978100375541,
          "mean_y": 0.5747126436781609,
          "nan_reason": null
        },
        {
          "bin": 6,
          "lo": 0.6,
          "hi": 0.7,
          "n": 78,
          "mean_p": 0.6318754041908259,
          "mean_y": 0.5641025641025641,
          "nan_reason": null
        },
        {
          "bin": 7,
          "lo": 0.7,
          "hi": 0.8,
          "n": 7,
          "mean_p": 0.7270743394487921,
          "mean_y": 0.7142857142857143,
          "nan_reason": null
        },
        {
          "bin": 8,
          "lo": 0.8,
          "hi": 0.9,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        },
        {
          "bin": 9,
          "lo": 0.9,
          "hi": 1.0,
          "n": 0,
          "mean_p": null,
          "mean_y": null,
          "nan_reason": "bin empty; not a stub"
        }
      ]
    },
    "slope": 0.24282994807772681,
    "intercept": {
      "note": "logistic intercept not a gate; slope is K-4"
    },
    "coverage_80": 0.8051948051948052,
    "v_note": "80% interval = pred_margin \u00b1 1.28155 \u03c3_margin; V gate reported, not a pass cut here"
  },
  "M-4": {
    "status": "NOT RUN",
    "reason": "no timestamped open for <=2023 in the deposited nflverse close table (earliest price is not a true open; pre7d absent)"
  },
  "M-5": {
    "status": "DEFERRED",
    "reason": "OOS edge survival deferred to the single holdout opening; le2023 is in-sample-adjacent and may not be cited as edge (I-5)"
  }
}
```

Baseline and adjusted used the same close-present set. Zero-edge drops CLV/ATS only.

## Hard rules

- No 2024/2025/2026 scored.
- No tokens created.
- Seed 20261023. VALUE PROVEN requires CI lo>0.
- Close vs outcome, not certified CLV.

