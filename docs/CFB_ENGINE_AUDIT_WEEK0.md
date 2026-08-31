# CFB Engine Audit — Week 0 close pass

**Phase 0 status:** READ ONLY complete.  
**Branch:** `cursor/cfb-week0-close-wp-shock-gates-3ca1`  
**Base:** `origin/deploy-vercel` @ `514ee671`  
**Audit date:** 2026-08-31  
**Discovery commands run:** layout `find`, house-style `find` (GATE/SCORECARD/NFL/CBB), scoped `rg` on CFB spine vocabulary, canary `rg`, `find *cfb*`, artifact JSON dumps via Python, live `resolve_season_universe` inspect.

**Opened paths (must be real):** see spine table + sections below. No WP / shock / power / KEI / publisher edits in Phase 0.

---

## Spine table

| Layer                                     | Path                                                                                         | Symbol                                                                                       | Reads                                                                                                                         | Writes                                                                                                       | Notes                                                                                                                                                                                                                                               |
| ----------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Results / schedule (official ESPN pack)   | `services/model-service/src/services/cfb_season_engine/data/cfb_official_schedule_2026.json` | `games[]` with `week`, `home`, `away`, `kickoff`                                             | `product_desk.official_week_board`, `scripts/cfb/build_cfb_kei_futures_2026.py`, `scripts/cfb/publish_official_slate_2026.py` | Publish scripts / manual pack refresh                                                                        | `as_of=2026-08-13`. **8 Week-0 games present; `home_score`/`away_score`/`status` all null — Week 0 not closed in schedule.**                                                                                                                        |
| Results / schedule (live season-sim seed) | `…/data/cfb_sample_schedule_2026.json` + `schedule.densify_schedule`                         | `densify_schedule`, `load_packaged_schedule`                                                 | `loaders.build_packaged_universe`                                                                                             | densify at load time                                                                                         | **Densified synthetic slate (~780 games, weeks 1–14). No Week 0. `official_schedule=false`.**                                                                                                                                                       |
| Power ratings (frozen SoT)                | `…/data/cfb_power_sot_2026.json` (+ web mirror `apps/web/lib/data/cfb-power-sot-2026.json`)  | `teams[].power_index` / `offense_index` / `defense_index`                                    | `apps/web/lib/cfb-research-artifacts.ts`, `build_cfb_kei_futures_2026.hydrate_missing_from_power_sot`, previews               | **Rebuild script NOT FOUND** (committed artifact only)                                                       | `power_version=cfb-power-sot-v0.15-20260814`, `power_as_of=2026-08-14`, `engine_version=cfb-season-engine-v0.15-power-sot`. OSU `power_index=1.6168` (**this is the ~1.617 canary power, not a WP logistic constant**).                             |
| Live compose / project-game               | `team_projection.py`, `priors.py`, `efficiency.py`, `loaders.py`                             | `compose_team_projection`, `project_game`, `expected_team_points`, `resolve_season_universe` | `/cfb/season-engine/*` via `routes/cfb.py`, `scripts/cfb/run_hierarchical_season_sim.py`                                      | in-memory universe; optional `in_season_update` state                                                        | Live `ENGINE_VERSION=cfb-season-engine-v0.9-inseason` (differs from frozen v0.15 stamp).                                                                                                                                                            |
| Game margin distribution                  | `team_projection.expected_team_points` → margin; sim noise via `realize_game_scores`         | `SCORE_NOISE_SD=12.5`, `score_noise_sd_for_week`                                             | project-game + season path                                                                                                    | priors knobs                                                                                                 | Early weeks inflate score noise (`EARLY_SEASON_SCORE_NOISE_MULT`).                                                                                                                                                                                  |
| P(win) [WP mapper]                        | `team_projection.win_prob_from_expected_scores`                                              | `Φ(margin / margin_sd)` via `math.erf`, clamp `[0.02, 0.98]`                                 | `project_game`, KEI `_wp_from_spread`                                                                                         | `priors.WIN_PROB_MARGIN_SD=15.2`, `win_prob_margin_sd_for_week`, team_u inflate `margin_sd *= 1+0.25*team_u` | **Week 0 uses base SD** (`early_season_factor` treats `w<1` as non-early). **Week 1–4 inflate** (`EARLY_SEASON_MARGIN_SD_MULT[1]=1.38`) → cupcake WPs soften into high-80s.                                                                         |
| Season simulator (API / CLI)              | `season_sim.simulate_full_season`                                                            | path-coherent `realize_game_scores` + `evolve_after_game`                                    | `run_hierarchical_season_sim.py`, `POST /cfb/season-engine/simulate`                                                          | none (returns dict)                                                                                          | Uses **densified** universe schedule. Notes still claim CFP deferred here.                                                                                                                                                                          |
| E[wins] / win-total band (published)      | `…/data/cfb_season_projections_2026.json` (+ web mirror)                                     | `teams[].mean/std/p10/p50/p90`                                                               | `cfb-research-artifacts.ts` → `/pro/cfb/projections`                                                                          | **Rebuild script NOT FOUND**                                                                                 | Method stamp: _“Frozen-SoT independent Bernoulli on official ESPN slate… In-path evolution off.”_ `n_sims=10000`, `n_games_scored=889`, `as_of=2026-08-14`. **Not** the densified `simulate_full_season` path.                                      |
| 12-team field constructor                 | `cfb_futures.select_cfp_field`                                                               | `AUTO_BIDS=5`, `AT_LARGE=7`, `_rank_key=(wins, power, team)`                                 | `accumulate_path` → futures artifact                                                                                          | `scripts/cfb/build_cfb_kei_futures_2026.py`                                                                  | **Docs/code:** top-5 conference champs by path rank (any conf) + 7 at-large by wins then power. **Brief wants:** ACC/B1G/B12/SEC autos + one G6 auto by power + power-aware at-larges — **code contradicts brief; record, do not silently invent.** |
| Playoff % / title %                       | `cfb_futures.accumulate_path`, `simulate_playoff`, `finalize_futures`                        | `cfp_make_pct`, `natty_pct`, `_playoff_wp` logistic `z=2.1*gap`                              | web `cfb-kei-artifacts.ts` / futures pages                                                                                    | same build script                                                                                            | Artifact `as_of=2026-08-17`, `n_sims=2500`. Playoff WP separate from game WP Φ curve.                                                                                                                                                               |
| KEI (published game line)                 | `cfb_kei.apply_cfb_kei`, `apply_bias_guard`                                                  | `kei_spread_home`, `kei_home_win_prob`                                                       | Edge Board / `product_desk._attach_kei`, web KEI pack                                                                         | `build_cfb_kei_futures_2026.py`                                                                              | **KEI = model spread + bias guard (+ menu labels). Not E[wins]/natty/playoff.** Rules: `data/ops/cfb-kei-rules-2026.md`.                                                                                                                            |
| Site / research surfaces                  | `apps/web/lib/cfb-*.ts`, `apps/web/app/(pro)/pro/cfb/**`                                     | frozen JSON loaders                                                                          | Next.js pages                                                                                                                 | artifact copies under `apps/web/lib/data/`                                                                   | Research `used_in_spread=false`; KEI board `used_in_spread=true`. Previews hardcode `CFB_PREVIEW_AS_OF="2026-08-14"`.                                                                                                                               |

