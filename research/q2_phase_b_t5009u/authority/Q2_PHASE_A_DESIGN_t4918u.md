# Q2 Phase A — Design paper: opponent-adjusted performance-based strength (t4918u)
Status: DESIGN PAPER under standing research (OWNER AMEND t4918u). **Not EXEC. No fitting, no scoring, no data access to 2024–25.** Label: DEV_RESEARCH. NFL NO-GO · CERT=0.
Pins: control 02197f58 · SCORE_RESULTS 2b9f302e · IF 6ca03716 · contract b41f4b43 · S1 kill DECISION 20c49524 (t4707u) · direction a053cedd · superseded plan f8669da9.

## 1. Question
Does a strength estimate built from **opponent-adjusted game-level performance** (rather than raw W-L) carry home-favorable information about realized margin beyond the frozen `wl_diff` baseline, on a locked development evaluation?

## 2. Why not S1 — differences table
S1 record: FAMILY_S1_LOOKS closed FAIL (k=2 consumed). Kill-test corr(pm_new−pm_G34, m−pm_G34) = −0.038 on sealed OOF (DECISION_RYAN_t4707u_KILL_EPA_TRAIL_FAMILY.md, pin 20c49524). ΔMAE_ref +0.1504 (MAE_S1 10.355 − MAE_G34 10.204; n=1105) EXISTING AND VERIFIED from ALEX_S1_EXECUTE_t4696u_v1.md (pin 59a37dd3) and IMV_GRADE_t4696u_S1_EXECUTE_v1.txt (pin 3fc46c93) — not restated in the kill DECISION text. Direction SUPERSEDED pending a *distinct mechanism*.

| Dimension | S1 (killed) | Q2 proposed | Distinct? |
|---|---|---|---|
| Unit | Decomposed EPA unit-strengths (off/def EPA components) | Single team net rating per game: opponent-adjusted point margin (primary) with EPA/play net as a *secondary* input | Yes — primary signal is score-margin based, not EPA decomposition |
| Adjustment | EPA trail (rolling raw EPA, no explicit schedule solve) | Explicit opponent adjustment: ridge/least-squares solve margin_ij = h + s_i − s_j on as-of games only | Yes — schedule strength is solved, not trailed |
| Temporal | Trailing window | As-of solve with prior carry-over from previous season (regressed to mean; regression fraction fixed on DEV) | Yes |
| Eval role | Tweaked on 2019–22 eval window | Invention on DEV 2013–2016 only; EVAL 2018–2022 opened once | Yes |
| Kill test | Failed (−0.038) | Same t4707u kill test is a **mandatory gate** (must be >0) | Inherited gate, not a rename |
**Rename guard:** any variant whose primary input is decomposed EPA unit-strength or rolling EPA trail is S1-family and is OUT OF SCOPE. If DEV shows only the EPA secondary carries signal, STOP and report — do not promote it.

## 3. Retained assets
| Asset | Pin | Status | Use |
|---|---|---|---|
| walkforward games.csv REG 2013–2023 (n=2992; scores, kickoff, spread) | 4fe1cdd7 | EXISTING AND VERIFIED (48a76836) | margins, schedule graph for solve, outcomes |
| PBP 2012–2022 parquets | 6ee24b44 (S1 restage) | EXISTING AND VERIFIED for S1; b41f4b43 EPA mapping UNVERIFIED | secondary EPA/play net |
| As-of rules (kickoff < target) | cf514078 | EXISTING AND VERIFIED | leakage guard |
| Contract field names | b41f4b43 | interface only (no logic reuse claimed) | output schema |
| Lane S 14-signal runner + stats code | #673 938fd55b | EXISTING (mirrored per 324f29b2) | screening stats harness |
| Hist off/def index, 5g EPA beyond sealed 70 | — | MISSING | not needed for Q2 primary |
| Rolling feature scripts for opp-adjust | — | MISSING (none located) | must build in Phase B |
| 2023 PBP | — | MISSING | 2023 outside Q2 windows anyway |

## 4. Splits / labels
- DEV (invention, any tuning of the ~2 hyperparameters: ridge λ, prior-season regression fraction): **2013–2016**.
- 2017 **excluded** (contains sealed 70 / Lane S consumed).
- EVAL **2018–2022, opened once**, after hyperparameters frozen and hashed. Label: **research-consumed locked development evaluation ≠ pristine holdout** (S1 already used 2019–22).
- 2023: excluded (PBP missing; keep as reserve, also research-consumed). 2024–25: sealed, not touched.
- Weeks 2–17 (week 1 as-of = prior only; ASSUMPTION).

## 5. Evaluation
**Signal screen (not forecast quality):** directional Spearman ρ(home_s − away_s, home margin); USEFUL screen requires ρ ≥ +0.15 home-favorable with cluster-robust CI lower > 0. Wrong-way never counts.
**Prediction-quality benchmarks (primary for Phase B go):** map rating diff to predicted margin via linear fit on DEV only, then on EVAL compare:
1. MAE / RMSE of margin vs constant home-edge baseline (DEV mean margin).
2. MAE vs frozen `wl_diff`-based linear predictor (fit DEV, same procedure).
3. Brier / log-loss on SU win via logistic on DEV, vs same two baselines.
4. Paired game-level differences with team-season block bootstrap CI (B=10000, seed 4918).
5. t4707u kill test: corr(pred_new − pred_WL, margin − pred_WL) > 0.
6. Leave-one-season-out sign stability across 2018–2022.
Market spread in games.csv used only as **descriptive reference** (how far from market); **not** a betting/CLV test and **not** a publish gate.

## 6. Power / dependence (ASSUMPTION)
EVAL ≈ 5 seasons × ~240 W2–17 games ≈ 1,200. Fisher-z MDE at α=0.05 two-sided 80%: n≈347 for ρ=0.15 unclustered. Deff = 1+(m−1)·ICC, m≈16 games per team-season; ICC 0.02–0.04 is **ASSUMPTION needing support** → estimate empirical ICC on DEV residuals before EVAL and record it. Detectability ≠ practical value: practical bar is the MAE/Brier improvement vs `wl_diff`, not ρ.

## 7. Stop / go
- Phase A → Phase B only on OWNER ACCEPT of this paper.
- Phase B go-to-"keep" criteria (draft): EVAL ρ ≥ +0.15 directional AND paired MAE improvement vs wl_diff with CI excluding 0 AND kill-test corr > 0 AND no post-EVAL tuning. Any failure → STOP family; report; no re-slice.
- DEV-stage early stop: if DEV ρ < +0.10 or DEV MAE not below wl_diff, STOP before opening EVAL.

## 8. Cost
Phase A ~1–2 d (this paper + OWNER review). Phase B ~8–12 d ASSUMPTION (solve + as-of pipeline ~3 d shared with Q1, eval harness ~2 d, review). Needs separate CLEAR.

## 9. Forbidden
No EXEC/fit under this paper · no S1 revival/rename · no 2024–25 · no forecast regen · control 02197f58/2b9f302e frozen · pub/bet/CERT HOLD · NFL NO-GO CERT=0.
