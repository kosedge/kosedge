# Q2 EVAL SPEC CLARIFY — t4923u v1 (FROZEN PAPER)
Filed by Alex Rourke RO · 2026-10-31 (America/New_York) · PAPER ONLY — no EXEC, no data runs, no scoring.
Answers ORDER COS_ORDER_ALEX_t4923u_Q2_EVAL_SPEC_CLARIFY.md sha8 98317c95. Label DEV_RESEARCH · NFL NO-GO · CERT=0.

## Pins (box-verified sha256 prefixes)
- ORDER 98317c95 · OWNER direction t4923u a9719970 · Q2 Phase A design 2702b295 · Amended plan 0e142005 (ACCEPTED)
- Index audit gate 83646d78 · map tip 3df95f51
- S1 kill DECISION_RYAN_t4707u_KILL_EPA_TRAIL_FAMILY.md: box sha256 50f57195… ; design 2702b295 cites pin 20c49524. **Pins differ** — both recorded; not reconciled here (CoS to confirm which revision is canonical).
- Control tip 02197f58 · SCORE_RESULTS 2b9f302e · IF 6ca03716 · contract b41f4b43
- #4 R1 protocol a1b4f03e ACTIVE — out of scope. Stage B RO separate — out of scope.

Field naming: `wl_diff` = home team as-of win% − away team as-of win% (as used in design 2702b295 §6/§9 and plan 0e142005). Exact column name in games.csv to be verified at Phase B FROZEN_CONFIG; if it differs, the mapping, not the definition, is recorded.

## 1. W-L comparator as an actual forecast
Two frozen W-L-family baselines:
- **WL_MARGIN** (points, home − away): `pm_WL = a + b·wl_diff`, (a,b) by OLS on DEV games only (2013–2016, REG W2–17), then frozen.
- **WL_WP** (probability ∈[0,1]): `P_WL(home win) = σ(c_WL + d_WL·wl_diff)`, logistic MLE on DEV only (ties excluded from fit), then frozen.
Training rules: DEV 2013–2016 only; every input as-of with source games kickoff < target kickoff; weeks 2–17; zero EVAL/2017/2023/2024–25 rows in any fit; the only comparator parameters are (a,b) and (c_WL,d_WL) — no regularization, no other knobs. Q2 `pm_new` uses the identical procedure (OLS rating_diff → margin on DEV).
Constant baselines: CONST_MARGIN = DEV mean home margin; CONST_WP = DEV home-win rate (ties excluded).

## 2. Kill test (inherits t4707u form; WL replaces G34)
- m = home_score − away_score (points). pm_WL = WL_MARGIN (§1). pm_new = Q2 rating_diff mapped by its own DEV-only OLS.
- **new−WL** := pm_new − pm_WL (points). **margin−WL** := m − pm_WL (points).
- Statistic: Pearson corr(new−WL, margin−WL) on the evaluation set under test. **Threshold: > 0** (strict, point estimate, as t4707u). Positive = new forecast's departure from WL moves with truth's departure from WL (incremental information).
- For Q2 Phase B the WL comparator **replaces pm_G34**; G34 is not used unless a separate predeclared comparison is added via CoS→OWNER.
- Points space only; not win-prob space.

## 3. Raw wl_diff ≠ point-margin forecast
`wl_diff` is a unitless win%-difference ∈[−1,1]. It must never be scored as MAE/RMSE against margin, nor used as pm_WL in the kill test, without the §1 map. Any code path computing MAE(wl_diff, m) or Brier on raw wl_diff = **SPEC FAIL / Phase B BLOCKED**.

## 4. ρ = directional screen only
Spearman ρ(home_s − away_s, m), USEFUL screen ρ ≥ +0.15 with cluster-robust CI lower > 0 (design 2702b295 l.40), is a screen, not forecast-quality evidence. Per plan 0e142005: "Correlation = signal screen only; not forecast-quality PASS or betting value." Forecast quality requires paired ΔMAE, ΔRMSE (points) and ΔBrier (prob) of Q2 vs WL_MARGIN/WL_WP and vs constant, each with §6 CIs.