---

## as_of inventory

| Surface                        | Value                               | Source opened                                        |
| ------------------------------ | ----------------------------------- | ---------------------------------------------------- |
| Official schedule pack         | `2026-08-13`                        | `cfb_official_schedule_2026.json`                    |
| Power SoT                      | `2026-08-14` (`power_as_of`)        | `cfb_power_sot_2026.json`                            |
| Season projections             | `2026-08-14`                        | `cfb_season_projections_2026.json`                   |
| Team previews const            | `2026-08-14`                        | `apps/web/lib/cfb-previews.ts` → `CFB_PREVIEW_AS_OF` |
| Roster snapshot (universe)     | `2026-08-12`                        | `resolve_season_universe` → `roster_as_of`           |
| Efficiency SP+ carry           | `2026-08-04`                        | universe notes `efficiency_as_of`                    |
| KEI W0/W1 board                | `2026-08-17`                        | `cfb_kei_w0_w1_2026.json`                            |
| Futures pack                   | `2026-08-17`                        | `cfb_futures_2026.json`                              |
| Live engine version stamp      | `cfb-season-engine-v0.9-inseason`   | `priors.ENGINE_VERSION`                              |
| Frozen power/proj engine stamp | `cfb-season-engine-v0.15-power-sot` | power/proj JSON                                      |

