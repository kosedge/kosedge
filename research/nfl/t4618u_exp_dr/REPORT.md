# Experiment D-R — honest schedule-rest on frozen G34 (t4618u)

**EXP D-R ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**

**RESEARCH VERDICT (STOP BOX, binding pooled ≤2022 OOF): `FAIL`**

Path M=FAIL · vs G34=FAIL · D4 artifacts=PASS · 2023 cannot-alone-PASS · floor=0.05 · FEAS §8 withdrawn

Filed `2026-10-28T14:53:31Z`. Paper/file evidence only. No Odds / merge / deploy / CERT claim.

## Authority

| item | sha8 |
|---|---|
| Ryan CLEAR t4618u | `05632ef0` |
| CoS execute order | `fe01612d` |
| PASS_PROTOCOL | `dd686e13` |
| FREEZE D6=(B) | `81998210` |
| ACK D6/D7 | `82c71d64` |
| Alex STOP ERRATUM | `6bd07cc8` |
| FEAS (frozen; §8 withdrawn) | `9906430e` |
| H2 FROZEN | `db2cf4b2` |
| G34 comparator | `c3248302` |

**Institutional memory:** `no prior grades` for this D-R execute product. Forward-only from ACK `82c71d64` · FEAS `9906430e` · H2 `db2cf4b2` · G34 `c3248302`.

## Frozen design

- `X_rest` = exactly 4 columns: `drest_clip`, `short_h`, `short_a`, `rest_missing`
- `pm_DR = pm_G34 + X_rest · β_rest` (intercept-free OLS on seasons `< S` only)
- HC1 diagnostic; point β used. G34 β/HFA/ratings **not** refit.
- Rest from `nflverse_gameday` date-diff; `>21d` → NaN; clip ±7; short ≤5.
- No DOW heuristic. No emit placeholder 7.0. No 2012 PBP. No `simulate_nfl_game`.
- F1 n_train=0 on `c3248302` (2013 not on comparator) → `β_rest := 0` (no rest adjustment).
- Binding F1–F9 ≤2022 OOF. 2023 supportive. 2024+ forbidden.

## STOP BOX (Alex 6bd07cc8 §5 / ACK 82c71d64 D7)

RESEARCH PASS iff ALL of:

1. Path M: `m ~ a + b·mm + c·pm_DR` (OLS HC1); c>0 and 95% CI excludes 0.
2. vs G34: paired boot B=10000 seed 4141 percentile CI on Δ_DR excludes 0 AND point Δ_DR ≥ 0.05.
3. D4 artifacts (β_rest HC1 incl `beta_missing_ind`; short-rest subset; missingness rates).

`Δ_DR = mae_G34 − mae_DR` (market terms cancel; not market-relative).

### Binding (pooled ≤2022 OOF)

- n = 2440
- MAE(DR) = 10.338466598619265
- MAE(G34) = 10.316425101229509
- MAE(epa, report-only) = 10.694311475409835
- MAE(market) = 9.976229508196722
- point Δ_DR = -0.022041497389756637
- Path M c = 0.020260899415023483  HC1 se = 0.08602716334405032  CI = [-0.14835234073931514, 0.1888741395693621]  pass=False
- vs G34 Δ CI = [-0.049514747237931894, 0.005288081052182504]  point_ge_0.05=False  pass=False

### 2023 supportive (cannot alone PASS)

- n = 285
- MAE(DR) = 10.420226950441576
- point Δ_DR = 0.05549438640052984
- Path M pass=False  vs G34 pass=False

### D4 short-rest subset (supportive)

- n = 150
- point Δ_DR = -0.020763566112365406

## Artifact sha8

| artifact | sha8 |
|---|---|
| `betas_rest_by_fold.csv` | `28b19abf` |
| `counts.json` | `1b9dc93c` |
| `fold_table.csv` | `d72008da` |
| `metrics_2023.json` | `7d93bb82` |
| `metrics_binding.json` | `cc8bb2b1` |
| `missingness.json` | `c6426657` |
| `predictions_dr.csv` | `0fc921dd` |
| `rest_emit.csv` | `32090818` |
| `short_rest_subset.json` | `d9b1984e` |
| `stop_rule.json` | `45d28040` |

## Non-claims

- CERT=0. NFL NO-GO. Coming Soon ON. F2 frozen.
- Research PASS ≠ market bar ≠ CERT. No Odds API. No merge of #646/#647/#648.
- Stop / floor / columns / comparator were not changed post-run.
- FEAS §8 DRAFT not applied. Exp A 0.10 floor not applied.
