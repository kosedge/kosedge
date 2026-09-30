# CFB Chapter 1 Phase 0 audit — margin→WP / KEI by bucket (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH1_WP_BUCKET_BRIEF.md`  
**Program:** `docs/CFB_ENTERPRISE_PROGRAM.md` (Chapter 0 PR #344 may still be open; tape numbers locked below)  
**This PR:** zero curve edits. No `apply_cfb_kei` / `win_prob_from_expected_scores` / power / shock / priors diffs.

Chapter 0 tape (locked):

| Signal                       |                                              Value |
| ---------------------------- | -------------------------------------------------: |
| Mid vs cupcake residual sign |                  **opposite** (`same_sign: false`) |
| W0 mid mean (KEI − close)    |                                         **−12.89** |
| W0 cupcake mean              |                                          **+9.85** |
| HAW@STAN residual            |                             **+15.4** (wrong side) |
| Canaries                     | BALL **−42.2** · TCU **≈ −20.39** · HAW **+10.90** |

---

## 1. Function spine (file:line)

Live published path for a board game:

| Step | What                                                                                    | Where                                                                    |
| ---: | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
|    1 | Compose team O/D indices (eff + roster + QB + units + coaching)                         | `team_projection.py:85–161` `compose_team_projection`                    |
|    2 | Power SoT rank = `0.5*(offense_index+defense_index)`                                    | `power_sot.py:145+` `build_power_sot`                                    |
|    3 | Expected points = league_ppg × (off/def)^response × unit boosts × pace + HFA + coaching | `team_projection.py:309–371` `expected_team_points`                      |
|    4 | ST nudge; `margin = home_exp − away_exp`; `spread_home = away − home`                   | `team_projection.py:558–566` `project_game`                              |
|    5 | `home_wp = Φ(margin / margin_sd)` + cupcake SD saturation                               | `team_projection.py:567–569` → `374–396` `win_prob_from_expected_scores` |
|    6 | API attaches KEI: copy model spread → bias guard → KEI WP from spread                   | `routes/cfb.py:201–205` → `cfb_kei.py:250–334` `apply_cfb_kei`           |
|    7 | KEI WP mapper (no cupcake sat)                                                          | `cfb_kei.py:80–84` `_wp_from_spread`                                     |

**Season-sim / E[wins] path (related, not identical):**

| Step | What                                                                        | Where                                                                           |
| ---: | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
|    A | Same `expected_team_points`, then **margin calibration** (scale+tanh)       | `power_sot.py:188–234` `frozen_expected_scores` → `margin_calibration.py:71–89` |
|    B | Bernoulli WP via `frozen_home_wp` (cupcake sat; uses `SCORE_NOISE_SD * √2`) | `power_sot.py:237–253`                                                          |

### Discovery finding — two mappers

`project_game` does **not** call `apply_calibrated_scores`. Season projections do. Margin cal id `cfb-margin-scale-v0.13-20260814` has `USED_IN_SPREAD = False` (`margin_calibration.py:27`). Published KEI is therefore **raw project-game spread + early bias guard**, not the sim-calibrated margin.

Doctrine hole (Chapter 0 exhibit): TCU Model −19.19 ≈ KEI −20.39 — bias guard is a ~1.2 pt early slice (`HOME_FAV_CORRECTION = -1.20`), not situation information.

---

## 2. Constants (quoted)

From `priors.py` (live engine):

| Constant                              |                               Value | Lines   |
| ------------------------------------- | ----------------------------------: | ------- |
| `ENGINE_VERSION`                      | `cfb-season-engine-v0.15-power-sot` | 42      |
| `SCORE_NOISE_SD`                      |                            **10.5** | 56      |
| `WIN_PROB_MARGIN_SD`                  |                            **15.2** | 58      |
| `WP_CUPCAKE_TARGET`                   |                            **0.90** | 62      |
| `WP_CUPCAKE_Z`                        |                        **1.28155…** | 63      |
| `WP_POWER_GAP_T`                      |                                0.28 | 65      |
| `HFA_BASELINE_POINTS`                 |                                 1.7 | 53      |
| `MATCHUP_RESPONSE`                    |                                1.40 | 107     |
| Early `WIN_PROB_MARGIN_SD` mult W1–W4 |           1.18 / 1.12 / 1.08 / 1.04 | 239–243 |

Cupcake saturation (application only — does not retune SD):

```text
# team_projection.py:386–396
margin = home - away
raw_sd = max(8.0, margin_sd)
if |margin| >= WP_CUPCAKE_Z * 8.0:
    eff_sd = min(raw_sd, |margin| / WP_CUPCAKE_Z)
home_wp = Φ(margin / eff_sd) clamped [0.02, 0.98]
```

Margin calibration knobs (sim path only today):

| Constant           | Value | File                       |
| ------------------ | ----: | -------------------------- |
| `MARGIN_FBS_SCALE` |  0.80 | `margin_calibration.py:30` |
| `MARGIN_TANH_TAU`  |  26.0 | 31                         |
| `MARGIN_FCS_SCALE` |  0.94 | 33                         |

KEI bias guard (weeks 0–2 only):

| Constant              |                                       Value | File            |
| --------------------- | ------------------------------------------: | --------------- |
| `HOME_FAV_CORRECTION` |                                       −1.20 | `cfb_kei.py:40` |
| `HOME_DOG_CORRECTION` |                                       +1.00 | 41              |
| `CORRECTION_CAP`      |                                        1.50 | 42              |
| Short-fav shrink      | 12% toward pick, cap 1.25, \|line\| 1.0–7.5 | 43–46           |

---

## 3. Historical corpus

| Layer                     | Path                                                                      |                          Years | Notes                                                 |
| ------------------------- | ------------------------------------------------------------------------- | -----------------------------: | ----------------------------------------------------- |
| Games + closes SoT        | `/Volumes/KosEdgeData/clean/cfb/historical/{games,closing_lines}.parquet` |                  **2020–2025** | Repo fallback gitignored: `data/cfb/warehouse/clean/` |
| Odds lake (primary close) | `/Volumes/KosEdgeData/clean/odds/cfb/`                                    |                      2020–2026 | Last snap strictly before kickoff                     |
| Ingest                    | `scripts/cfb/ingest_historical_warehouse.py` → `cfb_warehouse/ingest.py`  | `DEFAULT_SEASONS = 2020..2025` |                                                       |
| Inventory (committed)     | `data/ops/cfb-historical-warehouse-v1-20260812-inventory.json`            |                                |                                                       |
| PBP                       | `…/pbp/pbp_{year}_core.parquet`                                           |                  **2014–2025** | Includes **2019**; **no closing spreads**             |

### Row counts by season (inventory — with close spread)

|    Season |     Games | With close spread | Open (lake) |
| --------: | --------: | ----------------: | ----------: |
|      2020 |       571 |               512 |         477 |
|      2021 |       891 |               814 |         696 |
|      2022 |       900 |               838 |         717 |
|      2023 |       911 |               907 |         713 |
|      2024 |       965 |               965 |         793 |
|      2025 |       958 |               958 |         788 |
| **Total** | **5,196** |         **4,994** |   **4,184** |

**2019:** PBP only (890 games / 156,888 plays). **No** `games.parquet` / `closing_lines` row for 2019 in warehouse v1. Brief title says 2019–2025; warehouse **supports 2020–2025 closes**. Extending to 2019 requires a new ingest season, not available in this Phase 0 env.

**This cloud VM:** HD not mounted; repo parquet absent. Discovery script exits 2 and cites inventory:

`python3 scripts/cfb/cfb_ch1_wp_bucket_discovery.py --json`  
→ `data/ops/cfb-ch1-wp-bucket-corpus.json` (`ok: false`, inventory citation).

---

## 4. Bucket counts (Chapter 0 edges)

Edges: pick `[0,3)` · short `[3,7)` · mid `[7,14)` · long `[14,21)` · cupcake `[21,∞)`.

### Full corpus

**Not countable in this VM** (parquet missing). Script `scripts/cfb/cfb_ch1_wp_bucket_discovery.py` is the allowlisted measurement tool for an HD/worker run — counts only, no fit. It also splits **P4_vs_P4 / P4_vs_G5 / G5_vs_G5 / FCS** via `conference_for` + `fcs_opponent` (warehouse has FCS flags; no native P4 column).

### Directional sample only (not Phase 1 N)

Hist-cal `after_games_sample.json` (n=50, older engine) bucketed by \|close\| for **sign pattern only**:

| Bucket  |   n | mean (model − close) |
| ------- | --: | -------------------: |
| pick    |   6 |                −3.69 |
| short   |   5 |                −1.97 |
| mid     |  10 |                −1.42 |
| long    |   9 |            **+6.88** |
| cupcake |  20 |           **+21.23** |

Same qualitative story as Chapter 0: cupcake model **short** of book; mid not the same sign as cupcake on this tiny sample. **Do not fit on n=50.**

Warehouse FCS-flagged games (inventory): **701** across 2020–2025.

---

## 5. Current-curve residual on 2024–2025 holdout?

**Cannot score live `v0.15-power-sot` project-game / KEI vs warehouse closes in this PR without writing new replay code and mounting parquet.**

What exists (script-only read — different fairs):

| Artifact                                                                     | Fair                                                             | Holdout-ish                         | MAE vs close |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------- | -----------: |
| Walk-forward W0–4 (`data/ops/cfb-walkforward-week0-4-20260812-summary.json`) | Program EPA prior / week blend — **not** live roster+SP+ compose | 2024 n_close 776 · 2025 n_close 786 |  7.20 / 7.28 |
| Hist-cal comparable holdout 2023–24                                          | `v0.8.1-hist-cal`                                                | n=1572 after                        |         8.27 |

Walk-forward mean error **+2.0** overall (model less home/favorite than close) — opposite of Chapter 0 mid-band “KEI too long” on TCU. That confirms **prior-only warehouse fair ≠ published KEI spine**. Scoring the real curve is Phase 1 prep work on HD, not a sneak fit here.

**Recommendation for Phase 1 design:** warehouse already supports **walk-forward** (`scripts/cfb/run_walkforward_week0_4.py`) and season holdouts. Prefer **train 2020–2024 / hold out 2025** for the bucket margin→points map (closes dense 2023–25). Do **not** claim 2019 until closes are ingested. Do **not** refit on six W0 games.

---

## 6. Phase 1 allowlist (next PR only — not this one)

Named files that _would_ change after gate:

1. `services/model-service/src/services/cfb_season_engine/team_projection.py` — `win_prob_from_expected_scores` and/or how margin maps to `spread_home` **by bucket** (no team branches).
2. `services/model-service/src/services/cfb_season_engine/priors.py` — only if a **named** bucket SD / map constant is introduced (not a silent stretch of `WIN_PROB_MARGIN_SD` alone to fake TCU −8.5).
3. `services/model-service/src/services/cfb_season_engine/margin_calibration.py` — only if Phase 1 **unifies** project-game with the sim margin path (today `USED_IN_SPREAD=False`).
4. `services/model-service/src/services/cfb_season_engine/cfb_kei.py` — `_wp_from_spread` coherence with cupcake sat; **not** team-specific bias.
5. Bundled pack `apps/web/lib/data/cfb-kei-w0-w1-2026.json` — re-emit after curve change.
6. Season sim re-run N=10,000 via existing `power_sot` / futures path (order frozen).
7. New ops scorecard + optional `scripts/cfb/cfb_ch1_*_fit.py` (fit lives in scripts first).

**Explicitly off-limits in Phase 1 unless a later chapter names them:** `compose_team_projection` weights, `MATCHUP_RESPONSE` beauty pass, Utah / title scale, Week 0 power rebuild, `if team == "TCU"|"Hawaii"`.

---

## 7. Risk — what shuffles top-7 if Phase 1 is sloppy

| Sloppy move                                                                         | Why top-7 / canaries break                                                      |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Stretch `MATCHUP_RESPONSE` or O/D compose weights                                   | Changes expected margins → power-adjacent separation and E[wins]                |
| Apply `MARGIN_FBS_SCALE` / tanh onto live project-game without freezing power order | Compresses all gaps; OSU cupcake and mid-band move together                     |
| One global `WIN_PROB_MARGIN_SD` stretch to hit TCU −8.5                             | WP canaries (BALL 90s) and KEI magnitude decouple; Hawaii polarity may not flip |
| Touch `build_power_sot` sort key                                                    | Direct top-7 shuffle                                                            |
| Re-sim with strength evolution / Week 0 refit                                       | USF↔OSU E[wins] clone risk returns                                              |

Safe Phase 1 shape: **bucket map on margin→published points / WP**, power order frozen, scorecard trio + top-7 + USF canaries. If TCU stays ≈ −20 after an honest fit → **blocker**, do not stretch one SD.

---

## Phase 0 answers (checklist)

1. Spine mapped with file:line — **yes**
2. Constants quoted — **yes**
3. Corpus path + season counts — **yes** (2020–2025 closes; 2019 PBP-only)
4. Bucket N — **script ready**; full N **blocked on HD parquet** in this VM; inventory + sample only
5. Existing v0.15 residual on 2024–25 — **cannot** without new replay; stated honestly
6. Phase 1 allowlist — **yes**
7. Top-7 risk — **yes**

**Blocker-or-done:** Phase 0 discovery **DONE** for gate. Operator may require HD bucket dump as a one-line follow-up before Phase 1 fit PR — that is still measurement, not curve edit.

**Canaries:** unchanged (pack untouched).  
**Product numbers:** unchanged.