**Verdict:** CFB research surfaces **disagree** on `as_of` (08-13 / 08-14 / 08-17 / roster 08-12). Symptom #1 confirmed.

---

## Week 0 close path

**What exists today**

| Piece                                                               | Path                                                                    | Role                                                                                            | Safe for “close without power refit”?                                                        |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Official Week-0 slate                                               | `cfb_official_schedule_2026.json`                                       | 8 games (UNC@TCU, SJSU@USC, NCSU@UVA, JVST@fcs:NDSU, fcs:SAC@EMU, HAW@STAN, NMSU@FSU, MEM@UNLV) | Scores **missing**                                                                           |
| The Book ledger                                                     | `scripts/cfb/book_close_grade.py`, `data/ops/book/cfb-2026-08-29.json`  | Bet close/grade vs ESPN finals                                                                  | Grades bets; **does not** advance research `as_of` or lock sim state                         |
| Performance tracking                                                | `performance_tracking.record_result` + `POST …/projections/{id}/result` | Grade a logged projection                                                                       | Tracking only                                                                                |
| In-season efficiency update                                         | `in_season_update.ingest_result` + `POST …/in-season/ingest-result`     | Shrinkaged off/def efficiency moves from residual                                               | **Unsafe for this pass** — moves ratings (power-adjacent). Brief forbids Week-0 power refit. |
| Dedicated “close Week 0 → one as_of → re-sim from frozen power” CLI | —                                                                       | —                                                                                               | **NOT FOUND**                                                                                |

**Gaps that block a literal close**

1. No finals written into the official schedule pack.
2. Published win totals are a **frozen Bernoulli artifact** on the official slate; rebuild script **NOT FOUND**.
3. Live `simulate_full_season` uses a **different densified schedule** with **no Week 0 games** and no “lock completed results” start-state.
4. Using `in_season_update` would violate law 3 (no power refit from Week 0).

**Phase 1 implication:** Close must be invented only as bookkeeping on the **existing** official-slate + frozen-SoT path (write finals, advance `as_of`, re-run the existing Bernoulli/futures builders **without** calling `ingest_result` efficiency moves). If official-slate Bernoulli rebuild cannot be named from an existing function, stop that layer and write a blocker — do not invent `cfb_v2`.

---

## WP mapper (formula, constants, 3–5 current cupcake examples)

**Opened:** `team_projection.win_prob_from_expected_scores`, `project_game` margin_sd assembly, `priors.WIN_PROB_MARGIN_SD`, `cfb_kei._wp_from_spread`.

**Formula (research model):**

```text
margin = home_exp - away_exp
margin_sd = WIN_PROB_MARGIN_SD * early_season_factor(week, EARLY_SEASON_MARGIN_SD_MULT)
margin_sd *= 1.0 + 0.25 * mean(home.early_season_uncertainty, away.early_season_uncertainty)
z = margin / max(8.0, margin_sd)
home_wp = clamp( Φ(z), 0.02, 0.98 )   # Φ via erf
```

**Constants:** `WIN_PROB_MARGIN_SD = 15.2`; W1 mult `1.38` → base ~21.0 before team_u; clamp max **0.98** (not soft saturation to 0.99+).  
**Note:** `~1.617` in previews is **OSU power_index**, not this mapper’s scale. Playoff logistic uses `z = 2.1 * power_gap` in `cfb_futures._playoff_wp`.

**Cupcake examples dumped from live KEI board artifact** (`apply_cfb_kei` stamped model WP from `project_game`):