## 5. Brier: frozen DEV-only probability mapping
- Q2: `P_new = σ(c + d·pm_new)` (default logistic on mapped margin; rating_diff input equivalent up to affine and not to be swapped post hoc), MLE on DEV only. WL_WP same procedure (§1).
- Record in Phase B FROZEN_CONFIG before EVAL open: c, d (and c_WL, d_WL, a, b), n_fit, n_ties_excluded, sha256 of serialized fit object, freeze timestamp (America/New_York) + config sha.
- Outcome y = 1 if m>0, 0 if m<0; **ties excluded from Brier n; report n_ties**.
- Freeze point: after DEV fit, before any EVAL row is read. No refit/recalibration on EVAL. No 2024–25.

## 6. Selection + dependence
- Selection: DEV = invention + all comparator/mapping fits + DEV early stop (design l.56). EVAL 2018–2022 opened **once**. 2017 excluded; 2023 reserve; 2024–25 sealed.
- Dependence: paired game-level Δ with team-season block bootstrap, B=10000, seed 4918 (design l.45); cluster-robust (team-season) SE acceptable as secondary. Week clustering: report week-clustered SE as sensitivity. Empirical ICC on DEV residuals estimated and recorded before EVAL (design ASSUMPTION 0.02–0.04 must be replaced by measured value).
- Multiple looks: Q2 FAMILY look counter k=0 at ACCEPT of this clarify; DEV looks logged but do not consume EVAL; Phase B go/no-go = exactly one EVAL look (k→1). Any failure → STOP family; no re-slice, no re-threshold, no reseed.
- Keep criteria (design l.55, unchanged): ρ ≥ +0.15 directional AND paired ΔMAE vs WL_MARGIN CI excluding 0 (improvement) AND kill corr > 0 AND no post-EVAL tuning.

## 7. Research-consumed labels
| Window | Label |
|---|---|
| DEV 2013–2016 | invention / fit (research-consumed) |
| 2017 | EXCLUDED — research-consumed by sealed 70 + Lane S |
| EVAL 2018–2022 | research-consumed locked development evaluation ≠ pristine holdout (S1 used 2019–22) |
| 2023 | reserve; research-consumed if touched |
| 2024–25 | SEALED — not touched |
Q2 Phase A = research priority, NOT a production model. Phase B HELD — Needs CLEAR.

## Freeze table
| Item | Frozen value |
|---|---|
| DEV / EVAL | 2013–16 REG W2–17 / 2018–22 REG W2–17, one look |
| EVAL n (est.) | ≈1,200 (design ASSUMPTION) |
| WL_MARGIN | pm_WL = a + b·wl_diff, OLS DEV |
| WL_WP | σ(c_WL + d_WL·wl_diff), logistic DEV |
| Q2 maps | OLS rating_diff→pm_new; σ(c + d·pm_new), DEV |
| Kill | Pearson corr(pm_new−pm_WL, m−pm_WL) > 0, points |
| Screen | Spearman ρ ≥ +0.15, cluster CI lower > 0 |
| Bootstrap | team-season block, B=10000, seed 4918 |
| Ties | excluded from Brier/logistic; n_ties reported |
| Look counter | k=0 at ACCEPT; Phase B = 1 look |

## Constraints
- Index audit gate 83646d78: no scored experiment may broadly reuse hist index 1ee90fac until audit PASS; Stage B pilot in-scope only.
- Any change to math/eval rules escalates via CoS → OWNER (not "mapping fixes").

## Non-claims
≠CERT ≠edge ≠merge ≠betting ≠publication · no Odds · no 2024–25 · no runs/scoring performed for this paper · NFL NO-GO · CERT=0.

Register preflight: PAPER t4923u Q2_EVAL_SPEC_CLARIFY v1 · ORDER 98317c95 · design 2702b295 · plan 0e142005 · no EXEC · k=0.
