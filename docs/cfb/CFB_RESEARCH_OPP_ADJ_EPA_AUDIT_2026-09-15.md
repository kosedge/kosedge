# AUDIT — rematerialized #560 ADVANCE (Ryan, 2026-09-15)

Audit-only. Frozen knobs unchanged. `production_promote=false`. No board reopen. No SP+ / KEI / NFL change.

**Status for Ryan: advance OK (2025 sealed).**

Next product path: validated efficiency → scoring margin/totals conversion research — **not** board reopen on EPA MAE alone.

Evidence: `data/ops/cfb-research-opp-adj-epa-20260915/` · `ryan_audit_560.json` · `validation_report.json` · `frozen_method.json`

---

## 1) How was λ=40 selected?

Exact procedure (`select_params` in `services/model-service/src/services/cfb_warehouse/research_opp_adj_validate.py`):

- **Grid:** 8 cells (`PARAM_GRID`) — λ ∈ {40, 80, 160}, n0 ∈ {3, 4, 6}, decay ∈ {0.65, 0.75, 0.85} (not a full factorial).
- **Objective:** minimize next-game O/D EPA MAE (`mean_mae` = average of offense and defense MAE).
- **Folds:** none. Chronological pregame cutoffs: for each val week W, fit uses same-season `week < W` plus decayed prior-season finals.
- **Selection years:** **2023–2024 validation only.** Seed/train years 2014–2022 build priors. Recorded as `selection.selection_seasons = [2023, 2024]`.

**Did 2025 influence λ / n0 / decay?** No. `select_params` calls `evaluate_seasons(..., val_seasons=(2023, 2024))` only. The artifact flag is `holdout_used_for_selection: false`. Holdout is scored in `run_validation_suite` **after** argmin. Unit test `test_holdout_not_in_selection_contract` locks `2025 not in selection_seasons`.

Seal evidence (procedural, not a withheld 2025 file):

| Proof                       | Path / commit                                                                 |
| --------------------------- | ----------------------------------------------------------------------------- |
| Val-only argmin             | `research_opp_adj_validate.py` `select_params` / `VAL_SEASONS`                |
| Artifact flag               | `validation_report.json` → `selection.holdout_used_for_selection=false`       |
| Contract test               | `tests/test_cfb_research_opp_adj.py` `test_holdout_not_in_selection_contract` |
| Grid predates rematerialize | same `PARAM_GRID` since `04d85609`; λ=40 was cell 2 before any 2025 score     |
| Rematerialize report        | `6580589f` `validation_report.json` still lists selection seasons 2023–2024   |

2025 rows live in the same hist parquet and were in memory. They were **not** an input to argmin. That is the locked software seal. A physical holdout-ID file was not written before first look; the contract + test + artifact flag are the seal.

Why λ moved 160 → 40: pre-fix ridge ignored n0, so λ=160 won val. After n0 entered the ridge, val MAE ranked **λ=40 / n0=4 / decay=0.75** first (0.16689 vs λ=160 / n0=4 at 0.16806). Identification change, not holdout peeking.

---

## 2) Why did both baseline scores change?

Holdout **observation set is the same**.

| Check            |                               Pre-fix `91a43783` |                        Rematerialize `6580589f` |
| ---------------- | -----------------------------------------------: | ----------------------------------------------: |
| n team-games     |                                             1713 |                                            1713 |
| Unique `game_id` |                                                — |                                             930 |
| Weeks 1–12 n     |                                          229…116 | **identical** (`week_head_n_match_prefix=true`) |
| Target           |                     next-game O/D EPA/play (`y`) |                                            same |
| Exclusions       | FCS offense dropped; OT / garbage already in `y` |                                    same parquet |

Obs-key checksum (sorted `season,week,game_id,offense,defense,home`):

`009ce549ab9e0b0b5a94aa0bdc88b0c9d57d11e156c291634dca5e08f2532508`

File: `holdout_2025_obs_keys.tsv`.

Offense unadj/blend MAE is **bit-identical** to pre-fix (`0.19060067436327593` / `0.18387396759975136`). That proves the same `y` and the same STD/blend offense path.

Defense unadj/blend MAE moved (`0.191326` → `0.191517` unadj; `0.183275` → `0.183503` blend). Cause: `_std_to_date` / `_season_raw_means` fall back to **adj-model μ** when a defender has no same-season STD and no prior-season raw mean. Audit count: **0 offense rows** use that fallback; **5 defense rows** do (`ryan_audit_560.json`). Pair MAE is ½(off+def), so the published unadj/blend ticks (0.1910 → 0.1911, 0.1836 → 0.1837) are those five rows seeing a new μ after the estimator fix — not a new sample and not a new target definition.

Apples-to-apples on the ID set: **yes**. Do not read the 0.0001 baseline tick as a sample change.

---

## 3) What does h≈0.244 mean?

- **Units:** EPA/play on the **offense** team-game observation. Not points. Not a spread.
- **Coding:** `home = 1` if the offense is the home team, else `0` (neutral / unknown → 0). See `offense_is_home` / `ELIGIBLE_PLAY_RULES["home"]`.
- **Model:** `y = μ + h·home + off_i + def_j`. Home **offense** gets `+h`. Home **defense** is the other row (`home=0` for the away offense), so h is not a two-sided point-spread HFA.
- **Sign:** larger `h` → higher predicted EPA/play for the home offense, all else equal.

**Stability (frozen knobs, season-final fits — not the 2026 week-1–2 window):**

|              Season |          μ | h (EPA/play) |   n obs |
| ------------------: | ---------: | -----------: | ------: |
|                2014 |     −0.018 |        0.066 |    1706 |
|                2018 |      0.012 |        0.051 |    1768 |
|                2020 |      0.038 |        0.022 |    1130 |
|                2024 |      0.008 |        0.066 |    1892 |
|                2025 |      0.011 |        0.071 |    1912 |
| **2026 W1–2 apply** | **−0.106** |    **0.244** | **168** |

Full-season h sits ~0.05–0.07 (2020 dip 0.022). The 0.244 figure is a **small-sample early-season** intercept on 84 games. It is **not** spread-ready HFA. Do **not** convert `h` to a point spread.

---

## Status

**advance OK (2025 sealed).** Locked knobs stay `λ=40 / n0=4 / decay=0.75`. `production_promote=false`. Coming soon / live SP+ / KEI untouched.

Next step: validated efficiency → scoring margin/totals conversion research — not board reopen on EPA MAE alone.

**STOP.**