| Game      | Week | model_spread | model_wp   | kei_wp | model_sigma |
| --------- | ---- | ------------ | ---------- | ------ | ----------- |
| BALL@OSU  | 1    | −41.00       | **0.9652** | 0.9691 | 22.59       |
| UTEP@OU   | 1    | −32.41       | **0.9233** | 0.9307 | 22.70       |
| MOST@TAMU | 1    | −31.05       | **0.9168** | 0.9247 | 22.44       |
| FRES@USC  | 1    | −28.56       | **0.8940** | 0.9033 | 22.88       |
| MASS@RUT  | 1    | −26.22       | **0.8793** | 0.8897 | 22.38       |
| SJSU@USC  | 0    | −33.04       | 0.9789     | 0.9800 | 16.26       |
| NMSU@FSU  | 0    | −14.86       | 0.8174     | 0.8361 | 16.41       |

**Reading:** True monsters (~30+ pts) can still clear 90s; mid-cupcakes (~26–29 pts) in **Week 1** print **high-80s** because early `margin_sd` inflate. Week 0 skips early mult → same-class gaps look sharper. Symptom #2 confirmed on W1 cupcakes.

**Suggested gate threshold T (power units):** document in Phase 1 from engine power gaps (e.g. favorite–dog `power_index` gap or projected margin pts). Candidate: projected \|margin\| ≥ ~28 on home/neutral out-of-class ⇒ WP ≥ 0.90 after fix (measure from mapper, not Vegas).

---

## Year-shock

**Literal symbols `year_shock` / `yr_shock` / `team_season_sigma`:** **NOT FOUND.**

**Named variance stack that drives season bands (opened):**

| Knob                                                        | Path                                                                            | Symbol                                                 | Role                                                                                                          |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Score noise (primary band driver for Bernoulli + path sims) | `priors.py` / `realize_game_scores`                                             | `SCORE_NOISE_SD=12.5`, `EARLY_SEASON_SCORE_NOISE_MULT` | Independent game outcomes stay noisy → win totals compress toward similar widths                              |
| In-path strength evolution noise                            | `priors.STRENGTH_NOISE=0.014`, `EARLY_STRENGTH_NOISE_MULT`, `evolve_after_game` | week-indexed gauss bumps                               | **Off** for published Bernoulli artifact (`method` says evolution off); **on** for API `simulate_full_season` |
| Early identity uncertainty                                  | team `early_season_uncertainty`, `EARLY_SEASON_MARGIN_SD_MULT`                  | widens WP SD / softens favorites                       | Soft WP + fat score noise ⇒ USF-class ≈ OSU-class bands                                                       |

**Audit choice for Phase 1:** the lever that drives **published** win-total width is the **score-noise / WP softness pair** on the official-slate Bernoulli path (artifact method), not a separate year-shock module. Document `STRENGTH_NOISE` as the secondary path-sim shock; change the one that feeds the published board after the rebuild function is named.

**Baseline symptom:** USF width `p90−p10 = 4.0` **equals** OSU width `4.0` (both 7–11). USF E[wins] `8.884` ≈ OSU `8.883`.

---

## Futures / 12-team constructor

**Opened:** `cfb_futures.py`, `data/ops/cfb-season-rules-2026.md`, futures JSON.

| Rule       | Repo today                                   | Brief target                                                   |
| ---------- | -------------------------------------------- | -------------------------------------------------------------- |
| Field size | 12                                           | 12                                                             |
| Autos      | 5 highest-ranked **any-conference** champs   | ACC + Big Ten + Big 12 + SEC + **one G6** by engine power/rank |
| At-large   | next 7 by `(wins, power, team)` on the path  | **power-aware** (wins alone must not mint title tails)         |
| Byes       | seeds 1–4                                    | same                                                           |
| Title %    | bracket sim after field (`simulate_playoff`) | same (not “11+ wins ⇒ title”)                                  |
| Playoff WP | logistic `2.1 * power_gap`, clamp 0.08–0.92  | keep; do not stretch to Vegas                                  |

