# t5014u RO — Q2 keep → operational Independent Fair path

**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · pub/bet HOLD  
**Mode:** paper / read-only inspection. No merge · no deploy · no EVAL retune · no Stage C EXEC · no scored reuse of hist index `1ee90fac` · no model math/feature change · no 2024–25 access.

**Authority:** OWNER t5014u coordination session + bounded delegation `97925eb5`.  
**Baseline:** OWNER ACCEPT keep Q2 Phase B tip `03a4dd90` (FROZEN fit `70db070d` · config `aa2b47b3` · EVAL one-look kept · research-consumed).

**Packet SoT (do not merge):** draft PR [#679](https://github.com/kosedge/kosedge/pull/679) · branch `cursor/q2-phase-b-exec-a5ff` @ `af6be4f59c63af222d02c39878266460a37d418a`.  
This file is docs-only on `deploy-vercel`. Packet paths below are cited from that draft tree.

**IF in this report = Independent Fair (CLEAR-A), not injury-factor.** Injury overlays live on `NflGameInputs.injury_nowcast_*` and are out of Q2 keep scope.

---

## 0. Inspection identity

| Item | Value |
|---|---|
| This RO | t5014u · `research/q2_phase_b_t5009u/RO_IF_DEPENDENCY_MAP_t5014u.md` |
| Inspected live tip | `origin/deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f` |
| Q2 EXEC commit | `af6be4f59c63af222d02c39878266460a37d418a` (PR #679, DRAFT) |
| CLEAR-A IF merge | `1b39f4e9f6b2e04c264a41831f3bb7273e475011` (#657) — **code is on `deploy-vercel`** |
| Packet COMPONENTS | `ops/nfl_enterprise_green_t4359u/COMPONENTS_Q2PB_t5009u.md` sha256 `5a89fb63…` |

### Cited tips — box-verified on this clone vs coordination-only

| Tip | What it is | On this clone? |
|---|---|---|
| keep `03a4dd90` | OWNER ACCEPT keep (t5014u baseline) | **Not a git object / file** on `deploy-vercel` or #679. Cited from OWNER session. Packet itself still says “no self-ACCEPT.” |
| FROZEN md `28c582a1` | sha256 of `FROZEN_CONFIG_Q2PB_t5009u.md` | **VERIFIED** (`28c582a1b2b9ac49…`) |
| EVAL md `fe90f5f0` | sha256 of `EVAL_ONELOOK_Q2PB_t5009u.md` | **VERIFIED** (`fe90f5f0cb19378f…`) |
| fit `70db070d` | sealed fit object sha256 | **VERIFIED** inside FROZEN md/json |
| config `aa2b47b3` | sealed config sha256 | **VERIFIED** inside FROZEN md/json |
| Alex RO `d12898a2` | post-EXEC Alex RO (cited) | **Not a git object / file** on this clone |
| erratum `06849c65` | cited erratum | **Not a git object / file** on this clone |
| gate `83646d78` | no scored reuse of hist index `1ee90fac` | Cited throughout #679 packet; **no gate file** on `deploy-vercel` |
| delegation `97925eb5` | bounded RO delegation | **Not a git object / file** on this clone |
| as-of `cf514078` | kickoff < target | **VERIFIED** as `TIP_ASOF_KICKOFF` in packet `q2pb/constants.py`; **absent** from live IF Python |
| IF pin `6ca03716` | Phase A / eval-spec IF pin | Cited in #679 authority papers; **absent** from live IF tree |
| contract `b41f4b43` | Phase A “interface only” field map | Cited in #679 authority papers; **absent** from live IF tree |
| S1 kill `50f57195` | EPA-trail family kill | Cited in packet; **do not revive** |
| games `4fe1cdd7` | primary games.csv | **VERIFIED** on #679 (`games_4fe1cdd7.csv`) |
| outcomes `50bda875` | score-only 2013–2022 extract | **VERIFIED** on #679 |
| sim pin D3(ii) `75ee2ee9…` | CLEAR-A flag-OFF blended hash | **VERIFIED** live (`test_nfl_handicap_clear_a_d3.py`) |

`docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` still says “DRAFT PR only · not merged.” That sentence is **stale**: #657 is on `deploy-vercel` as `1b39f4e9`. Ledger + IF helpers remain **DEVELOPMENT_ONLY — not wired to production callers**.

---

## 1. DEPENDENCY MAP

Classification is **relative to the live Independent Fair caller / pipeline** on `deploy-vercel`. Packet status is recorded beside it. Components are exactly those in `COMPONENTS_Q2PB_t5009u.md`.

**IF live path (what “live” means here):**

```
tasks.run_nfl_market_simulations
  → _load_team_strength_priors(session, season_year, as_of_week=matchup_week)
  → _resolve_team_strength_indices(...)          # prefers EPA prior; W-L record is cold-start only
  → NflGameInputs(offense_index_*, defense_index_*)
  → simulate_nfl_game(...)                      # PRODUCTION default; market blend ON
```

Independent Fair entry is **code-present, callers = tests only**:

```
simulate_nfl_game_independent_fair
  → simulate_nfl_game(..., independent_fair=True)   # market_blend exact 0
  → independent_fair{margin_mu, total_mu, sigma}
```

Only non-definition imports of `simulate_nfl_game_independent_fair` / `independent_fair_mus`:  
`services/model-service/tests/test_nfl_handicap_clear_a_d3.py` (plus `independent_fair_mus` in `test_nfl_handicap_clear_a_d1_d4_remotion.py`).

| # | Q2 keep component | Packet path / symbol | Packet | vs live IF caller/pipeline |
|---|---|---|---|---|
| 1 | As-of ridge Massey | `research/q2_phase_b_t5009u/q2pb/strength.py` · `solve_ridge` · `asof_for_targets` · `AsOfFeatures` · `StrengthSolve` · `carry_prior` · `season_end_ratings` | EXISTING AND VERIFIED on #679 (sealed λ=20, r=0.5, fit `70db070d`) | **MISSING.** Live strength is EPA rolling + packaged priors → `offense_index_*` / `defense_index_*`. No Massey, no ridge `margin = h + s_i − s_j`, no `home_s`/`away_s`/`rating_diff` on `NflGameInputs`. |
| 2 | `asof_wl_diff` | `research/q2_phase_b_t5009u/q2pb/metrics.py` · `asof_wl_diff` · `record_wl_diff` | EXISTING AND VERIFIED on #679 (definition frozen; Pearson vs `record_entering_*` mapping = 0.99993) | **MISSING.** No `wl_diff` / `asof_wl_diff` field on IF inputs, L0, or sim. Live path **de-preferenced** W-L record index (`_resolve_team_strength_indices` docstring: ESPN W-L was a silent override; EPA now preferred). |
| 3 | Score-only extract | `research/q2_phase_b_t5009u/extract_outcomes_score_only.py` · `data/outcomes_2013_2022_score_only.csv` (`50bda875`) | EXISTING AND VERIFIED as six-column public finals; **gate `83646d78` still binds** (not an experiment frame) | **MISSING** from IF. Live outcomes are DB/sim, not this extract. A `historical_oos_games.csv` path exists under `data/ops/nfl-reopening-packet-20260916/historical-oos/` — **not hashed, not opened, not used** in this RO. |
| 4 | Freeze barrier | `research/q2_phase_b_t5009u/run_q2_phase_b.py` · `phase1_dev` · `_write_sealed` · `eval_rows_read=false` before EVAL | EXISTING AND VERIFIED on #679 (`28c582a1` / `aa2b47b3`, freeze `2026-10-31T18:08:23.133346-04:00`) | **MISSING.** IF does not consume FROZEN_CONFIG. No freeze-before-EVAL barrier on the sim/ledger path. |
| 5 | Leakage assert | `q2pb/strength.py` · `assert_asof_leakage` (same-kickoff and later excluded; rule `cf514078`) | EXISTING AND VERIFIED on #679 + unit guard | **MISSING as this assert.** Closest live analog is **week-cap**, not kickoff-instant: `_load_team_strength_priors(..., as_of_week=)` → `_fetch_rolling_feature_latest_rows(..., week_cap=)`. Ledger uses `canonicalize_as_of_ts` / `as_of_ts ≤ decision_ts` (`nfl_handicap_ledger/identity.py`) — identity clock, not Massey design-matrix leakage. **Do not treat week-cap as `cf514078` verified.** |
| 6 | DEV maps | `q2pb/metrics.py` · `ols` · `logistic_mle` · `LinearMap` · `LogisticMap` | EXISTING AND VERIFIED on #679 (DEV 2013–16 only; coefficients in FROZEN md) | **MISSING / not a live IF consumer.** IF margin is `compute_nfl_projection_decomposition` → MC means, not `pm_new = 2.56374413 + 1.66062406 · rating_diff`. |
| 7 | Cluster bootstrap | `q2pb/metrics.py` · `cluster_bootstrap` (B=10000, seed 4918) | EXISTING AND VERIFIED on #679 (EVAL one-look `fe90f5f0`) | **SUPERSEDED as an IF runtime dependency.** Eval harness only. No further Q2 EVAL/retune. |
| 8 | Team-season ICC | `q2pb/metrics.py` · `icc_oneway` | EXISTING AND VERIFIED on #679 (DEV residual ICC **0.0195** replaces design ASSUMPTION 0.02–0.04) | **SUPERSEDED as an IF runtime dependency.** Design-assumption close only. |
| 9 | Season-firewall CSV loader | `q2pb/data.py` · `load_games` · `window_rows` · `load_outcomes_score_only` · `verify_games_pin` | EXISTING AND VERIFIED on #679 (phase 1 materializes 2013–16 only) | **MISSING** from IF. Live loaders are SQL rolling-feature / packaged JSON, not this CSV firewall. |
| 10 | Unit guards | `research/q2_phase_b_t5009u/tests/test_q2pb_guards.py` | EXISTING AND VERIFIED on #679 | **MISSING** from IF test suite. CLEAR-A tests cover blend=0 / ledger reject, not Massey leakage. |

### Not in COMPONENTS_Q2PB — still binding

| Item | Status vs IF |
|---|---|
| EPA / PBP secondary (Phase A: PBP `6ee24b44`, mapping `b41f4b43`) | **SKIPPED on Q2 keep** (no PBP on prior VM). This VM: **no** NFL `play_by_play_{2012–2022}.parquet` and **no** `6ee24b44` artifact. Production NFL PBP **schema** exists (`infra/db/013_nfl_pbp_normalized.sql`, `034_nfl_pbp_tendency_columns.sql`) and packaged EPA priors exist (`nfl_season_engine/data/nfl_team_epa_priors_2026.json`) — those feed **live EPA indices**, not Q2 secondary mapping. **`b41f4b43` = EXISTING BUT UNVERIFIED** (Phase A citation only; no map file on this clone). **Do not revive S1** (kill `50f57195` / design also cites `20c49524`; pins differ, not reconciled here). |
| Hist index `1ee90fac` as experiment frame | **BLOCKED** (gate `83646d78`). Score-only extract is not a license to reload scored columns / trailing_* / EPA / 2023–26. |
| Stage C (Q1) | **AMEND — not cleared.** |
| Lane S / sealed 70 / 2017 | EXCLUDED from Q2 fit/EVAL. Do not reopen. |

---

## 2. CONTRACT MAP

### 2a. What IF currently consumes

| Concern | Live fields / modules | Pin if any | Notes |
|---|---|---|---|
| Team strength | `NflGameInputs.offense_index_home/away`, `defense_index_home/away` | none of `6ca03716` / `b41f4b43` / `cf514078` | Built in `tasks._load_team_strength_priors` + `tasks._resolve_team_strength_indices`. Backbone: `nfl_season_engine.efficiency_backbone` (`epa_to_strength_indices`, `strength_payload_from_package`, `EFFICIENCY_BACKBONE_VERSION`). Optional packaged override `load_packaged_epa_priors`. |
| Margin prediction | `compute_nfl_projection_decomposition` → MC `margins` → `independent_fair.margin_mu` | D3(ii) `75ee2ee9…` (flag-OFF hash); seed `D3II_FIXED_SEED=47401` | IF forces `market_blend=0` and does **not** shift MC draws. Default live path blends toward market (`NFL_MARKET_BLEND_*`). |
| Totals / sigma | `independent_fair.total_mu`, `independent_fair.sigma` | same | From MC totals + framework `base_score_stdev`. |
| `wl_diff` | **not consumed** | — | W-L record index is cold-start fallback only. |
| As-of (strength) | `as_of_week` on `_load_team_strength_priors`; `NflGameInputs.kav_as_of_week`, `second_order_as_of_week`, `matchup_week` | not `cf514078` | Week grain, not kickoff-instant. |
| As-of (ledger identity) | L0/L1/L4 `as_of_ts`; `canonicalize_as_of_ts`; `business_identity_key` | blueprint comments `243a384e`, `908b21b4` | `as_of_ts` is capture identity, not Massey history filter. |
| Exposure / ledger L0 | `L0_REQUIRED_FIELDS`: `game_id`, `model_version`, `as_of_ts`, `capture_id`, `baseline_personnel_ref`, `off_eff_h/a`, `def_eff_h/a`, `pace_h/a`, `margin_mu`, `total_mu`, `sigma`, `market_blend` (exact 0) | schema `handicap-ledger-v0-clear-a` | **No prod writer.** Residual **R1/F8 “oracle strength”** still open in `schema.py`. |
| Offline / prod callers | Prod: `tasks.run_nfl_market_simulations` → `simulate_nfl_game` (blend ON). HTTP: `routes/nfl.py`. IF explicit entry: tests only. | `NFL_INDEPENDENT_FAIR_PATH = False` (doc only; **not** an env kill-switch) | `pre_blend_model_markets_from_diagnostics` aligns IF mus to blended-run diagnostics; it is not a strength module. |

`NflGameInputs` also carries 5g EPA / success / KAV / injury nowcast / weather / travel / tendency. Those are **live sim factors**, not Q2 keep outputs. Swapping them is a math/feature change (Needs Ryan).

### 2b. What Q2 keep already emits (frozen; do not retune)

From `AsOfFeatures` + FROZEN maps (`28c582a1` / `aa2b47b3`):

| Q2 field | Source | Frozen use |
|---|---|---|
| `home_s`, `away_s`, `rating_diff` (= home_s − away_s) | `asof_for_targets` | Spearman screen; input to DEV OLS |
| `hfa`, `n_asof_games` | `StrengthSolve` / `AsOfFeatures` | diagnostics |
| `asof_wl_diff` | `asof_wl_diff(game, history)` | win% home − away; kickoff < target; 0-0 → 0.5 |
| `pm_new` | DEV OLS: `2.56374413 + 1.66062406 · rating_diff` | mapped margin; **do not refit** |
| `pm_WL` | DEV OLS: `2.77041980 + 10.71786351 · wl_diff` | comparator only |
| `P_new` | DEV logistic on `pm_new` | Brier only; not an IF input |
| identity | `Game.key` = `(season, week, home, away)` + `game_id` + `kickoff_utc` | join key |

### 2c. Interface-only: optional Q2 consume **without** changing frozen IF math

Frozen IF math = `compute_nfl_projection_decomposition` + MC loop + `independent_fair=True` blend-zero. **Do not write Q2 ratings into `offense_index_*` / `defense_index_*` / `off_eff_*`.** That would change the sim.

Required if OWNER later wants a sidecar (interfaces only — **not implemented here**):

```
Q2AsOfSidecar  (research annotation; fail-closed if any field missing)
  game_id, season, week, home, away, kickoff_utc
  q2_home_s, q2_away_s, q2_rating_diff, q2_hfa, q2_n_asof_games
  q2_asof_wl_diff
  q2_pm_new                    # apply frozen DEV map only; no new OLS
  q2_fit_sha = 70db070d…
  q2_config_sha = aa2b47b3…
  q2_asof_rule = cf514078
  q2_games_pin = 4fe1cdd7
```

Join: `game_id` if both sides share it; else `Game.key`.  
Attach **beside** L0 / IF projection as non-authoritative payload.  
Do **not** set `L0.market_blend`.  
Do **not** overwrite `independent_fair.margin_mu`.  
Do **not** load `1ee90fac` scored columns to build the sidecar.  
Reuse existing symbols only: `asof_for_targets`, `asof_wl_diff`, `assert_asof_leakage`, sealed FROZEN maps.

`b41f4b43` remains the Phase A name for “contract field names, interface only.” It is **EXISTING BUT UNVERIFIED** on this clone (no artifact file). A future adapter paper should either reproduce that map from a located box or declare a new named interface — **Needs Ryan if it claims to be `b41f4b43`.**

`6ca03716` is the Phase A IF pin. Live IF SoT on this branch is CLEAR-A `1b39f4e9` / ledger schema `handicap-ledger-v0-clear-a`. Treat `6ca03716` as **EXISTING BUT UNVERIFIED** (citation without file), not as the live caller.

---

## 3. BOUNDED PROPOSAL (paper only · Needs OWNER if EXEC)

**Smallest next step toward operational IF that reuses Q2 keep, without Stage C, without scored `1ee90fac` reuse, preferring existing code:**

Keep Q2 where it is (draft #679). Do not merge it. Do not retune. Do not call `simulate_nfl_game_independent_fair` from a new Q2 runner.

Next concrete artifact (still paper until OWNER CLEAR): a **sidecar field contract** that lists the `Q2AsOfSidecar` keys above and the join to `game_id` / `Game.key`, stating explicitly that IF `margin_mu` and `offense_index_*` stay untouched. Implementation, if later CLEARED, is a read of existing `asof_for_targets` + frozen coefficients — no new ridge, no second EVAL look.

That is the existing-code path: the solve, leakage assert, `asof_wl_diff`, and freeze already exist on #679; the IF envelope and labeled IF entry already exist on `deploy-vercel`. The gap is a **named optional annotation**, not a new strength engine.

### CoS may ACCEPT under standing RO authority

- This RO map (docs-only; CERT=0).
- Filing Q2 keep as **research-consumed** (OWNER ACCEPT `03a4dd90`) without promoting #679.
- Commissioning the sidecar **paper** (interfaces only; no code).
- Confirming EPA secondary stays SKIPPED; S1 stays killed (`50f57195`).
- Confirming gate `83646d78` still blocks scored `1ee90fac` reuse.
- Non-exec inspection notes (paths, shas, “not wired”).

### Needs Ryan (math / features / eval rules / protected data / merge)

- Any EXEC: sidecar writer, IF caller wiring, ledger L0 capture, Railway/Vercel, merge of #679 or this PR.
- Writing Q2 ratings into `NflGameInputs` or L0 `off_eff_*` / `margin_mu`.
- Any new fit, map, bootstrap, EVAL look, or threshold change.
- Stage C EXEC or AMEND lift.
- Opening 2024–25 or sealed holdouts.
- Scored reuse / reload of `1ee90fac` beyond the already-documented six-column extract.
- Claiming `b41f4b43` or `6ca03716` verified without locating the box.
- Reviving S1 / EPA-trail / `trailing_*`.
- CERT>0, pub, bet, production promote.

---

## 4. HARD HOLDS (do not propose lifting)

- Stage C AMEND
- Scored feature reuse of `1ee90fac` **BLOCKED** (gate `83646d78`)
- No further Q2 EVAL / retune (k already 0→1; research-consumed)
- No production promote
- CERT=0
- pub/bet HOLD
- No 2024–25 access
- No S1 revive (kill `50f57195`)
- No merge of draft #679
- No model math / feature change on the live sim

---

## 5. EPA secondary note

Q2 keep: **SKIPPED/UNAVAILABLE** (FROZEN md; no `6ee24b44` on prior VM).  
This VM: NFL PBP parquets / `6ee24b44` **MISSING**. Mapping `b41f4b43` = **EXISTING BUT UNVERIFIED**.  
Live packaged EPA is a **different** path (IF team indices), not a license to run Q2 EPA secondary.  
**Do not revive S1.**

---

## 6. Single recommended next OWNER-or-CoS action

**CoS ACCEPT this RO map under standing RO authority. Do not EXEC.**

If a follow-on is wanted, the next OWNER ask is **CLEAR or refuse a paper-only Q2→IF sidecar field contract** (`Q2AsOfSidecar` in §2c) — no caller wiring, no second EVAL look, no Stage C, no `1ee90fac` scored reuse.

Until that CLEAR: Q2 keep stays research-consumed on draft #679; IF stays the CLEAR-A labeled path with EPA indices and no Massey input.

---

## 7. Citations (required)

keep `03a4dd90` · FROZEN `28c582a1` · EVAL `fe90f5f0` · Alex RO `d12898a2` · erratum `06849c65` · gate `83646d78` · COMPONENTS_Q2PB · fit `70db070d` · config `aa2b47b3` · as-of `cf514078` · IF pin `6ca03716` · contract `b41f4b43` · S1 kill `50f57195` · delegation `97925eb5` · CLEAR-A `1b39f4e9` · games `4fe1cdd7` · outcomes `50bda875` · EXEC commit `af6be4f5` · live tip `f5e3bb58`.
