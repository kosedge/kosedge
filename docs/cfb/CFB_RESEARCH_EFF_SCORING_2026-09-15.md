# CFB research — efficiency → scoring (points → margin / total)

**Date:** 2026-09-15  
**Authorized:** Ryan / CoS GO — research-only.  
**Protocol lock:** `docs/cfb/EVAL_PROTOCOL.md` at `6aae7b7a` **before** any scoring fit or grid.  
**`production_promote=false`.** Boards stay Coming soon. Live SP+ / KEI unchanged. No board reopen.

Evidence: `data/ops/cfb-research-eff-scoring-20260915/`  
Frozen EPA: `data/ops/cfb-research-opp-adj-epa-20260915/` (`λ=40`, `n0=4`, `decay=0.75`)

---

## Recommendation (confirmation only)

**Call: revise.**

2024 weeks ≥ 10, FBS vs FBS, n = **280** games (seal). 2025 was **not** used for the call.

| Target | Model MAE | Best Vegas-free baseline | Rel | Abs |
| --- | ---: | ---: | ---: | ---: |
| Margin (`home − away`) | **13.05** | 14.26 (prior-season points blend) | **−8.5%** | **−1.21** |
| Total (`home + away`) | 14.15 | **13.68** (train league-mean points) | **+3.4% worse** | **+0.47 worse** |

Locked rule required beating **both** margin and total by ≥1% relative or ≥0.25 pts. Margin clears. Total does not. Bias: margin +2.63; total +3.76 (total bias is also worse than the better baseline by more than 1.5).

`production_promote=false`. Do not reopen boards. Promotion is a separate Ryan decision.

2025 (development evidence only, n=783): same shape — margin 13.01 vs blend 14.78; total 14.15 vs league 13.90. Not a seal.

---

## A) Independent baseline fallbacks (clean #560 EPA benchmark)

**IBF-v1:** when STD and prior-season raw are both missing, use `mean(y)` on FBS-offense team-games in **2014–2022** (seed ∪ train). Value = **0.04069**. Never `fit.mu`. Never 2023–2026 games.

Same 2025 obs keys as #560:

| Check | Value |
| --- | --- |
| n | 1,713 team-games / 930 games |
| Obs-key SHA | `009ce549ab9e0b0b5a94aa0bdc88b0c9d57d11e156c291634dca5e08f2532508` |
| SHA match | **true** |
| IBF rows | 0 offense / **5 defense** (same five as the audit) |

| Predictor | Pair MAE (clean) | Previous (coupled μ) | Δ |
| --- | ---: | ---: | ---: |
| Opponent-adjusted | **0.16728386** | 0.16728386 | **0** (bit-identical) |
| Unadjusted STD | 0.19095704 | 0.19105877 | −0.000102 |
| Prior-season blend | 0.18356437 | 0.18368829 | −0.000124 |

Offense unadj/blend MAE is still bit-identical to #560 (`0.19060067` / `0.18387397`). Defense unadj moved `0.19151687 → 0.19131340` because those five rows now see 0.04069 instead of the adj-model μ.

Relative MAE cut on the **clean** baselines: **12.40%** vs unadj, **8.87%** vs blend (was 12.44% / 8.93%). Direction and materiality do **not** flip. Do **not** quote the old pair-MAE improvement as if the benchmark were unchanged — file this delta.

EPA knobs were **not** retuned.

---

## Scoring model

```
epa_i     = μ_fit + off_i + def_j          # EPA h·home dropped
points_i  = a + b · (epa_i · exp_plays) + h_pts · home_i
margin    = home_points − away_points      # home perspective
total     = home_points + away_points
```

| Locked / selected | Value |
| --- | --- |
| EPA stack | frozen #560 `fit_joint_v2`, `λ=40`, `n0=4`, `decay=0.75` |
| `a` (train OLS) | 25.73 |
| `b` (train OLS) | 0.787 |
| Pace source (2023 val) | `pace_plays` (scrimmage plays / offense game) |
| `ppp` (train) | 5.662 plays / possession (`pace_plays / n_drives`) |
| League pace (train, selected source) | 69.24 plays |
| `exp_plays` | `0.5 * (pregame_home_pace + pregame_away_pace)` |

Inputs are pregame only. No synthetic score/pace fills. No CFBD.

### Shrunk HFA used for scoring

```
h_pts = (N / (N + k)) · h_window + (k / (N + k)) · h_prior
      = (5727 / 5737) · 5.869 + (10 / 5737) · 6.727
      = 5.870 points
```

