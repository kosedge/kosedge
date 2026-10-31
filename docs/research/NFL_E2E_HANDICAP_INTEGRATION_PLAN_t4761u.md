# NFL E2E handicap integration PLAN (paper / read-only)

**Status:** PAPER / READ-ONLY · DRAFT only · **not** an implementation · **not** a merge-ready behavior PR  
**Ticket:** t4761u · **Authority:** DECISION `50d1f096` · COS_ORDER Cursor E2E PLAN  
**Tip inventoried:** `deploy-vercel` @ `1b39f4e9f6b2e04c264a41831f3bb7273e475011` (merged #657 CLEAR-A)  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF · no capture · no deploy · no credentials · no paid Odds · no uncertified publish · no experiment execute  
**Do not restart:** EPA-trail · `FAMILY_S1_LOOKS`

This packet is the Cursor ENGINEERING deliverable for Goal A **prep**: inventory + smallest end-to-end integration **plan**. Implementation awaits a separate scoped CLEAR. Goal B (certified forecasting) is out of scope.

---

## 0. Paper provenance (do not invent architecture)

| ID | What it is | Where it lives on this tip | How this plan uses it |
|----|------------|----------------------------|------------------------|
| DECISION `50d1f096` | Owner sprint: Goal A shadow pipeline vs Goal B cert | Attached to this run (not in-repo) | Authority for paper/RO prep only |
| HL blueprint **PASS_PAPER `a31035eb`** | IMV-passed Handicap Layer integration blueprint | **Not in this checkout.** Linear KOS-29/32 (2026-10-30) cite Alex blueprint ACTIVE t4730u CLEAR `4c1bc2c3`, paper CLOSED `e4554211`. Body not on `deploy-vercel`, not in `docs/`, not in open PRs searchable here. | Cited as design authority. **This plan does not reconstruct a new architecture from that missing body.** |
| Paper **`243a384e`** + Spec 2 **`908b21b4`** | In-repo encoding of L0 / L1 / L4 + IF/HF/MIF coexistence | `nfl_handicap_ledger/{__init__,schema,ddl_clear_a}.py/.sql` + CLEAR-A tests | **Working architecture SoT for this packet** |
| IMV PASS_CONTROLS `a9d44516` · DECISION `39fe2d9d` | CLEAR-A controls (IF de-blend + append-only ledger) | `docs/ops/NFL_HANDICAP_CLEAR_A_*.md` + #657 | Preserve Independent Fair separately from market blend |
| H-IFT-1 paper `0dec0d84` | Alex hypothesis (IMV in flight under DECISION `752691fb`) | **Not in this checkout.** Cursor must not execute it. | Parallel lane only. Do not fold into this plan. |
| #657 merge `1b39f4e9` / CLEAR-A `a4b88ae8` (COS) | Independent Fair path + JSONL ledger | Merged on tip | Existing controls this plan wires **around**, not around |

**Architecture already locked in-repo (paper `243a384e` / Spec 2 `908b21b4` / CLEAR-A):**

```
verified inputs
    → raw Independent Fair (L0, forecast_label=independent_fair, market_blend exact 0)
    → handicap adjustments as HandicapDelta[] (L1, forecast_label=handicap_delta)
    → handicapped_fair is a *separate forecast identity* (label exists; no layer writer yet)
    → distribution / simulation (same Monte Carlo; IF does not shift draws)
    → market comparison as Market Informed Fair (L4, forecast_label=market_informed_fair)
    → append-only research ledger (IF / HF / MIF never overwrite)

L5 never reads MIF as fair.
Three forecasts never overwrite each other.
Default / flag-OFF production path stays the historical blended forecast.
```

No new layers, no new forecast labels, no env kill-switch that can silently replace live outputs (`NFL_INDEPENDENT_FAIR_PATH = False` is documentation only; `simulate_nfl_game` does not read it).

---

## 1. Exact code paths by slice stage

### 1.1 Verified inputs

There is **no** single `build_nfl_game_inputs()`. Production assembly is `tasks.run_nfl_market_simulations` (mirror: `routes/nfl` ad-hoc sim). Contract object: `NflGameInputs` in `services/model-service/src/services/nfl_simulator.py`.

| Input | Source of truth on tip | Entry |
|-------|------------------------|-------|
| Schedule / game row | `games` + `seasons` + `teams`; ESPN helper `nfl_data.fetch_nfl_schedule` | `tasks.pull_nfl_context_snapshot` → `games` / `nfl_game_context` |
| Power / EPA | Packaged JSON via `load_packaged_epa_priors` when `prefer_packaged_epa=True` (default remat). DB rolling blend `_load_team_strength_priors` only when not packaged-only. | `nfl_epa_authority.resolve_adhoc_simulation_strength` refuses ESPN W-L persist |
| Matchup / EPA features | `nfl_dp_matchup_features_weekly` | `nfl_matchup_features.fetch_latest_matchup_feature_pack` → `matchup_pack_to_sim_input_kwargs` |
| Roster / depth / injury nowcast | `nfl_dp_injuries` + continuity | `nfl_injury_nowcast.fetch_nfl_injury_nowcast` — **stripped when overlays_off** (default) |
| Rest | `nfl_game_context.rest_days_*` or heuristic | `nfl_data.rest_days_from_schedule` |
| Weather / travel | `nfl_game_context.context.environment` or fallback | `nfl_environment.build_nfl_environment_context` |
| KAV / second-order / personnel / coach / info velocity | Matchup pack + `nfl_second_order_factors` | Passed only when **not** `overlays_off` |
| Market lines (blend input, not IF) | `odds_snapshots` | `tasks._fetch_nfl_market_consensus_lines`; live fallback `_fetch_live_nfl_market_lines_by_abbr` |
| Totals calibration | Historical projections | `fetch_nfl_totals_calibration` |
| Local research fixtures | Packaged EPA + W1/W2 slates | `nfl_epa_authority.NFL_2026_W1_OUTCOMES`, `NFL_2026_W2_SLATE`, `rematerialize_week_epa_overlays_off`; reopening packet `data/ops/nfl-reopening-packet-20260916/` |
| CLEAR-A deterministic fixture | In-test only | `tests/test_nfl_handicap_clear_a_d3.py` `_d3_inputs()` — CLE vs BAL, week 8, seed `47401`, 800 sims |

**Fail-closed remat defaults** (`tasks.run_nfl_market_simulations`, `POST /api/jobs/run-nfl-simulations`): `force_overlays_off=True`, `prefer_packaged_epa=True`, `unlock_overlays=False`. Gate: `nfl_epa_authority.overlays_must_stay_off`.

**Shadow implication:** a Goal A run that needs injury / personnel / KAV / coach factors as *handicap deltas* cannot use the default remat path as-is. Those fields are nulled when overlays stay off. CLEAR-A tests already demonstrate L1 rows with `missing=True` (honest empty, no impute).

### 1.2 Raw fair (Independent Fair)

| Symbol | File | Role |
|--------|------|------|
| `NflGameInputs` | `nfl_simulator.py` | Input contract |
| `compute_nfl_projection_decomposition` | `nfl_handicapping_framework.py` | Point-space margin/total **before** MC (shared by IF and blend) |
| `simulate_nfl_game(..., independent_fair=True)` | `nfl_simulator.py` | Opt-in IF: no draw shift; records `if_margin_mu` / `if_total_mu` **before** sort and **before** linear totals calibration on `markets.total_mean` |
| `simulate_nfl_game_independent_fair` | `nfl_simulator.py` | Explicit entrypoint; fail-closed label + `market_blend == 0` |
| `independent_fair_mus` | `nfl_simulator.py` | Extract `(margin_mu, total_mu)` from labeled block |
| `INDEPENDENT_FAIR_FORECAST_LABEL` / `NFL_INDEPENDENT_FAIR_PATH` | `nfl_simulator.py` | Label `"independent_fair"`; path constant **False** and unread by sim |
| `pre_blend_model_markets_from_diagnostics` | `nfl_model_handicap.py` | Research Model from `diagnostics.market_blend.pre_blend_*` on a **blended** (or IF-with-zero-weight) projection |
| `validate_l0_row` / `append_layer(..., layer=L0)` | `nfl_handicap_ledger/validate.py`, `store.py` | L0 ledger write (tests only today) |

**IF vs default (do not conflate):**

| | Default `simulate_nfl_game` | Independent Fair |
|--|-----------------------------|------------------|
| Market blend | Shifts every margin/total draw toward `market_spread_home` / `market_total` (`NFL_MARKET_BLEND_*` + weeks 1–4 boost) | No shifts; weights 0 |
| Output keys | No `forecast_label`, no `independent_fair` | Both present |
| `markets.*` | Post-blend + linear totals calibration | Same pipeline (draws unmoved; **totals cal still applies** to `markets.total_mean`) |
| Live callers | `tasks.py` ~4967, `routes/nfl.py` ~4893 | **None** |

D3(i) pin: IF mus match `pre_blend_model_markets_from_diagnostics` within 0.01 pt. Residual R1/F8 (NON_BLOCKING): oracle does not lock `if_out["markets"]` or weeks 1–4 disagreement boost.

**L0 required fields** (`schema.L0_REQUIRED_FIELDS`, paper `243a384e`): `game_id`, `model_version`, `as_of_ts`, `capture_id`, `baseline_personnel_ref`, `off_eff_h/a`, `def_eff_h/a`, `pace_h/a`, `margin_mu`, `total_mu`, `sigma`, `market_blend` (exact 0). Missing ⇒ REJECT, never impute.

**Gap:** no `sim → L0` helper. IF block has mus/sigma; it does **not** emit `baseline_personnel_ref` / `off_eff_*` / `pace_*`. Those are filled only in test literals.

### 1.3 Handicap adjustments

Two existing systems. **Do not merge them.** CLEAR-A L1 is the research ledger; the live product "handicap" is mostly post-blend KEI naming.

**A. Research L1 (blueprint, not wired)**

| Symbol | File | Role |
|--------|------|------|
| `L1_ENTRY_POINTS` | `nfl_handicap_ledger/schema.py` | Frozen: `{efficiency, possessions, variance, shape, points}` |
| `validate_l1_row` / `commit_l1_stage` | `validate.py` | Fail-closed; atomic; `forecast_label` **must** be `handicap_delta` (HF smear forbidden) |
| L1 required fields | `schema.py` | `capture_id`, `as_of_ts`, `baseline_ref`, `registry_id`, `source_snapshot_id`, `factor`, `entry_point`, `delta`, `uncertainty` |

**B. Live factor decomposition (already runs inside every sim, including IF)**

`compute_nfl_projection_decomposition` writes `diagnostics.framework.factor_contributions` with existing keys (not L1 `entry_point` names):

| Framework key | Default | Env |
|---------------|---------|-----|
| `base_efficiency` | ON | (core) |
| `home_field_advantage` | ON | |
| `rest_travel` / `travel_schedule` | ON | `NFL_FRAMEWORK_TRAVEL_ENABLED` |
| `weather_environment` | ON | `NFL_FRAMEWORK_WEATHER_ENABLED` |
| `travel_weather_interaction` | ON | `NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED` |
| `kav_efficiency` | ON in config | `NFL_FRAMEWORK_KAV_ENABLED` — **nulled on overlays_off remat** |
| `injuries_depth` | ON when nowcast non-null | **nulled on overlays_off remat** |
| `error_regime` | ON (σ widen) | `NFL_FRAMEWORK_ERROR_REGIME_ENABLED` |
| `personnel_efficiency` | OFF | `NFL_FRAMEWORK_PERSONNEL_ENABLED` |
| `coach_aggression` | OFF | `NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED` |
| `info_velocity` | OFF | `NFL_FRAMEWORK_INFO_VELOCITY_ENABLED` |
| `external_dvoa` | OFF | `NFL_FRAMEWORK_EXTERNAL_DVOA_ENABLED` |
| `situational_flags` / `regression_luck` | present | |

**C. Product KEI / "handicap_*" (not the research ledger)**

| Symbol | File | Live? |
|--------|------|-------|
| `annotate_projection_model_handicap` / `resolve_model_and_handicap` | `nfl_model_handicap.py` | Live on remat + fair-lines read. `model_*` = pre-blend research; `handicap_*` = published post-blend |
| `apply_week1_kei_reprice_for_published_fair` | `nfl_kei_week1_reprice.py` | Live **identity**. `WEEK1_KEI_PUBLISH_MUTATE_FAIR = False` |
| `apply_kei_reprice_to_projection` / `run_injury_kei_window` | `nfl_injury_kei_cadence.py` | Library + `scripts/nfl/injury_kei_reprice.py` only. Not Celery. |

**Mapping decision (NOT made here):** L1 `entry_point` ∈ {efficiency, possessions, variance, shape, points} vs framework keys above. Existing test fixture uses `factor="injury_availability"` / `"weather"` with `entry_point="points"`. A CLEAR must approve a **registry** (`registry_id`) that maps framework keys → L1 `(factor, entry_point)` without inventing new entry points. Until then, honest L1 is `missing=True` + `delta=0.0` (already proven).

**HF (`handicapped_fair`):** label + DDL CHECK exist. **No layer accepts it.** L1 explicitly rejects HF. `test_if_hf_mif_coexist_without_overwrite` writes L0 + L1 + L4, not an HF row. Do **not** mint L2/L3 in this plan. HF remains a derived view (IF mus + sum of committed L1 deltas) until a scoped CLEAR names the writer.

### 1.4 Distribution / simulation

Same function for IF and blend: `simulate_nfl_game`.

| Output | Where | Notes |
|--------|-------|-------|
| Monte Carlo scores | gauss around `mean_home` / `mean_away` from decomposition | `simulations` default 4000; D3 pin uses 800 |
| `markets.home_win_prob` / `away_win_prob` | post-draw (and post-blend if default) | |
| `markets.spread_home` / `total_mean` | post-blend (default) or unshifted (IF) | IF `markets.total_mean` still gets linear totals calibration |
| `markets.total_p10/p50/p90` | quantile + cal delta | |
| `markets.fair_home_ml` / `fair_away_ml` | `_fair_moneyline_from_prob` | Win probs are post-blend on default path → Model ML = KEI unless a later handicap-role reprice |
| `independent_fair.margin_mu/total_mu/sigma` | IF only | σ = sim `stdev`, not a fitted residual |
| `diagnostics.framework.factor_contributions` | both | Attribution for Goal A item 3, not yet ledger-copied |

**Valid-distribution check already available:** finite mus, `sigma > 0`, p10 ≤ p50 ≤ p90, win probs in (0,1) and sum ~1. Not packaged as a Goal A harness.

### 1.5 Market comparison

| Stage | File:function | Shadow-safe? |
|-------|---------------|--------------|
| Odds HTTP | `odds_api.fetch_odds` (`ODDS_API_KEY` / `_BACKUP`) | **No** — paid; locked this sprint |
| Scheduled persist | `tasks.pull_odds_snapshot` → `odds_snapshots` | Needs Railway beat + key. C10 HOLD |
| Remat blend input | `tasks._fetch_nfl_market_consensus_lines` | Needs DB snapshots or live fetch |
| Fair-lines assemble / edge | `routes/nfl._nfl_fair_lines_impl` (`spread_edge`, `total_edge`, `ml_edge_prob`) | Customer GET `persist=0`; still needs a book print |
| Stake close | `nfl_market_close.stake_close_spread` | Warehouse / snapshot |
| Publish tags | `nfl_side_total_publish_policy.nfl_publish_tag` | `NFL_PRODUCT_GATE_STATUS` default YELLOW; public paint still Coming Soon |
| Historical close research | `nfl_warehouse/odds_lake.py` | Partial; `docs/ODDS_DATA_INFRA.md` documents open→close DATA GAP |
| L4 MIF validator | `validate_l4_row` | Schema only. Required: `market_snapshot_id`, `captured_at`, `forecast_label`, `as_of_ts`, `capture_id`, `game_id` |
| D3/L4 test payload extras | `blend_weight_spread/total`, `week_scale` | Comparison metadata, **not** a second fair |

CLEAR-A control: L4 is `market_informed_fair`. L5 (not implemented) **never reads MIF as fair**. Market comparison for Goal A must write L4 (or a side-by-side JSON) **without** feeding MIF back into IF or L1.

**Pinned local market (already in CLEAR-A tests, no Odds):**

```
D3II_MARKET_SPREAD_HOME = 3.5
D3II_MARKET_TOTAL = 43.5
```

That is enough for a one-game shadow compare. It is **not** a slate.

### 1.6 Internal research ledger

| Symbol | File | Role |
|--------|------|------|
| `LEDGER_SCHEMA_VERSION` | `schema.py` | `"handicap-ledger-v0-clear-a"` |
| `HandicapLedgerEnvelope` | `schema.py` | Append-only envelope |
| `business_identity_key` / `make_prediction_id` | `identity.py` | Identity = `(layer, forecast_label, game_id, as_of_ts, capture_id, schema_version)`; payload ignored; `hl_{32 hex}` |
| `canonicalize_as_of_ts` / `parse_ledger_ts` | `identity.py` | UTC, microseconds stripped, Z suffix; naive rejected |
| `AppendOnlyHandicapLedger` | `store.py` | In-memory + optional JSONL; load re-validates; never overwrite |
| `commit_l1_stage` | `validate.py` | Atomic L1 only. **No** `commit_l0_stage` / `commit_l4_stage` |
| `reject_top_level_payload_conflicts` | `validate.py` | R7: no top-level vs payload precedence |
| `reject_contaminated_market_blend` | `validate.py` | Any present `market_blend` must be exact 0 |
| `ddl_clear_a.sql` | same package | DEVELOPMENT_ONLY. **Do not apply.** F10 residual: REVOKE FROM PUBLIC ≠ owner lock |

**Live callers of `nfl_handicap_ledger`:** tests only. Package banner: not wired to capture, overlays, scoring, migrate, or production.

### 1.7 Publication control (Goal A item 8 — already closed)

| Constant | File | Value |
|----------|------|-------|
| `NFL_EDGE_BOARD_PUBLIC_ENABLED` | `apps/web/lib/cfb-edge-board-public.ts` | `false` |
| `NFL_FAIR_LINES_PUBLIC_{SPREAD,ML,TOTAL}_ENABLED` | same | `false` |
| `NFL_FAIR_LINES_PLAY_ENABLED` / `KELLY_ENABLED` | same | `false` |
| `NFL_FAIR_LINES_CERTIFIED_RUN_ID` / `SHA256` / `AT` | same | `null` (CERT=0) |
| `FOOTBALL_PUBLIC_NUMBERS_HEADING` | same | `"Coming soon"` |
| Internal QA only | `NFL_EDGE_BOARD_INTERNAL=1` | not a CLEAR |

A shadow E2E must not flip these. Internal research stays off the customer paint.

---

## 2. Dependencies

### 2.1 Data pins (local, no network)

| Pin | Value | Used by |
|-----|-------|---------|
| D3(ii) blended SHA256 | `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` | `test_nfl_handicap_clear_a_d3.py` — prod path byte-identical |
| D3 fixture | CLE@BAL, `game_id=d3ii-clear-a-baseline`, week 8, seed `47401`, 800 sims, mkt 3.5 / 43.5 | IF + blend compare |
| Ledger schema | `handicap-ledger-v0-clear-a` | All CLEAR-A tests |
| Model version string | `nfl-v1.5-matchup-sim` (`DEFAULT_NFL_MODEL_VERSION`) | IF + L0 tests |
| Reopening candidate (historical, not this slice) | SHA `153b6a884a8e` packaged EPA overlays OFF | `data/ops/nfl-reopening-packet-20260916/` — do not retune |
| War-room Fair Lines practice SHA | `b5ee9d80…` REJECTED_NO_CLEAR | Must not bind CERT |

### 2.2 Env (read, do not set for this plan)

| Knob | Default | Shadow note |
|------|---------|-------------|
| `force_overlays_off` / `unlock_overlays` | True / False | Remat strips handicap-class inputs |
| `NFL_MARKET_BLEND_SPREAD_WEIGHT` / `TOTAL_WEIGHT` | 0.30 | Default path only; IF forces 0 |
| `NFL_EARLY_SEASON_MARKET_BLEND_BOOST_W{1-4}` | 0.25…0.10 | Default path only |
| `NFL_FRAMEWORK_*_ENABLED` | see §1.3 | Personnel/coach/info_velocity/DVOA already false |
| `NFL_INDEPENDENT_FAIR_PATH` | constant False | **Must stay unread** |
| `NFL_PRODUCT_GATE_STATUS` | YELLOW | Tags only; public still dark |
| `NFL_WEEKLY_PROPS_LIVE` | true (web) | **Different spine.** Do not touch. |
| `DATABASE_URL` | required by many imports | CLEAR-A tests set a dummy DSN; they do not hit Postgres |
| `ODDS_API_KEY` / `_BACKUP` | unpaid / locked | Do not configure |

### 2.3 C10 / Railway

`.github/workflows/deploy-railway.yml` is **workflow_dispatch + `confirm_c10_clear=CLEAR`** only (G4 / #656 `209e90aa`). Bare push of `services/model-service/**` must not `railway up` api/worker/beat. Goal A does **not** need Railway. Do not request C10 restore.

### 2.4 Odds

Paid Odds is locked. Historical nflverse closes exist for old backtests (`scripts/nfl/historical_market_backtest.py`) — that is a **blend-tuning** script, not this slice, and must not be re-run as an experiment. Shadow market compare = pinned fixture numbers or already-on-disk `odds_snapshots` / warehouse files. `odds_mode=reuse` on fair-lines GET does not persist.

### 2.5 Local-only runtime

| Works offline | Needs |
|---------------|-------|
| CLEAR-A pytest (26) | Python 3 + `services/model-service` on `PYTHONPATH`; dummy `DATABASE_URL` |
| `simulate_nfl_game_independent_fair` on `_d3_inputs()` | same |
| Framework decomposition on a constructed `NflGameInputs` | same |
| JSONL `AppendOnlyHandicapLedger` | tmp path |
| Coming Soon constants | repo read |
| Packaged-EPA remat helpers | local JSON priors; **not** required for the one-game D3 slice |

| Blocked | Why |
|---------|-----|
| Live remat slate | Postgres + (usually) `odds_snapshots` |
| Live Odds | paid key + policy |
| Railway worker / beat | C10 HOLD |
| Capture / `nfl_dp_*` refresh | no capture; W8 consume-proof already accepted elsewhere — do not reopen |
| DDL apply | F10 residual; DEVELOPMENT_ONLY |
| Public Fair Lines / Edge Board | CERT=0 · Coming Soon ON |
| H-IFT-1 execute | Alex/IMV lane; no experiment CLEAR |
| EPA-trail / `FAMILY_S1_LOOKS` | explicitly stopped |

---

## 3. Missing pieces vs Goal A tonight

Goal A checklist (DECISION `50d1f096`) scored against **this tip**, not against a future CLEAR.

| # | Goal A item | Status on `1b39f4e9` | Missing for a *working* shadow pipeline |
|---|-------------|----------------------|------------------------------------------|
| 1 | Reproducible run | **Partial.** D3 fixture + 26 tests are deterministic. No one-command orchestrator that walks the full slice and writes a receipt. | Local orchestrator script (proposed P1). Must not call live remat/Odds. |
| 2 | Raw + adjusted fair preserved | **Partial.** IF labeled and de-blended. Prod blend pinned. `model_*` vs `handicap_*` exist on the product path. HF **row** does not exist (no layer). | Decide: HF as derived view from L0+L1 (no new layer) **or** wait for blueprint-named writer. Do not invent L2. |
| 3 | Handicap attribution | **Partial.** `factor_contributions` on every sim. L1 schema + `commit_l1_stage` exist. No sim→L1 copy. No approved `registry_id` map. | Registry CLEAR + copier (P2). Until then, L1 `missing=True` is the honest write. |
| 4 | Valid distributions | **Partial.** MC + bands exist. No Goal A assertion harness (finite mus, quantile order, σ>0, IF mus vs `markets` residual documented). | Small assertion helper in the orchestrator tests (P1b). |
| 5 | Market comparison | **Partial.** Default blend + fair-lines edge exist (prod/Odds). L4 validator exists. No IF-vs-pinned-market writer. | Pinned-market L4 append (P3). **Never** feed L4 back into IF. |
| 6 | Fail-closed | **Met for ledger validators** (R7, N1–N4, D1–D4). Prod path fail-closed on overlays and Coming Soon. Orchestrator does not exist to inherit those rejects. | Orchestrator must call existing validators; no new precedence rules. |
| 7 | Hypothesis IMV grade | **Not this lane.** H-IFT-1 `0dec0d84` is Alex → IMV. | Cursor: do not grade, do not execute. |
| 8 | Publication control | **Met.** Coming Soon ON, CERT unbound, PLAY/Kelly off. | Do not touch `cfb-edge-board-public.ts`. |

**Honest tonight bar without a new CLEAR:** the *controls* for Goal A (IF de-blend, ledger rejects, Coming Soon) are on tip. The *pipeline* (one fixture → L0 → L1 → compare → L4 JSONL → receipt) is **not** assembled. That assembly is the smallest scoped CLEAR, not tonight's paper.

**Out of Goal A (do not sneak in):** HF layer mint, DDL/Postgres store, capture_id from a real capture service, overlays ON, C10, paid Odds, public paint, EPA-trail, FAMILY_S1_LOOKS, H-IFT-1 execute, player-props spine.

---

## 4. Proposed patch plan (smallest bounded commits) — NOT implemented

All commits below are **proposals**. None are in this PR. Each needs a scoped CLEAR. Default production callers stay on `simulate_nfl_game` without `independent_fair`.

### P0 — already merged (do not redo)

#657 `1b39f4e9`: IF path + append-only JSONL ledger + 26 tests. Preserve D3(ii) SHA `75ee2ee9…`.

### P1 — local shadow orchestrator (needs CLEAR) — smallest Goal A slice

**One commit.** New **script + tests only**. No `tasks.py` / `routes/nfl.py` / web / Celery / env flag.

Proposed (names illustrative, not created):

- `scripts/nfl/shadow_handicap_e2e_t4761u.py`
- `services/model-service/tests/test_nfl_shadow_handicap_e2e_t4761u.py`

Behavior (all local):

1. Load `_d3_inputs()` (or a JSON clone of that fixture under `data/ops/` — **do not expand the slate**).
2. Call `simulate_nfl_game_independent_fair` with D3 kwargs (seed 47401, 800 sims, pinned 3.5 / 43.5).
3. Call `simulate_nfl_game` (default) on the same inputs; assert D3(ii) SHA unchanged.
4. Map IF mus/sigma → L0 row. For `off_eff_*` / `def_eff_*` / `pace_*` / `baseline_personnel_ref`: use **explicit fixture constants** (same as D3 coexistence test: 1.0 / `baseline-personnel-ref-dev`) **or** fail-closed if a later CLEAR names the real mapping. Do not impute from missing sim fields.
5. `AppendOnlyHandicapLedger(path).append_layer(..., L0, independent_fair)`.
6. Write L1 as `missing=True` / `delta=0.0` / `entry_point="points"` for a **frozen allow-list of factor names already used in tests** (`injury_availability`, `weather`) via `commit_l1_stage`. No new factors.
7. Write L4 with `market_snapshot_id="pin-d3ii-3.5-43.5"`, `captured_at` ≤ `decision_ts`, pinned market numbers in payload. `forecast_label=market_informed_fair`.
8. Emit a JSON receipt: IF mus, blended SHA, L0/L1/L4 `prediction_id`s, `market_blend==0`, Coming Soon constants unread/unflipped.
9. Refuse: `ODDS_API_KEY`, `DATABASE_URL` writes, Railway, `unlock_overlays`, any `forecast_label=handicapped_fair` row.

**Acceptance:** one command, exit 0, JSONL has exactly 1 L0 + N L1 + 1 L4, three distinct `prediction_id`s, D3(ii) SHA still green.

### P1b — distribution assertions (same CLEAR as P1 or a 5-line follow-up)

Assert on the IF result: mus finite, `sigma > 0`, `total_p10 ≤ total_p50 ≤ total_p90`, win probs in (0, 1), IF `market_blend` exact 0. Document R1/F8: `markets.total_mean` may differ from `independent_fair.total_mu` because linear totals calibration still runs.

### P2 — L1 attribution copy (needs **separate** CLEAR + registry)

Only after CoS/Ryan name a `registry_id` that maps **existing** `factor_contributions` keys → L1 `(factor, entry_point)` using the frozen five entry points. Copier reads `diagnostics.framework.factor_contributions`; writes `delta` from `margin_points` (or the named component); still `missing=True` when overlays_off nulled the input. **No new factors. No overlays ON.**

### P3 — HF derived view (optional, needs CLEAR)

If Goal A item 2 is judged to require a stored HF: **do not add a layer**. Options that stay inside Spec 2:

- **Preferred:** receipt-only derived view `hf_margin_mu = if_margin_mu + sum(L1.delta where entry_point=points)` (and analog for total if a total-delta convention is named). Not a ledger row.
- **Only if blueprint `a31035eb` (when deposited) names a writer:** a later commit may append `forecast_label=handicapped_fair` once a layer is specified. That layer is **not** L1. Do not guess L2.

### P4 — explicitly out of this sprint

Live remat hook, Postgres DDL, capture pipeline, `NFL_INDEPENDENT_FAIR_PATH` env, overlays unlock, C10, paid Odds, Coming Soon OFF, CERT bind, EPA-trail, FAMILY_S1_LOOKS, H-IFT-1 execute.

### Suggested CLEAR text (for CoS → Ryan)

> CLEAR-P1 only: local D3-fixture orchestrator + tests that write IF L0 / missing L1 / pinned L4 JSONL and assert D3(ii) SHA + Coming Soon untouched. No live callers. No HF layer. No DDL. No Odds. No Railway. No overlays. Implementation of P2/P3 remains blocked.

---

## 5. Deterministic tests + acceptance evidence checklist

### 5.1 Already green on tip (must stay green)

```bash
cd services/model-service
python3 -m pytest \
  tests/test_nfl_handicap_clear_a_d3.py \
  tests/test_nfl_handicap_clear_a_d1_d4_remotion.py \
  tests/test_nfl_handicap_clear_a_n1_n4_remotion.py \
  tests/test_nfl_handicap_clear_a_r7.py -q
# expect: 26 passed
```

| Evidence | Pin / proof |
|----------|-------------|
| IF mus ≈ pre-blend helper | D3(i) ±0.01 |
| Default path unchanged | D3(ii) SHA `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` |
| L1 missing field / future as_of | D3(iii) REJECT, store empty |
| L1 append-only | D3(iii) never overwrite |
| IF / L1 / L4 coexist | `test_if_hf_mif_coexist_without_overwrite` (3 ids) |
| Exact blend=0 | D1 F1; bool rejected |
| Identity ignores payload | D1 F4 |
| Naive timestamps | D1 F5 |
| No impute | D1 F6 |
| L1 ≠ HF; L4 = MIF | D1 F9 |
| `commit_l1_stage` atomic | D1 F13 |
| N1–N4 | remotion file |
| R7 top vs payload | `test_nfl_handicap_clear_a_r7.py` (6) |
| `NFL_INDEPENDENT_FAIR_PATH is False` | D3(i)(ii) |

### 5.2 Proposed after P1 CLEAR (not written)

- Orchestrator dry-run on D3 fixture → receipt JSON + JSONL.
- Byte-compare blended output to D3(ii) SHA in the **same process** as the IF run.
- Ledger load of the written JSONL re-validates (R7 clean).
- Attempted L0 with `market_blend=0.3` REJECT.
- Attempted L1 with `forecast_label=handicapped_fair` REJECT.
- Attempted L4 with empty `market_snapshot_id` REJECT.
- Grep/assert: no `ODDS_API_KEY` read, no `unlock_overlays=True`, no edits under `apps/web/lib/cfb-edge-board-public.ts`.
- `git diff origin/deploy-vercel -- apps/web` empty for P1.

### 5.3 Goal A acceptance evidence (what CoS should demand before claiming A)

1. Command + SHA of the orchestrator commit + fixture pins.
2. Receipt showing IF `market_blend=0` and mus.
3. Receipt showing L1 rows (even if `missing=True`) with `prediction_id`s.
4. Quantile / σ checks.
5. L4 vs pinned 3.5 / 43.5 (delta recorded; **not** used as fair).
6. Pytest 26 + new P1 tests.
7. H-IFT-1 IMV grade **from IMV**, not Cursor.
8. Screenshot or constant dump: Coming Soon ON, CERT ids null.

Items 1–6 and 8 are engineering. Item 7 is a different queue.

---

## 6. What can run fully offline vs blocked

### 6.1 Fully offline / local now (no CLEAR, no network)

| Action | How |
|--------|-----|
| Prove IF ≠ blend | `pytest` D3(i)(ii) |
| Prove ledger fail-closed | D1–D4 + N1–N4 + R7 |
| Hand-walk IF on D3 fixture | `simulate_nfl_game_independent_fair(_d3_inputs(), seed=47401, simulations=800, market_spread_home=3.5, market_total=43.5)` |
| Read Coming Soon / CERT=0 | `cfb-edge-board-public.ts` |
| Read architecture | this file + `nfl_handicap_ledger/schema.py` |

### 6.2 Offline after P1 CLEAR (still no Railway / Odds / prod)

One-game shadow: verified **fixture** inputs → IF → L0 JSONL → missing L1 → pinned-market L4 → receipt. That is the minimum Goal A *engineering* slice.

### 6.3 Blocked (do not attempt)

| Block | Lock |
|-------|------|
| C10 / Railway api/worker/beat restore | C10 HOLD · G4 |
| Paid Odds pull | sprint lock |
| Prod remat / beat | C10 + overlays OFF + no live caller wiring |
| Capture IDs from a real capture service | no capture |
| Postgres ledger | F10 / no `infra/db` apply |
| Overlays ON / injury nowcast volume | `overlays_must_stay_off` |
| Public numbers / PLAY | CERT=0 · Coming Soon ON · F2 frozen |
| EPA-trail / FAMILY_S1_LOOKS | owner stop |
| H-IFT-1 experiment execute | needs IMV disposition + separate CLEAR |
| Expanding L1 factors beyond test allow-list | no registry CLEAR |

### 6.4 Hybrid (exists, but not this slice)

`scripts/nfl/nfl_reopening_packet_20260916.py`, `evaluate_enterprise_gates.py`, `historical_market_backtest.py`, `full_pipeline_holdout_backtest.py` — older research. Do not revive as the Goal A orchestrator. They predate CLEAR-A labels and can drift IF vs blend.

---

## 7. Risks / residuals (do not expand)

| ID | Residual | Plan stance |
|----|----------|-------------|
| R1/F8 | D3(i) oracle vs `markets` / early-season boost | Document only |
| R2/F10 | DDL owner lock | Do not apply SQL |
| R7 | Closed on JSONL load | Keep tests |
| R8 | as_of second-grain vs timestamptz µs | `canonicalize_as_of_ts` strips µs; do not reopen |
| Paper `a31035eb` body absent | Cannot quote unseen sections | If CoS deposits the file, **amend this plan** rather than guess |
| HF layer unspecified | Label without writer | Derived view only |
| L0 efficiency/pace fields | Not produced by sim | Fixture constants or REJECT |
| `capture_id` | No capture service | Synthetic `cap-d3ii-t4761u` in P1 only; never a prod capture |

---

## 8. What this packet is not

- Not an implementation.
- Not a merge-ready behavior change.
- Not a C10 restore, Odds buy, Railway bounce, or Coming Soon flip.
- Not a restart of EPA-trail or FAMILY_S1_LOOKS.
- Not an H-IFT-1 grade or execute.
- Not a new architecture.
- Not Goal B / CERT.

Success for this run: **plan packet ready for CoS → Ryan scoped CLEAR** (recommended: CLEAR-P1 only).

---

## RECEIPT

| Field | Value |
|-------|-------|
| Ticket | t4761u |
| DECISION | `50d1f096` |
| Plan doc | `docs/research/NFL_E2E_HANDICAP_INTEGRATION_PLAN_t4761u.md` |
| Plan sha256 | see PR RECEIPT (`sha256sum` of this file at commit) |
| Tip inventoried | `1b39f4e9f6b2e04c264a41831f3bb7273e475011` |
| Architecture SoT used | paper `243a384e` + Spec 2 `908b21b4` as encoded on tip; PASS_PAPER `a31035eb` cited, body not in checkout |
| Code changed | **none** (this file only) |
| Tests run | none required (paper); CLEAR-A 26 remain the regression bar |
| Next | CoS → Ryan CLEAR-P1 or hold |