**Contradiction:** code/docs (`cfb-season-rules-2026.md`) describe top-5 conf champs; brief wants P4 + G6 auto. Phase 1 must **record** and align field constructor carefully without inventing a 16-team world.

---

## KEI definition (verbatim from code or existing docs)

From `cfb_kei.py` module docstring (opened):

> Model = pure research fair. This module never mutates model\_\* fields.  
> KEI = model + versioned handicap menu + measured bias guard.  
> Market is information only. \|KEI − open\| ≥ threshold → INVESTIGATE, never auto-move KEI to the open.  
> Edge / Tag = KEI vs best market only.

From `data/ops/cfb-kei-rules-2026.md`:

> **KEI** = published line = model + versioned menu + measured bias guard. `used_in_spread=true`.

**Numeric default:** `apply_bias_guard` only (early weeks): home-fav −1.20 / home-dog +1.00 capped; short-fav shrink; then `_wp_from_spread(kei_spread, margin_sd)`.

**Not** E[wins], natty %, or playoff %. Team season tails live in projections/futures packs, separate files. **No `KEI_EQUALS_TAIL` today** — guard still required so a publisher cannot collapse them later.

---

## Canary baselines (OSU, USF, Utah, top-7 vector, cupcake WPs)

**Dump source:** Python read of model-service + web-mirrored JSON artifacts on 2026-08-31 (Phase 0). Functions named below.

| Metric                  | OSU                         | USF              | UTAH            | Function / artifact                                 |
| ----------------------- | --------------------------- | ---------------- | --------------- | --------------------------------------------------- |
| power_index             | 1.6168 (rank 1)             | 1.2601 (rank 43) | 1.4841 (rank 9) | `cfb_power_sot_2026.json`                           |
| E[wins] mean            | 8.883                       | 8.884            | 9.014           | `cfb_season_projections_2026.json` (`teams[].mean`) |
| win-total width p90−p10 | 4.0 (7–11)                  | 4.0 (7–11)       | 4.0 (7–11)      | same (`p10`/`p90`)                                  |
| std                     | 1.460                       | 1.474            | 1.475           | same                                                |
| cfp_make_pct            | 90.7                        | 24.8             | 73.2            | `cfb_futures_2026.json` via `finalize_futures`      |
| natty_pct               | 17.0                        | 0.2              | **6.6**         | same                                                |
| KEI (team season)       | n/a — KEI is game-line only | n/a              | n/a             | `apply_cfb_kei`                                     |
| as_of (proj/power)      | 2026-08-14                  | 2026-08-14       | 2026-08-14      | artifacts                                           |
| as_of (futures/kei)     | 2026-08-17                  | 2026-08-17       | 2026-08-17      | artifacts                                           |

**Top-7 power vector** (`power_index` descending):  
1 OSU 1.6168 · 2 ORE 1.5625 · 3 MISS 1.5479 · 4 MIA 1.5309 · 5 IU 1.5232 · 6 TAMU 1.5190 · 7 ND 1.5016

**Cupcake WPs:** see WP mapper table above.

**Cannot dump from live site functions without Railway:** web pages read the same frozen JSON via `cfb-research-artifacts.ts` / `cfb-kei-artifacts.ts`. Phase 1 dump script must call those loaders or the Python builders that produce the same files (`project_game_preview` / `apply_cfb_kei` / futures finalize) — not a parallel math path.

---

## Shared-code risk (NFL/CBB/MLB)

| Shared piece                         | Path                                                                              | Risk                                                                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `proof_layer`                        | `services/model-service/src/services/proof_layer/*` via `performance_tracking.py` | Shared across sports. **Do not change core proof_layer for CFB-only WP/shock.** CFB adapter-only edits if needed; else blocker. |
| Book ledger                          | `services/model-service/src/services/book_ledger/*`                               | Shared grading; Week-0 bet grades ≠ research close. Touch only CFB snapshot helpers if required.                                |
| NFL enterprise gates / season engine | `docs/NFL_ENTERPRISE_GATES.md`, `scripts/nfl/*`, `nfl_*`                          | **Clone tone only.** Do not edit.                                                                                               |
| CBB KEI docs                         | `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`                                       | Reference only. No CBB code edits.                                                                                              |
| MLB trees                            | `docs/MLB_*`, mlb services                                                        | Untouched.                                                                                                                      |

