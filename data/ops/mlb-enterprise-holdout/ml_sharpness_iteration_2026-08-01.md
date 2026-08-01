# MLB moneyline sharpness iteration — 2026-08-01

**Branch:** `mlb-ml-sharpness`  
**Policy:** Evidence-first; no Odds densify; unused holdout still frozen; props remain `research_only`.

## Inventory (wired vs unused)

| Lever | Status | Notes |
|-------|--------|-------|
| SP quality / K-BB-GB shape | **Wired** | `starter_identity_features` → PA/pitch sim |
| Starter firmness + missing-SP shrink | **Wired** | `sharpen_game_inputs` on daily / nowcast / resim |
| Lineup shock + SP-change shock | **Wired** (nowcast) | Bounded offense muls |
| Platoon vs L/R | **Partial → fixed** | Context built one hand; nowcast did not refresh on SP flip |
| Rest days | **Wired** (JSON context) | Not a dedicated column; defaults to 1.0 if missing |
| Bullpen fatigue / availability | **Wired** in sim | Sharpen previously **double-counted** via `bullpen_quality_from_state` |
| Park / weather reliability | **Wired** | Dome damp in sim |
| Home-field advantage | **Missing → fixed** | Neutral slate was ~49.8% home win |
| Market blend / shrink-to-close | Unused for MLB ML | Correctly not shipped |
| Calibration (bin map) | Wired in walkforward | Barely moves Brier (~1e-5) |
| Data-lake `offense_split_vs_l/r` | Stored daily | Not previously selected on nowcast SP change |

## What we implemented

1. **Totals-neutral home-field advantage** (`HOME_FIELD_OFFENSE_MUL=1.035`) in PA-sim and pitch-sim run construction.
2. **Remove bullpen double-count** in `sharpen_game_inputs` — fatigue/availability stay on the simulator path only; rest-day bullpen stress kept.
3. **Platoon refresh on SP change** — context now stores `offense_split_vs_l` / `vs_r`; nowcast re-selects split when starter handedness/identity changes.

## Metrics

### Synthetic HFA check (no DB; fixed 54% home-win labels)

```bash
PYTHONPATH=services/model-service python3 scripts/mlb/eval_ml_sharpness_synthetic.py
```

| | Avg P(home) | Avg total | Brier |
|--|------------:|----------:|------:|
| Before (no HFA) | 0.499 | 9.069 | **0.2536** |
| After (HFA) | 0.542 | 9.047 | **0.2494** |
| Δ | +0.043 | −0.022 | **−0.0042** |

This is a wiring sanity check, **not** a walkforward / unused-holdout grade.

### Full walkforward / CLV

**Completed 2026-08-01** — see [`ml_sharpness_resim_grade_2026-08-01.md`](./ml_sharpness_resim_grade_2026-08-01.md).

| | Before (subscription) | After (full May–Jul resim) |
|--|----------------------:|---------------------------:|
| Base Brier | 0.251616 | **0.250502** |
| ML CLV | +0.0232 | **+0.00702** |
| ECE | — | 0.0277 |

Brier moved slightly toward the 0.24 gate; ML / RL / total CLV regressed. Unused holdout still frozen.

### Unit / integration

```bash
cd services/model-service && python3 -m pytest \
  tests/test_mlb_simulator.py \
  tests/test_mlb_pa_feature_sharpen.py \
  tests/test_mlb_lineup_shock.py -q
```

**27 passed** (includes new HFA + platoon + no-double-count tests).

## Next if Brier still fails ≤0.24

1. Force-resim May–Jul densify window with these changes; re-grade walkforward (exclude unused holdout).
2. Ablate SP identity coverage (heuristic-fallback share) and expand live Statcast / pitcher arsenal features.
3. Grade unused holdout (2026-07-18–08-10) only after train exclusion stays clean — do not stake-market ML until pass.
4. Avoid market-blend shrink as a first lever; prefer matchup-PA richness.

## Risks

- **RL / totals:** HFA is product-neutral by design; still re-check `avg_spread_clv` / `avg_total_clv` after resim.
- **Overfit:** HFA uses a long-run baseball prior (~53.5–54%), not a holdout-tuned coefficient.
- **Platoon refresh** only helps when context JSON has `offense_split_vs_l/r` (requires context snapshot after this deploy).
