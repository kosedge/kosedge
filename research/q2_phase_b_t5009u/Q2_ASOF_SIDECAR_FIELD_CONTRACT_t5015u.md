# t5015u — `Q2AsOfSidecar` field contract (paper only)

**Label:** DEV_RESEARCH · CERT=0 · NFL NO-GO · pub/bet HOLD  
**Mode:** paper / interfaces only. **Do not merge · do not deploy · do not implement wiring · no EVAL · no retune · no model math/feature change · no Stage C · no scored reuse of hist index `1ee90fac` · no 2024–25 access.**

**Authority:** OWNER t5015u. Keep ACCEPT `03a4dd90` · FROZEN `28c582a1` / fit `70db070d` / config `aa2b47b3` · EVAL one-look `fe90f5f0` · Alex keep RO `d12898a2` · delegation `97925eb5` · as-of rule `cf514078` · CLEAR-A `1b39f4e9` · map draft [#680](https://github.com/kosedge/kosedge/pull/680) `be8c27a6`.  
Alex PASS_RO_MAP on #680: tip `4a1bc064` (coordination; not a git object on this clone). Soft note applied below for `b41f4b43` only — **no map re-review** (Alex owns #680).

**This paper does not ACCEPT keep, does not EXEC wiring, and does not promote CERT.**

**IF in this paper = Independent Fair (CLEAR-A), not injury-factor.** Injury overlays live on `NflGameInputs.injury_nowcast_*` and stay out of Q2 keep / sidecar scope.

---

## 0. Identity

| Item                          | Value                                                                                                                                                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| This paper                    | t5015u · `research/q2_phase_b_t5009u/Q2_ASOF_SIDECAR_FIELD_CONTRACT_t5015u.md`                                                                                                                             |
| Inspected live tip            | `origin/deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f`                                                                                                                                        |
| Q2 keep packet (do not merge) | draft [#679](https://github.com/kosedge/kosedge/pull/679) · `cursor/q2-phase-b-exec-a5ff` @ `af6be4f59c63af222d02c39878266460a37d418a`                                                                     |
| Prior map (do not re-do)      | draft [#680](https://github.com/kosedge/kosedge/pull/680) · `cursor/q2-keep-if-ro-map-53e0` @ `be8c27a6d32d2e1cc676ff269109832faab74a2d` · `research/q2_phase_b_t5009u/RO_IF_DEPENDENCY_MAP_t5014u.md` §2c |
| CLEAR-A IF merge              | `1b39f4e9f6b2e04c264a41831f3bb7273e475011` (#657) — **code is on `deploy-vercel`**                                                                                                                         |
| FROZEN md                     | sha256 prefix `28c582a1` of `ops/nfl_enterprise_green_t4359u/FROZEN_CONFIG_Q2PB_t5009u.md` on #679                                                                                                         |
| Fit / config                  | `70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571` / `aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49`                                                                    |

---

## 1. HARD — three-layer runtime distinction

These three layers are **not interchangeable**. A sentence that says “IF is tests-only” or “IF is prod blended” without naming the layer is a defect. `tests-only` and `prod blended` below are scoped to the layer they sit in.

### Layer 1 — Repository code on `deploy-vercel`

Symbols **present** on inspected live tip `f5e3bb58` via CLEAR-A merge `1b39f4e9` (#657). Presence ≠ production invoke.

| Symbol / path                                          | File:lines (live tip)                                                                                                                                                                                                                             | What it is                                                                                                                                                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `simulate_nfl_game(..., independent_fair=False\|True)` | `services/model-service/src/services/nfl_simulator.py:519–531` (flag), `:611–617` (blend-zero branch), `:847–860` (labeled payload)                                                                                                               | Default path is blended. Opt-in flag attaches `independent_fair{margin_mu,total_mu,sigma,market_blend=0}`.                                                                                                         |
| `simulate_nfl_game_independent_fair`                   | `nfl_simulator.py:877–911`                                                                                                                                                                                                                        | Explicit labeled IF entry. Docstring: “Never the live default. Production callers must keep using `simulate_nfl_game` without this flag.”                                                                          |
| `independent_fair_mus`                                 | `nfl_simulator.py:914–925`                                                                                                                                                                                                                        | Reads labeled IF mus; fail-closed if unlabeled or blend ≠ 0.                                                                                                                                                       |
| `NFL_INDEPENDENT_FAIR_PATH`                            | `nfl_simulator.py:34–39`                                                                                                                                                                                                                          | Constant `False`. **Documentation + opt-in name only** — `simulate_nfl_game` does **not** read an env kill-switch.                                                                                                 |
| `INDEPENDENT_FAIR_FORECAST_LABEL`                      | `nfl_simulator.py:38`                                                                                                                                                                                                                             | `"independent_fair"`                                                                                                                                                                                               |
| EPA priors path                                        | `services/model-service/src/tasks.py:_load_team_strength_priors` `:1051–1080` (`as_of_week` → `week_cap_current`); `_resolve_team_strength_indices` `:1547–1592` (EPA `offense_index` / `defense_index` preferred; W-L record is cold-start only) | Live strength SoT. Not Massey. Not Q2.                                                                                                                                                                             |
| Ledger helpers                                         | `services/model-service/src/services/nfl_handicap_ledger/schema.py` `L0_REQUIRED_FIELDS` `:59–75`; `LEDGER_SCHEMA_VERSION = handicap-ledger-v0-clear-a`; header `:8` **DEVELOPMENT_ONLY — no capture**                                            | Append-only IF/HF/MIF envelope. Residual R1/F8 “oracle strength” still open (`schema.py:11`).                                                                                                                      |
| Layer-1 **test imports** of the labeled IF entry       | `services/model-service/tests/test_nfl_handicap_clear_a_d3.py` (imports `simulate_nfl_game_independent_fair`, `independent_fair_mus`, `NFL_INDEPENDENT_FAIR_PATH`); `test_nfl_handicap_clear_a_d1_d4_remotion.py` (`independent_fair_mus`)        | On **this live tree**, non-definition imports of the labeled IF entry are tests. **This sentence is Layer 1 only.** It does not describe Layer 2 and does not overwrite OWNER/CoS-accepted offline IF caller work. |

`docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` still says “DRAFT PR only · not merged.” That sentence is **stale** for Layer 1: #657 is on `deploy-vercel` as `1b39f4e9`. Stale docs do not move this into Layer 3.

D3(ii) flag-OFF blended hash (Layer 1 test pin, not a sidecar field): `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`.

### Layer 2 — Accepted offline Independent Fair caller

OWNER/CoS-accepted **offline** work that **invokes** the labeled IF entry (or a pinned IF tip) **outside** the live Railway/Vercel subscriber path. This layer is **not** “tests-only.” Do not collapse it into Layer 1 test imports or Layer 3 blended prod.

| Artifact                                     | Status on this inspection                                                                                                                                              | What it is                                                                                                                                                                                                                                                               |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OWNER ACCEPT t4910u bounded diagnostic score | draft [#672](https://github.com/kosedge/kosedge/pull/672) · `data/ops/OWNER_ACCEPT_t4910u_BOUNDED_DIAG_SCORE_70.md` + packet `data/ops/nfl-hist-diag-score-70-t4910u/` | OWNER-accepted offline IF score of 70 complete 2017 REG games. `CALL_AUDIT.md`: original score tip `19c6a460` invoked `simulate_nfl_game_independent_fair` × 70 (sealed). Close tip `02197f58` did **not** re-invoke.                                                    |
| Offline IF caller script                     | `#672` `data/ops/nfl-hist-diag-score-70-t4910u/score_t4910u.py`                                                                                                        | Loads simulator/framework from pinned IF tip `6ca03716fe52930332d5ffba302c312a651980cc` via worktree `/tmp/t4910u-if-6ca03716`. `MARKET_BLEND = 0`, `SIMULATIONS = 4000`. Does **not** import the W8 eval rest helper.                                                   |
| IF tip / simulator pin used by that caller   | tip `6ca03716` · `nfl_simulator.py` sha `52d9e909` · framework `a0051cc4` (packet `ASSUMPTIONS.md` / `CALL_AUDIT.md` / Alex RO on #672)                                | **Not** the `deploy-vercel` HEAD object of `nfl_simulator.py`. Packet is explicit: live HEAD simulator ≠ `52d9e909`.                                                                                                                                                     |
| W8 offline eval caller (distinct)            | cited in OWNER ACCEPT t4910u: tip `6ca03716` W8 eval path; rest_days correction `155d3ca0` / execution `90bf65ab`                                                      | OWNER ACCEPT binds: hist diagnostic scoring may use tip `6ca03716` **only if** sealed reconstructed `rest_days_*` are bound and **never** re-derived via the W8 eval caller. Silent tip substitution forbidden. This is a **second** offline caller family, not Layer 3. |
| CLEAR-P1 local D3 shadow orchestrator        | draft [#662](https://github.com/kosedge/kosedge/pull/662) · `scripts/nfl/shadow_handicap_e2e_t4761u.py`                                                                | Local fixture: D3 CLE vs BAL → `simulate_nfl_game_independent_fair` (`market_blend=0`) → L0/L1/L4 receipt. DRAFT; parent inventoried `1b39f4e9`. Not a production writer.                                                                                                |
| SOURCE ONLY `52d9e909` @ `1b39f4e9`          | cited on draft [#668](https://github.com/kosedge/kosedge/pull/668) (Hist BT Stage-1 recon)                                                                             | Cited, **not invoked** for that recon. Confirms the sealed IF simulator object is a Layer 2 pin, not a Layer 3 caller.                                                                                                                                                   |
| t4921u #4 R1 confirmatory addendum           | draft [#675](https://github.com/kosedge/kosedge/pull/675)                                                                                                              | Sealed IF-only **internal sampling consistency** (`R1_PASS`). Packet label: “IF-only internal sampling consistency. Not calibration, forecast skill, … merge-to-prod, or betting.” Different “R1” from ledger residual R1/F8 oracle strength.                            |
| R1 IF-only ACCEPT `e7b7c567`                 | **cited in OWNER t5015u brief; not located as a git object, file, PR body, Linear issue, Notion page, or Slack message on this clone**                                 | Coordination tip, same class as keep `03a4dd90` / delegation `97925eb5`. **Absence of this git object does not erase Layer 2.** Located OWNER-accepted offline IF invoke remains t4910u / `19c6a460` / `score_t4910u.py` at tip `6ca03716`.                              |

Layer 2 is research/offline. CERT=0. No subscriber forecast. No production promote. Sidecar wiring, if later CLEARED, would be a **new** Layer-2-or-later adapter — not an edit of these sealed callers, and not a Layer 3 flip.

`6ca03716` as “Phase A IF pin / live caller SoT”: **EXISTING BUT UNVERIFIED** for Layer 3. Live IF _code_ SoT on this branch is CLEAR-A `1b39f4e9`. `6ca03716` **is** the sealed offline diagnostic IF tip on #672. Those are different claims.

### Layer 3 — Actual deployed runtime today

What Railway beat/worker and the model-service HTTP path **invoke** on inspected live tip `f5e3bb58`. **Blended** `simulate_nfl_game`. Not the labeled IF entry. Not Q2 Massey.

| Entrypoint                | File:lines                                                                                                                                      | Invoke                                                                                                                                                             |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Celery task               | `services/model-service/src/tasks.py:4531–4542` `run_nfl_market_simulations`                                                                    | Default production slate runner. Routed on `QUEUE_MODELS` (`celery_app.py:133`). Beat name `TASK_RUN_NFL_SIMULATIONS` (`main.py:79`, `celerybeat_schedule.py:20`). |
| Strength load (same task) | `tasks.py:4723–4727` → `_load_team_strength_priors(..., as_of_week=matchup_week_for_priors)` then `_resolve_team_strength_indices` `:4800`      | EPA / packaged priors → `NflGameInputs.offense_index_*` / `defense_index_*`. Week-cap, not kickoff-instant.                                                        |
| Sim call (same task)      | `tasks.py:4967–4977` `simulate_nfl_game(inputs, ..., market_spread_home=..., market_total=...)`                                                 | **`independent_fair` omitted → False.** Market blend ON when lines exist (`NFL_MARKET_BLEND_*` in `nfl_simulator.py:32–33`).                                       |
| HTTP                      | `services/model-service/src/routes/nfl.py:4739–4744` `POST /simulations/{game_id}` `run_nfl_simulation` → `:4893–4898` `simulate_nfl_game(...)` | Same blended entry. Audit stamp on this path includes `production_promote=False` (`:4908`).                                                                        |
| Week-cap (not `cf514078`) | `tasks.py:765–773` `_week_cap_nullable_predicate`; `:780–829` `_fetch_rolling_feature_latest_rows(..., week_cap=)`                              | `week <= week_cap`. **Do not claim week-cap = `cf514078`.**                                                                                                        |

**Layer 3 does not run subscriber Independent Fair forecasts.** CERT=0 · pub/bet HOLD · Coming Soon remains the product posture this paper assumes. Presence of `nfl_market_projections` writes on the HTTP/task path is **not** CERT>0, **not** a PLAY tag, and **not** a claim that subscribers are consuming IF.

### Layer-collapse defects (do not write)

| Defect                                        | Why                                                                                                                                |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| “IF is tests-only”                            | True only for Layer 1 non-definition imports on live HEAD. False for Layer 2 (`score_t4910u.py` / `19c6a460` / #662 orchestrator). |
| “IF is in production”                         | Layer 1 code is merged; Layer 3 callers still use blended `simulate_nfl_game`.                                                     |
| “Week-cap is the as-of rule”                  | Layer 3 week-cap ≠ Layer 2/`cf514078` kickoff-instant.                                                                             |
| “`6ca03716` is the live IF caller”            | That tip is the sealed offline diagnostic IF tree (#672). Live code SoT is `1b39f4e9`.                                             |
| Using ALEX_E1 (`b41f4b43`) as Q2 sidecar math | Different contract. See §8.                                                                                                        |

---

## 2. Purpose of `Q2AsOfSidecar`

Optional **research annotation** that can sit **beside** an Independent Fair projection / L0 envelope and cite frozen Q2 Phase B as-of strength **without** mutating live strength or IF margin.

Reuse the accepted keep method (OWNER ACCEPT `03a4dd90`; FROZEN `28c582a1` / fit `70db070d` / config `aa2b47b3`; as-of `cf514078`) toward Independent Fair (CLEAR-A `1b39f4e9`) **as a named sidecar**, not as a replacement engine.

**Not implemented here.** EXEC of a writer Needs Ryan (appendix). This paper only names fields, units, join, cutoff, pins, fail-closed, and isolation.

---

## 3. Fields and units

All `q2_*` values are **research annotation**. Source of truth for each numeric field is the sealed keep packet on #679 — **do not refit**.

### 3a. Game identity (join keys)

| Field         | Type / unit                                   | Source symbol (packet #679)     | Required                                                                                  |
| ------------- | --------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------- |
| `game_id`     | string                                        | `Game.game_id` (`q2pb/data.py`) | **yes** if the other side has `game_id`; else fail-closed unless `Game.key` join succeeds |
| `season`      | int (NFL season year)                         | `Game.season`                   | yes                                                                                       |
| `week`        | int (REG week)                                | `Game.week`                     | yes                                                                                       |
| `home`        | string (team code as in `games_4fe1cdd7.csv`) | `Game.home`                     | yes                                                                                       |
| `away`        | string                                        | `Game.away`                     | yes                                                                                       |
| `kickoff_utc` | tz-aware UTC datetime                         | `Game.kickoff_utc`              | yes                                                                                       |

`Game.key` = `(season, week, home, away)` (`q2pb/data.py` property `key`).

**Join rule**

1. If both the sidecar row and the IF/L0 row have a non-empty `game_id`, join on `game_id`.
2. Else join on `Game.key`.
3. If neither join is unique and complete → **refuse the row** (fail-closed). Do not fuzzy-match on name, market, or week alone.
4. Sidecar must carry **both** `game_id` (when present on the games pin) **and** `Game.key` components so either side can join.

Do not invent a new identity. Do not map franchise aliases at join time beyond the keep packet’s existing `PRIOR_ALIAS` / `PRIOR_ALIAS_REVERSE` (`q2pb/constants.py`), which apply to **prior-season rating carry only**, not to game identity.

### 3b. As-of strength (frozen solve; no new ridge)

| Field             | Type / unit                                                                   | Source symbol                              | Frozen use                                             |
| ----------------- | ----------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------ |
| `q2_home_s`       | float — ridge Massey team rating (home), mean-centered within the as-of solve | `AsOfFeatures.home_s` ← `asof_for_targets` | input to `q2_rating_diff`                              |
| `q2_away_s`       | float — same scale (away)                                                     | `AsOfFeatures.away_s`                      | input to `q2_rating_diff`                              |
| `q2_rating_diff`  | float — `q2_home_s − q2_away_s` (dimensionless rating points)                 | `AsOfFeatures.rating_diff`                 | Spearman screen; **only** allowed input to `q2_pm_new` |
| `q2_hfa`          | float — unpenalized home-field intercept from the same as-of solve            | `AsOfFeatures.hfa` / `StrengthSolve.hfa`   | diagnostic; **not** added again into `q2_pm_new`       |
| `q2_n_asof_games` | int — count of current-season scored games with `kickoff_utc <` target        | `AsOfFeatures.n_asof_games`                | leakage assert recount                                 |

Sealed solve knobs (FROZEN; do not retune): λ = `20.0`, regression fraction r = `0.5`, n_fit = 960, n_ties_excluded = 4. Model: `margin = h + s_home − s_away` (`q2pb/strength.py` module docstring).

### 3c. As-of W-L comparator (definition frozen; not an IF input)

| Field             | Type / unit                                                                 | Source symbol                                         | Definition                                                                                                                              |
| ----------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `q2_asof_wl_diff` | float — home current-season as-of win% minus away current-season as-of win% | `asof_wl_diff(game, history)` (`q2pb/metrics.py:212`) | win% = `(W + 0.5·T) / (W+L+T)`; **0-0 → 0.5** (`win_pct`, `q2pb/data.py:201–205`); as-of games have `kickoff_utc <` target (`cf514078`) |

`games.csv` `4fe1cdd7` has **no** `wl_diff` column. `record_entering_home/away` is a mapping cross-check only (Pearson vs recomputed = 0.99993 on the sealed DEV). Sidecar stores the **recomputed** `asof_wl_diff`, not the record-column mapping.

`pm_WL` / `P_new` / cluster bootstrap / ICC are **keep-packet eval/diagnostic only**. They are **not** `Q2AsOfSidecar` fields and are **SUPERSEDED** as Independent Fair runtime dependencies (map §1 #7–8). Do not add them to the sidecar.

### 3d. Mapped margin (frozen DEV OLS only)

| Field       | Type / unit                         | Formula (sealed coefficients; do not refit) |
| ----------- | ----------------------------------- | ------------------------------------------- |
| `q2_pm_new` | float — mapped home margin (points) | `2.56374413 + 1.66062406 · q2_rating_diff`  |

Exact FROZEN JSON coefficients (`a_q2`, `b_q2` on #679):

- `a_q2 = 2.5637441292077354`
- `b_q2 = 1.660624056183471`

A writer, if later CLEARED, **applies these sealed numbers**. No new OLS, no EVAL-window refit, no intercept tweak, no HFA add-on.

`q2_pm_new` is **not** `independent_fair.margin_mu` and must not be written into it.

### 3e. Pin fields (required on every row)

| Field           | Value                                                                                                                                         | Meaning                        |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `q2_fit_sha`    | `70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571` (prefix `70db070d` acceptable if the writer stores prefix + verifies full) | sealed fit object              |
| `q2_config_sha` | `aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49` (prefix `aa2b47b3`)                                                        | sealed config                  |
| `q2_asof_rule`  | `cf514078`                                                                                                                                    | kickoff-instant as-of (see §5) |
| `q2_games_pin`  | `4fe1cdd7` (full games sha256 `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`)                                             | primary games.csv              |

Optional provenance (recommended, not a substitute for the four pins): `q2_frozen_md_sha = 28c582a1…`, `q2_keep_commit = af6be4f5…`, `q2_outcomes_sha = 50bda875…` (score-only extract; **not** an experiment frame).

---

## 4. Isolation — must not mutate live strength or IF margin

A sidecar row is **non-authoritative payload beside** L0 / IF projection.

**Forbidden writes** (Needs Ryan if anyone proposes them; this contract refuses them):

| Target                                                    | Why forbidden                                                                                           |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `NflGameInputs.offense_index_home` / `offense_index_away` | Live EPA / packaged strength (Layer 3). Writing Q2 ratings here changes the sim.                        |
| `NflGameInputs.defense_index_home` / `defense_index_away` | same                                                                                                    |
| L0 `off_eff_h` / `off_eff_a` / `def_eff_h` / `def_eff_a`  | Ledger required fields (`schema.py:64–67`). Q2 is not EPA efficiency.                                   |
| `independent_fair.margin_mu` / `total_mu` / `sigma`       | Frozen IF math = `compute_nfl_projection_decomposition` + MC loop + `independent_fair=True` blend-zero. |
| `L0.market_blend`                                         | IF L0 requires exact 0. Sidecar must not set or “help” this field.                                      |
| `L0.margin_mu` / `total_mu` / `sigma`                     | same as IF mus                                                                                          |
| Any `trailing_*` / packaged EPA / S1 family               | S1 kill `50f57195`. Do not revive.                                                                      |

Attach **beside**. Do not merge maps. Do not “blend Q2 into EPA.” Do not shift MC draws.

---

## 5. Pregame cutoff / as-of rule

**Sidecar as-of = `cf514078` (kickoff-instant), not week-cap.**

Keep-packet rule (`q2pb/strength.py` module docstring; `TIP_ASOF_KICKOFF = "cf514078"` in `q2pb/constants.py`):

> Only games with kickoff **strictly before** the target kickoff enter the design matrix. Same-kickoff games do not see each other.

Operational consequences for the sidecar:

- History filter: `h.kickoff_utc < target.kickoff_utc` (strict).
- Same kickoff timestamp → **excluded** (not in `q2_n_asof_games`).
- Later kickoff → **excluded**.
- Prior-season ratings enter only as the ridge **target** after `carry_prior` (r = 0.5), then the current-season as-of solve. Season-end ratings feed the **next** season’s prior only (`asof_for_targets`).
- Week number is **not** the cutoff. A week-2 Saturday night game does not see a week-2 Sunday game even if both are “week 2.”

**Contrast — Layer 3 week-cap (not this rule):**

`_load_team_strength_priors(..., as_of_week=)` → `_fetch_rolling_feature_latest_rows(..., week_cap=)` uses `week <= week_cap` (`tasks.py:765–773`, `:780–829`). Ledger `canonicalize_as_of_ts` / `as_of_ts ≤ decision_ts` is **capture identity**, not Massey design-matrix leakage.

**Do not claim week-cap = `cf514078`.** A sidecar writer that filters on week only is a contract violation.

---

## 6. Prior-game exclusion / leakage assert

Reuse existing `assert_asof_leakage` (`q2pb/strength.py`). Do not write a new guard.

Behavior (packet):

1. Recount current-season scored games with `kickoff_utc <` target.
2. If recount ≠ `q2_n_asof_games` → `AssertionError` (fail-closed).
3. Target cannot appear in its own window (`self-inclusion` assert on `game_id`).
4. Same-kickoff and later games are not countable.

Sidecar contract: if leakage assert would fire, **do not emit the row**. No partial fill, no “use last good week,” no impute of `q2_home_s` / `q2_away_s` from season-end or from Layer 3 EPA.

---

## 7. Missing-data refusal (fail-closed)

Refuse the **row** (and, if a batch writer is later CLEARED, refuse the batch if the contract so states — default: **row refuse**, do not impute) when any of the following hold:

- Any required identity field missing / non-finite kickoff.
- Join failure (§3a).
- Any of `q2_home_s`, `q2_away_s`, `q2_rating_diff`, `q2_hfa`, `q2_n_asof_games`, `q2_asof_wl_diff`, `q2_pm_new` missing, NaN, or non-finite.
- Any pin field missing or not equal to the sealed values in §3e.
- `asof_for_targets` / `asof_wl_diff` / `assert_asof_leakage` cannot run on the pinned games + score-only extract.
- Writer would need scored columns / `trailing_*` / EPA / 2023–26 from hist index `1ee90fac` (gate `83646d78`).
- Writer would need 2024–25 rows.
- Writer would apply a new transform, new OLS, or a week-cap substitute for `cf514078`.

**No silent dataclass defaults.** This is the same fail-closed spirit as ledger L0 “missing ⇒ REJECT, never impute” (`schema.py:58–59`) and as ALEX_E1’s “FORBID silent defaults” — applied here to **Q2 sidecar fields**, not as a claim that this paper verified ALEX_E1 as Q2-secondary.

---

## 8. `b41f4b43` (Alex PASS_RO_MAP `4a1bc064`) — cite the box file; do not run Q2 EPA secondary

If this sidecar paper names `b41f4b43`, the box file is:

`ops/nfl_enterprise_green_t4359u/ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md`

Alex PASS_RO_MAP tip `4a1bc064` (on #680): that path matches tip `b41f4b43`.

**This clone:**

- Exact box path `ops/nfl_enterprise_green_t4359u/ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` is **absent** from `deploy-vercel`, draft #679, and draft #680.
- Content-identical file on draft [#663](https://github.com/kosedge/kosedge/pull/663) (`cursor/hift1-efficiency-recovery-f693`): `data/ops/nfl-efficiency-2026-w1-w8-t4770u/ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md`.
- sha256 of that inspected file: `b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4` (prefix **`b41f4b43` MATCH** this inspection).

`b41f4b43` remains **EXISTING BUT UNVERIFIED as Q2-secondary / Phase A EPA-secondary mapping**. File-hash match is **not** a license to:

- run Q2 EPA / PBP secondary (keep: SKIPPED/UNAVAILABLE; no `6ee24b44` claimed here),
- revive S1 (kill `50f57195`),
- treat ALEX_E1’s 20 `NflGameInputs` efficiency fields as `Q2AsOfSidecar` fields,
- claim this paper verified `b41f4b43` as an IF consume map for Massey ratings.

ALEX*E1 is an **efficiency-input** contract for `simulate_nfl_game_independent_fair` (`offense_index*_`, `_\_epa_5g`, matchup diffs, …). `Q2AsOfSidecar`is a **different named interface** (map §2c). A future adapter that claimed to *be*`b41f4b43` still **Needs Ryan**.

---

## 9. Reuse existing symbols only — no new transform, EVAL, retune, or source

If OWNER later CLEARs a writer, it may call **only**:

| Symbol                                                         | Packet path                                             | Allowed use                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| `asof_for_targets`                                             | `research/q2_phase_b_t5009u/q2pb/strength.py`           | emit `home_s` / `away_s` / `rating_diff` / `hfa` / `n_asof_games` |
| `asof_wl_diff`                                                 | `q2pb/metrics.py`                                       | emit `q2_asof_wl_diff`                                            |
| `assert_asof_leakage`                                          | `q2pb/strength.py`                                      | refuse leaking rows                                               |
| sealed coefficients                                            | FROZEN md/json `28c582a1` / `aa2b47b3` / fit `70db070d` | `q2_pm_new = a_q2 + b_q2 · rating_diff`                           |
| `load_games` / `verify_games_pin` / `load_outcomes_score_only` | `q2pb/data.py`                                          | pin `4fe1cdd7`; score-only extract `50bda875`                     |

**Blocked**

- Gate `83646d78` blocks scored reuse of hist index `1ee90fac` (keep extract is six identity+score columns for 2013–2022 only; not an experiment frame).
- Stage C **AMEND** — not cleared.
- S1 kill `50f57195` — do not revive EPA-trail / `trailing_*`.
- No second EVAL look (`fe90f5f0` already k: 0→1; research-consumed).
- No new ridge, map, bootstrap, threshold, or source acquisition.
- No merge of #679 or #680.
- No Python implementation in this PR.

---

## 10. What the sidecar is _not_

- Not live team strength.
- Not L0 `off_eff_*`.
- Not IF `margin_mu`.
- Not a market blend weight.
- Not ALEX_E1 efficiency fields.
- Not a CERT, PLAY, or pub surface.
- Not a week-cap EPA prior.
- Not a second Q2 EVAL.

---

## Appendix A — CoS wiring card (HELD · do not implement)

**Wiring stays HELD.** This appendix is the exact future behavior **if** OWNER later CLEARs a writer. It is not a CLEAR.

### A1. Future behavior (only after OWNER CLEAR)

1. Read pinned `games_4fe1cdd7` + score-only extract `50bda875` through existing loaders.
2. Call `asof_for_targets` with sealed λ=20, r=0.5, incoming priors from the sealed fit object `70db070d` (no re-solve of DEV hyperparameters).
3. Call `asof_wl_diff` per target.
4. Run `assert_asof_leakage`; refuse failures.
5. Set `q2_pm_new` from sealed `a_q2`/`b_q2` only.
6. Stamp pin fields (§3e).
7. Join to an existing IF/L0 `game_id` or `Game.key`.
8. Persist or return a **sidecar document** beside the projection. Do **not** call `simulate_nfl_game_independent_fair` from a new Q2 runner unless a **separate** OWNER CLEAR says so (that would be caller wiring, not this contract).
9. Do not write the forbidden targets in §4.

### A2. Verification gates (paper; not run here)

- Pin sha match: games `4fe1cdd7`, fit `70db070d`, config `aa2b47b3`, as-of tip `cf514078`.
- Leakage assert green on the emitted set.
- No write into `offense_index_*` / `defense_index_*` / L0 `off_eff_*` / `independent_fair.margin_mu` / `L0.market_blend` (diff-level proof).
- Fail-closed on one deliberately missing field.
- Layer 3 `run_nfl_market_simulations` / `POST /simulations/{game_id}` still call blended `simulate_nfl_game` unless a **later** OWNER CLEAR says otherwise.
- No 2024–25 rows. No `1ee90fac` scored columns. No S1.

### A3. Remaining Needs Ryan boundary

- Any EXEC: sidecar writer, IF caller wiring, ledger L0 capture, Railway/Vercel, merge of #679 / #680 / this PR.
- Writing Q2 ratings into `NflGameInputs` or L0.
- Any new fit, map, bootstrap, EVAL look, or threshold.
- Stage C EXEC or AMEND lift.
- Opening 2024–25 or sealed holdouts.
- Scored reuse of `1ee90fac` beyond the already-documented six-column extract.
- Claiming `b41f4b43` or `6ca03716` **verified as Q2-secondary / live IF SoT** without a new OWNER/Alex close (this paper located the ALEX_E1 file hash and the #672 offline tip; that is not those claims).
- Treating `e7b7c567` as a git-verified ACCEPT without locating the artifact.
- Reviving S1 / EPA-trail / `trailing_*`.
- CERT>0, pub, bet, production promote.

CoS may ACCEPT this **paper** under standing RO authority. CoS may not EXEC wiring from this file.

---

## 11. Hard holds (do not propose lifting)

- Stage C AMEND
- Scored feature reuse of `1ee90fac` **BLOCKED** (gate `83646d78`)
- No further Q2 EVAL / retune
- No production promote
- CERT=0
- pub/bet HOLD
- No 2024–25 access
- No S1 revive (kill `50f57195`)
- No merge of draft #679 or #680
- No model math / feature change on the live sim
- No implementation in this PR

---

## 12. Citations

keep `03a4dd90` · FROZEN `28c582a1` · EVAL `fe90f5f0` · Alex keep RO `d12898a2` · Alex PASS_RO_MAP `4a1bc064` · erratum `06849c65` · gate `83646d78` · COMPONENTS_Q2PB · fit `70db070d` · config `aa2b47b3` · as-of `cf514078` · IF pin `6ca03716` (offline diagnostic tip on #672; **not** live Layer 3 SoT) · contract `b41f4b43` = box `ops/nfl_enterprise_green_t4359u/ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` (EXISTING BUT UNVERIFIED as Q2-secondary) · S1 kill `50f57195` · delegation `97925eb5` · CLEAR-A `1b39f4e9` · games `4fe1cdd7` · outcomes `50bda875` · EXEC commit `af6be4f5` · map `be8c27a6` · live tip `f5e3bb58` · offline score `19c6a460` / close `02197f58` · simulator pin `52d9e909` · R1 IF-only ACCEPT `e7b7c567` (cited; **not located** as a git object on this clone).