- **Units:** points added to the **home** team's predicted points. Neutral / unknown → 0.  
- **`h_window`:** train OLS home coefficient after the EPA×plays term (N = 5,727 non-neutral train games).  
- **`h_prior`:** train mean(`home_points − away_points`) = 6.727. This is **not** “true HFA if teams cancel” — it includes favorite-host schedule.  
- **`k`:** 10, selected on 2023 val only. With N = 5,727 the shrink is tiny (grid was flat).  

**Forbidden and not used:** `spread ≈ 0.244 × n_plays` (≈ 17 points at 70 plays). Thin-window EPA `h≈0.244` is an early-2026 EPA/play intercept, not a spread. Season-final EPA `h` (~0.05–0.07) was also not converted to points.

---

## Splits (protocol)

| Set | Window | n (FBS vs FBS games) | Role |
| --- | --- | ---: | --- |
| Train | 2016–2022 | 4,867 | Fit `a`, `b`, HFA prior / window, `ppp` |
| Validation | 2023 | 778 | Select pace source + `k` only |
| **Confirmation** | **2024 weeks ≥ 10** | **280** | **Seal / recommendation** |
| Development evidence | 2025 | 783 | EPA-known year; labeled only |

2024 late was unseen for **scoring knobs**. EPA λ was selected on full 2023–2024 — confirmation seals the conversion, not a fully independent stack.

---

## Validation numbers

### Confirmation (seal) — 2024 weeks ≥ 10

| | Margin MAE | Margin bias | Total MAE | Total bias | Team-pts MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Model** | **13.05** | +2.63 | 14.15 | +3.76 | 9.71 |
| STD points | 14.28 | −3.91 | 15.30 | +2.42 | — |
| Prior blend (`n0=4`) | 14.26 | −3.85 | 14.76 | +2.05 | — |
| League mean / 0-margin | 15.93 | −4.19 | **13.68** | +2.52 | — |

Confirmation is entirely the late band (weeks ≥ 10) by construction.

### Validation 2023 (selection only)

| | Margin MAE | Total MAE | Team-pts MAE |
| --- | ---: | ---: | ---: |
| Model | 13.62 | 13.58 | 9.70 |
| Early W1–4 | 14.23 | 14.28 | 10.40 |
| Mid W5–9 | 13.34 | 12.73 | 9.24 |
| Late W≥10 | 13.31 | 13.76 | 9.48 |
| Best baseline margin | 14.73 (blend) | | |
| Best baseline total | 14.18 (league) | | |

Val objective `0.5*(margin+total) MAE` = 13.60. `k` cells differ by <0.002 — large-N HFA.

### Train 2016–2022 (fit only)

Model margin MAE 14.19 / total 14.16 / team-pts 10.19. Early worse than mid/late on margin (15.14 vs 13.67 / 13.90).

### 2025 development evidence (not the call)

Model margin 13.01 vs blend 14.78; total 14.15 vs league 13.90. Early / mid / late margin MAE: 13.67 / 12.32 / 13.10.

---

## Why revise (not advance / not reject)

- Conversion is **not empty**: confirmation margin beats both point baselines by a material amount.  
- Totals are **not ready**: a constant train-mean total beats the EPA×pace total on the seal set. The model over-projects combined scoring (bias +3.76).  
- HFA at 5.87 pts is a residual home+quality term, not a cleaned 2–3 pt HFA. Do not ship it as “the number.”  
- n = 280 ≥ 150, so the seal is usable. Reject is not the call.

Next research (separate): a totals-specific intercept or ST/finishing term; do **not** retune this grid on confirmation. Do **not** reopen boards on margin MAE alone.

---

## Reproducible commands

```bash
# Protocol was locked first:
#   git show 6aae7b7a:docs/cfb/EVAL_PROTOCOL.md

cd services/model-service
python3 -m pytest tests/test_cfb_research_opp_adj.py \
  tests/test_cfb_research_scoring.py -q

PYTHONPATH=services/model-service python3 scripts/cfb/run_research_opp_adj_clean_baselines.py \
  --as-of 20260915 --write-ops

PYTHONPATH=services/model-service python3 scripts/cfb/run_research_scoring.py \
  --as-of 20260915 --write-ops
```

No CFBD. No write to Aug 13 `raw/cfb/pbp/`. Hist restore: `data/cfb/research/pbp_hist/as_of_20260915/` (gitignored).

Checksums: `data/ops/cfb-research-eff-scoring-20260915/artifact_checksums.json`.

---

## Out of scope (unchanged)

Coming soon / live SP+ / KEI / NFL / Edge Board chrome. No UI. No stake tags.

**STOP.**
