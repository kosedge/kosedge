# B2-PACE-v1 Phase 2.5 hardening receipt

## Locked interpretation (unchanged)

- Unit defect fixed; Train-A ΔMAE vs C0 = −0.449, 95% CI [−0.562, −0.336].
- Still trails B1: ΔMAE = +0.314, 95% CI [+0.232, +0.394].
- Calibration 0.703 → 1.013.
- Successful unit correction; **not** evidence B1 beaten; non-default research challenger.

## Commit / hash binding

- Feature commit: `0d08b963014c5c3f51378cf4c2558cf0a8e287bc`
- Prior PR HEAD: `a5ccc463c10090ae819fc6fe7beeb34139bda462`
- `fair_b2_pace_v1.py` SHA-256 @feature: `ae5a34cdc7a2d5324fe4b372e31820464c5f385fffba7583ff5ffa43cb123707`
- Same @prior HEAD: `ae5a34cdc7a2d5324fe4b372e31820464c5f385fffba7583ff5ffa43cb123707`
- Behavior unchanged feature→prior HEAD: **True**

- Incumbent exact reproduction: **True** (max_abs_diff=0.0)

## Train-A venue split

### home_site (n=3246)
- C0_incumbent_b2: n=3246; MAE=9.434; RMSE=11.863; bias=0.062; cal_slope=0.711; MAE_CI95=[9.190, 9.685]
- B2_PACE_v1: n=3246; MAE=9.002; RMSE=11.368; bias=0.651; cal_slope=1.023; MAE_CI95=[8.765, 9.236]
- B1_close_consensus: n=3246; MAE=8.724; RMSE=11.042; bias=0.392; cal_slope=1.011; MAE_CI95=[8.493, 8.965]

### neutral_site (n=337)
- C0_incumbent_b2: n=337; MAE=10.227; RMSE=12.867; bias=-3.737; cal_slope=0.657; MAE_CI95=[9.421, 11.071]
- B2_PACE_v1: n=337; MAE=9.618; RMSE=12.198; bias=-2.332; cal_slope=0.939; MAE_CI95=[8.868, 10.459]
- B1_close_consensus: n=337; MAE=8.956; RMSE=11.566; bias=0.217; cal_slope=0.984; MAE_CI95=[8.189, 9.755]

### unknown_venue (n=0)

## Neutral-HCA counterfactual (research only; not implemented)

- C0 baseline overall: n=3583; MAE=9.509; RMSE=11.961; bias=-0.295; cal_slope=0.703; MAE_CI95=[9.267, 9.749]
- C0 HCA=0 on neutrals overall: n=3583; MAE=9.458; RMSE=11.909; bias=-0.025; cal_slope=0.709; MAE_CI95=[9.219, 9.698]
- PACE baseline overall: n=3583; MAE=9.060; RMSE=11.449; bias=0.370; cal_slope=1.013; MAE_CI95=[8.823, 9.291]
- PACE HCA=0 on neutrals overall: n=3583; MAE=9.039; RMSE=11.428; bias=0.640; cal_slope=1.019; MAE_CI95=[8.807, 9.264]

- Neutral-only C0 baseline: n=337; MAE=10.227; RMSE=12.867; bias=-3.737; cal_slope=0.657; MAE_CI95=[9.421, 11.071]
- Neutral-only C0 HCA=0: n=337; MAE=9.689; RMSE=12.343; bias=-0.868; cal_slope=0.657; MAE_CI95=[8.898, 10.532]
- Neutral-only PACE baseline: n=337; MAE=9.618; RMSE=12.198; bias=-2.332; cal_slope=0.939; MAE_CI95=[8.868, 10.459]
- Neutral-only PACE HCA=0: n=337; MAE=9.390; RMSE=11.985; bias=0.538; cal_slope=0.939; MAE_CI95=[8.621, 10.215]

## Future design only: B2-PACE-NEUTRAL-v1

- Confirmed neutral: HCA=0; confirmed home: HCA=2.8696; unknown: fail closed.
- One atomic change; requires venue_status Lab data-contract migration.
- Not implemented in this phase.

## Governance

- No Test-A / pocket scoring.
- No formula change; no neutral challenger implementation.
- No merge / deploy / promotion.