---

## Existing gates / scorecards to clone

| Asset                    | Path                                                                          | Use                                                                                       |
| ------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| NFL enterprise gates doc | `docs/NFL_ENTERPRISE_GATES.md`                                                | Tone/structure for `docs/CFB_ENGINE_GATES.md`                                             |
| NFL gate evaluator       | `scripts/nfl/evaluate_enterprise_gates.py`, `nfl_enterprise_gates.py`         | Pattern only — add **CFB-only** module beside CFB tests                                   |
| CFB tests present        | `services/model-service/tests/test_cfb_*.py` (kei, futures, season_engine, …) | Add `test_cfb_enterprise_gates.py` here                                                   |
| Web CFB tests            | `apps/web/__tests__/lib/cfb-*.ts`                                             | Optional as_of / KEI≠tail asserts                                                         |
| Ops scorecard-ish        | `data/ops/cfb-independent-kei-futures-20260817.md`, walkforward summaries     | Not a before/after engine scorecard — Phase 1 writes `docs/CFB_ENGINE_WEEK0_SCORECARD.md` |

**CBB enterprise gates file:** **NOT FOUND** (no `docs/CBB_ENTERPRISE_GATES.md`).

---

## Blockers already visible

1. **`SCHEDULE_FORK`:** Live API season sim = densified sample; published win totals = official-slate Bernoulli artifact; futures builder = official slate. One engine package, **two schedule spines**. Closing Week 0 on official results does not automatically update densified API sims. Must unify on allowlisted loaders or stop with blocker — **do not invent `cfb_v2/`**.
2. **`CLOSE_PATH_MISSING`:** No idempotent Week-0 close that writes finals + single `as_of` + re-sim **without** `in_season_update` power moves. Schedule scores null.
3. **`PROJECTIONS_REBUILD_NOT_FOUND`:** No script in `scripts/cfb/` that regenerates `cfb_season_projections_2026.json` / power SoT (only KEI/futures builder found). Canary dump can read artifacts; rematerialize may block.
4. **`YEAR_SHOCK_NAME`:** No symbol named year-shock; mapped to score-noise + early WP inflate (+ optional `STRENGTH_NOISE`). Acceptable if Phase 1 documents the chosen symbol; blocker only if still unnameable after allowlist work.
5. **`FUTURES_FIELD_RULES_DRIFT`:** Code/docs autos ≠ brief’s P4+G6 auto. Recorded; fix on allowlist in `cfb_futures.py` without team-id hacks.
6. **`ASOF_SPLIT` + `ENGINE_VERSION_SPLIT`:** 08-13/14/17 and v0.15 vs v0.9 stamps.
7. **Utah natty 6.6%:** Already near the ~5% symptom. After real WP+shock+power-aware field, if still ~5%, write `docs/CFB_ENGINE_BLOCKER.md` — do not stretch Φ / `2.1` logistic / OSU’s 1.6168 power.
8. **Shared `proof_layer`:** Do not retune for CFB WP.

None of these authorize Utah/USF branches or market blend.

---

## Phase 1 file allowlist

Only these paths may be edited/added in Phase 1 (plus regenerating listed JSON artifacts they already own):

### Docs (required / conditional)

- `docs/CFB_ENGINE_ONE_PASS_BRIEF.md`
- `docs/CFB_ENGINE_AUDIT_WEEK0.md`
- `docs/CFB_ENGINE_GATES.md`
- `docs/CFB_ENGINE_WEEK0_SCORECARD.md`
- `docs/CFB_ENGINE_BLOCKER.md` _(only if a law forces stop)_

### Engine (CFB season engine only)

