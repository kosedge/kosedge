# EVAL_ONELOOK_Q2PB_t5009u — DEV_RESEARCH

**CERT=0 · NFL NO-GO · DEV_RESEARCH · k: 0→1 · no post-EVAL tuning**

## Verdict (reported, not accepted): **KEEP_CANDIDATE (not self-ACCEPTED)**

Keep requires ALL of 349e081e §6. This file does **not** self-ACCEPT.
Next: Alex RO → CoS.

## Identity

- frozen fit sha256 `70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571`
- frozen config sha256 `aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49`
- freeze 2026-10-31T18:08:23.133346-04:00
- λ=20.0 r=0.5
- n=1199 n_ties=4

## §6 keep gates

- Spearman ρ = 0.382690 (need ≥ +0.15)
- cluster bootstrap ρ CI = [0.327944, 0.433026] (need lo>0)
- keep_rho = True
- ΔMAE (new−WL) = -0.442614 (need improvement ⇒ mean<0)
- ΔMAE cluster CI = [-0.674436, -0.206842] (need hi<0)
- keep_mae = True
- kill Pearson corr(pm_new−pm_WL, m−pm_WL) = 0.295862 (need >0)
- keep_kill = True
- post_eval_tuning = False
- keep_all = True

## Prediction quality vs WL / constant

- MAE new/WL/const = 10.306251 / 10.748865 / 11.093694
- RMSE new/WL/const = 13.189823 / 13.810326 / 14.355291
- ΔRMSE new−WL = -0.620503; new−const = -1.165468
- Brier new/WL/const = 0.223397 / 0.236440 / 0.249351
- ΔBrier new−WL = -0.013043; new−const = -0.025954

## Sensitivity

- week-cluster Spearman boot CI = [0.336003, 0.427078]
- bootstrap B=10000 seed=4918 n_clusters=160

## Leave-one-season-out (sign stability; not a re-threshold)

- 2018: n=240 ρ=0.3750 ΔMAE=-0.3663 kill=0.3063
- 2019: n=240 ρ=0.4135 ΔMAE=-0.3874 kill=0.2766
- 2020: n=240 ρ=0.3712 ΔMAE=-0.1966 kill=0.2120
- 2021: n=240 ρ=0.4291 ΔMAE=-1.0216 kill=0.3872
- 2022: n=239 ρ=0.3124 ΔMAE=-0.2404 kill=0.2685

## Prohibited (honored)

- no 2017 / 2023 / 2024–25 in fits or EVAL rows (2017 history-only for 2018 prior)
- no scored reuse of hist index `1ee90fac` as experiment frame
- no trailing_* / S1 / EPA-trail revive; EPA SKIPPED/UNAVAILABLE
- no math/eval rule change; no merge/deploy/pub/bet

No self-ACCEPT of keep. Alex RO → CoS.
