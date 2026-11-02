# Experiment A — ridge-joint 54-cell fold validation (t4602u)

**EXP A ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**

**VERDICT (binding pooled ≤2022 OOF): `PASS`**

Stop (a)=FAIL · Stop (b)=PASS · 2023 cannot-alone-PASS · reversal_caution=False

Filed `2026-10-28T13:09:29Z`. Paper/file evidence only. No Odds / merge / deploy / CERT claim.

## Authority

| item | sha8 |
|---|---|
| Ryan CLEAR t4602u | `1992ea62` |
| CoS execute order | `3e500d55` |
| IMV PREFLIGHT LOOK (full §4) | `a5083123` |
| H2 FROZEN manifest | `db2cf4b2` |
| Exp E IMV_PASS | `3d79c41b` |
| Exp E counts | `b0365365` |
| H1 addendum | `5d426ae9` |
| H1 SHA256SUMS | `97774e08` |
| tip (E H1) | `0940a289` |
| Alex SPEC §4 | `ddffb72e` |
| ESTIMATOR addendum | `84a28a05` |
| Cursor ACK | `6fcc0af6` |

## Frozen design (unchanged)

- `ESTIMATOR_ID` = `nfl-research-opp-adj-epa-v0-ridge-joint`
- `n0_base` = 4.0
- grid 54 (ρ / λ / ρ_s / HFA off|fold_fit)
- L1: HFA off, then ρ=0.95, λ=1, ρ_s=0.67; ε=1e-9
- F1–F9 S=2014…2022 primary; 2023 supportive; 2024+ forbidden
- ONE fold-fit β; `margin_A = β · rating_diff_home + HFA`; `simulate_nfl_game=false`

## Selected cell (inner-CV MAE, L1 tie-break)

- `cfg_id` = `G34`
- ρ=0.95 λ=2.0 ρ_s=0.67 HFA=fold_fit n0=8.0
- pooled ≤2022 inner-CV MAE = `10.316425094613239`

## Stop rule — Alex ddffb72e §4 (full emit)

Exp A FAILS unless:

(a) encompassing `m ~ a + b·mm + c·pm_A` (OLS, HC1) gives c 95% CI excluding 0 with c>0;

OR

(b) paired game bootstrap of Δ, B=10000, seed 4141, percentile 95% CI excludes 0 AND point Δ ≥ 0.10 pts.

`Δ = mean(gap_baseline) − mean(gap_A)`; `gap_X = |m − pm_X| − |m − mm|`.

Binding = pooled ≤2022 OOF. 2023 supportive / cannot-alone-PASS. VOID if changed post-run.

### Binding (pooled ≤2022 OOF)

- n = 2440
- MAE(A) = 10.316425094613237
- MAE(epa baseline) = 10.694311475409835
- MAE(market) = 9.976229508196722
- point Δ = 0.3778863807965986
- (a) c = 0.0511507602072242  HC1 se = 0.08906523159074416  CI = [-0.12341709371063433, 0.22571861412508273]  pass=False
- (b) Δ CI = [0.22331531822928416, 0.5293600144140136]  point_ge_0.10=True  pass=True

### 2023 supportive (cannot alone PASS)

- n = 285
- MAE(A) = 10.475721349820141
- point Δ = 0.20782250982898176
- (a) pass=False  (b) pass=False
- reversal_caution = False

## Artifact sha8

| artifact | sha8 |
|---|---|
| `betas_by_fold.csv` | `8fbeaa7c` |
| `counts.json` | `b60deb6a` |
| `fold_table.csv` | `380538a5` |
| `grid_mae.csv` | `170cec7a` |
| `metrics_2023.json` | `76b94beb` |
| `metrics_binding.json` | `1cac09ff` |
| `predictions.csv` | `c3248302` |
| `selected_cell.json` | `3172b236` |
| `stop_rule.json` | `e14e235d` |

## Non-claims

- CERT=0. NFL NO-GO. Coming Soon ON. F2 frozen.
- No Odds API. No merge of #646/#647/#648. No LOCKED_SCORING change.
- Rating-model h was not added into margin_A.
- Stop rule was not changed post-run.