- `services/model-service/src/services/cfb_season_engine/priors.py`
- `services/model-service/src/services/cfb_season_engine/team_projection.py`
- `services/model-service/src/services/cfb_season_engine/season_sim.py`
- `services/model-service/src/services/cfb_season_engine/schedule.py`
- `services/model-service/src/services/cfb_season_engine/loaders.py`
- `services/model-service/src/services/cfb_season_engine/cfb_futures.py`
- `services/model-service/src/services/cfb_season_engine/cfb_kei.py` _(guard/assert only — no new formula)_
- `services/model-service/src/services/cfb_season_engine/product_desk.py`
- `services/model-service/src/services/cfb_season_engine/__init__.py` _(lineage / as_of plumbing only)_
- `services/model-service/src/services/cfb_season_engine/types.py` _(only if close start-state fields required)_
- `services/model-service/src/routes/cfb.py` _(as_of / close wiring only; no NFL routes)_

### Data artifacts (CFB only — mirrors must stay in sync)

- `services/model-service/src/services/cfb_season_engine/data/cfb_official_schedule_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_season_projections_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_futures_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_official_slate_2026.json`
- `apps/web/lib/data/cfb-power-sot-2026.json`
- `apps/web/lib/data/cfb-season-projections-2026.json`
- `apps/web/lib/data/cfb-futures-2026.json`
- `apps/web/lib/data/cfb-kei-w0-w1-2026.json`
- `apps/web/lib/data/cfb-official-slate-2026.json`
- `apps/web/data/processed/kei_lines_cfb.json`

### Scripts / tests

- `scripts/cfb/build_cfb_kei_futures_2026.py`
- `scripts/cfb/cfb_dump_canaries.py` _(new)_
- `scripts/cfb/close_week0.py` _(new only if required to name the close path; must call existing engine functions)_
- `scripts/cfb/rebuild_season_projections_2026.py` _(new only if projections rebuild is otherwise NOT FOUND — must reuse `project_game` / official slate, not a second model)_
- `services/model-service/tests/test_cfb_enterprise_gates.py` _(new)_
- `services/model-service/tests/test_cfb_futures.py` _(field-rule asserts)_
- `services/model-service/tests/test_cfb_kei.py` _(KEI ≠ tail assert)_
- `apps/web/lib/cfb-previews.ts` _(as_of const only)_
- `apps/web/lib/cfb-research-artifacts.ts` / `apps/web/lib/cfb-kei-artifacts.ts` _(lineage footer only)_
- `data/ops/cfb-kei-rules-2026.md` / `data/ops/cfb-season-rules-2026.md` _(rule sync if field constructor changes)_

### Explicitly excluded

- Any `services/**/nfl_*`, `**/cbb*`, `**/mlb*`, `scripts/nfl/**`, NFL/CBB/MLB docs besides read-only clone reference
- `in_season_update.py` efficiency refit path for Week-0 training
- New package trees / `cfb_v2/`

---

## Phase 0 commands captured

```bash
ls -la
find . -maxdepth 3 -type d -not -path './.git*' -not -path './node_modules*' | head -200
find . -iname '*GATE*' -o -iname '*SCORECARD*' -o -iname '*NFL*ENGINE*' -o -iname '*CBB*ENGINE*' | head -80
rg -n -i --glob '!{**/.git/**,**/node_modules/**,**/*.lock}' 'KEI|…|cfp' | head -400
rg -n -i --glob '!{**/.git/**,**/node_modules/**}' 'South Florida|\bUSF\b|\bUtah\b|Ohio State|\bUNC\b|TCU' | head -200
find . -type f \( -iname '*cfb*' -o -iname '*ncaaf*' -o -iname '*college*football*' \) -not -path './.git/*' | head -200
# plus scoped rg under cfb_season_engine/ + Python artifact dumps + resolve_season_universe()
```

`rg` available at `/exec-daemon/rg`.

---

## Phase 0 freeze confirmation

No WP, shock, power, Utah/USF, or publisher notebook edits were made in Phase 0. Next commit should be docs-only (`docs: CFB Week 0 audit`), then Phase 1 strictly on the allowlist above.
