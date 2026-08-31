# CFB Engine Audit — unify live API onto frozen SoT

**Base:** `deploy-vercel` @ tag `cfb-week0-close-2026-08-31` (`bfe5b0b5`)  
**Branch:** `cursor/cfb-unify-live-api-onto-power-sot-3ca1`  
**Mode:** Phase 0 READ ONLY — paths opened below; no WP / shock / power / Utah edits.

---

## Two-clock table

| Surface                               | Path                                                                             | Version stamp                                                                                                                                              | as_of                                                                     | Universe (official vs densified)                                                                                                                             | Power source                                                                                             |
| ------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Live status / project-game / simulate | `services/model-service/src/routes/cfb.py` → `cfb_season_engine`                 | **`cfb-season-engine-v0.9-inseason`** (`priors.ENGINE_VERSION` / `DEFAULT_SEASON_ENGINE_VERSION`; hard fallback string also in `cfb_season_engine_status`) | not stamped as product `as_of` on every payload; status uses live compose | **Official ESPN slate** when `cfb_official_schedule_2026.json` present (`loaders._build_universe_from_team_payloads`); densify only if official blob missing | Live `compose_team_projection` from packaged SP+/roster (same off/def indices as frozen SoT on canaries) |
| Frozen power SoT JSON                 | `…/data/cfb_power_sot_2026.json` (+ `apps/web/lib/data/cfb-power-sot-2026.json`) | `engine_version=**v0.9-inseason**` · `power_version=**cfb-power-sot-v0.15-week0-close-20260831**`                                                          | `power_as_of=2026-08-31`                                                  | Official schedule used at build (`close_week0.py` / `power_sot`)                                                                                             | `power_sot.build_power_sot`                                                                              |
| Frozen season projections             | `…/data/cfb_season_projections_2026.json` (+ web mirror)                         | `engine_version=**v0.9-inseason**` · `power_version=v0.15-week0-close` · `artifact_id=…v0.15-n10000-week0-close…`                                          | `as_of=2026-08-31` · `power_as_of=2026-08-31`                             | Official closed slate (6 Week-0 finals locked)                                                                                                               | Frozen power indices + Bernoulli sim                                                                     |
| Frozen futures / KEI                  | `cfb_futures_2026.json` · `cfb_kei_w0_w1_2026.json`                              | `engine_version=**v0.9-inseason**`                                                                                                                         | `as_of=2026-08-31`                                                        | Same closed slate                                                                                                                                            | Futures from power-aware field; KEI game line                                                            |
| Preview `modelNote`                   | `apps/web/lib/cfb-previews.ts`                                                   | Prose claims **`cfb-season-engine-v0.15-power-sot`**                                                                                                       | `as_of 2026-08-31`                                                        | n/a (copy)                                                                                                                                                   | Numbers from dump; **engine string ≠ JSON `engine_version`**                                             |
| Densify path (fallback)               | `schedule.densify_schedule` via `loaders` when official blob absent              | inherits `ENGINE_VERSION`                                                                                                                                  | n/a                                                                       | Densified sample                                                                                                                                             | Same compose                                                                                             |

**Honest two-clock diagnosis (opened evidence):**

1. **Stamp fork (primary):** `priors.ENGINE_VERSION` is still `cfb-season-engine-v0.9-inseason`. Week 0 close wrote that string into frozen JSON. Preview prose and the Week 0 audit narrative talk about `cfb-season-engine-v0.15-power-sot`. That is three labels for one board.
2. **Universe fork (mostly closed):** Live `resolve_season_universe(demo=True)` already loads official schedule (`official_schedule=true`, 889 games, slate_complete, 6 Week-0 finals scored). Densify is **not** the live default when the official blob is present. `loaders.documentation()["schedule_policy"]` still **lies** (“seed sample + densify…”).
3. **Ratings fork (not observed on canaries):** Live off/def indices for OSU/USF/Utah/top-7/cupcake opponents **match** frozen power SoT to displayed precision. Live cupcake WPs match the closed dump (BALL@OSU 0.98, FRES@USC 0.9278, MASS@RUT 0.9147).

---

## Live API entrypoints

| Route / symbol                                            | File                                       | Calls                                                                                                                                                          |
| --------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /cfb/season-engine/status`                           | `routes/cfb.py` `cfb_season_engine_status` | `engine_status_payload` ← `resolve_season_universe`; hardcodes fallback `"cfb-season-engine-v0.9-inseason"`                                                    |
| `POST /cfb/season-engine/project-game` (+ `game-preview`) | `routes/cfb.py`                            | `resolve_season_universe` → `project_game_preview` → `project_game` (`team_projection.py`)                                                                     |
| `POST /cfb/season-engine/simulate`                        | `routes/cfb.py`                            | `resolve_season_universe` → `simulate_full_season` (`season_sim.py`)                                                                                           |
| In-season ingest / state / reset                          | `routes/cfb.py` + `in_season_update.py`    | Opt-in (`apply_inseason` default **false** on result POST). Efficiency profile defaults `apply_inseason=True` but empty state is currently a no-op on canaries |
| `resolve_season_universe`                                 | `loaders.py`                               | Prefer `build_packaged_universe` → official schedule when blob present                                                                                         |
| `compose_team_projection`                                 | `team_projection.py`                       | Used inside universe build / project-game                                                                                                                      |
| `DEFAULT_SEASON_ENGINE_VERSION`                           | `__init__.py`                              | Alias of `priors.ENGINE_VERSION`                                                                                                                               |

---

## Frozen publisher entrypoints

| Symbol / script                                                                          | File                                                          | Role                                                                                      |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `build_power_sot` / `build_season_projection_artifact` / `package_power_and_projections` | `power_sot.py`                                                | Writes power + proj JSON; stamps `ENGINE_VERSION` + `POWER_VERSION` / close power version |
| `CLOSE_POWER_VERSION`                                                                    | `power_sot.py`                                                | `cfb-power-sot-v0.15-week0-close-20260831`                                                |
| `scripts/cfb/close_week0.py`                                                             | locks Week-0 finals; repackages with `CLOSE_POWER_VERSION`    |                                                                                           |
| `scripts/cfb/package_power_sot_and_projections.py`                                       | packaging entry                                               |                                                                                           |
| `scripts/cfb/build_cfb_kei_futures_2026.py`                                              | KEI + futures artifacts; uses `DEFAULT_SEASON_ENGINE_VERSION` |                                                                                           |
| `scripts/cfb/cfb_dump_canaries.py`                                                       | reads frozen JSON (site loaders’ numbers)                     |                                                                                           |
| Web mirrors                                                                              | `apps/web/lib/data/cfb-*.json`                                | Served by `cfb-research-artifacts.ts` / `cfb-kei-artifacts.ts`                            |

---

## Where ENGINE_VERSION is set (must become one symbol)

| Symbol                          | Location                                          | Current value                                                         |
| ------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| **`priors.ENGINE_VERSION`**     | `priors.py:41`                                    | `cfb-season-engine-v0.9-inseason` ← **single SoT for code**           |
| `DEFAULT_SEASON_ENGINE_VERSION` | `__init__.py`                                     | `= ENGINE_VERSION`                                                    |
| Hardcoded fallback              | `routes/cfb.py:101`                               | `"cfb-season-engine-v0.9-inseason"` (pre-import)                      |
| Written into artifacts          | `power_sot.py`, futures/KEI builders              | copies `ENGINE_VERSION` at package time                               |
| Preview prose                   | `cfb-previews.ts` modelNote                       | `cfb-season-engine-v0.15-power-sot` (hand string; not reading priors) |
| Power layer stamp (separate)    | `power_sot.POWER_VERSION` / `CLOSE_POWER_VERSION` | `cfb-power-sot-v0.15-…` — keep; do not confuse with engine stamp      |

**Phase 1 rule:** change `priors.ENGINE_VERSION` to `cfb-season-engine-v0.15-power-sot`, re-stamp artifact `engine_version` fields (and web mirrors) **without** re-simming a new E[wins] board, fix the `cfb.py` fallback + `loaders.documentation` schedule_policy lie, regenerate preview `modelNote` engine substring from the dump/constant (no hand-authored ratings).

---

## Default universe today vs required default

|                 | Today (opened)                                              | Required after unify                                                               |
| --------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Schedule        | Official ESPN blob default; densify fallback only           | Same — densify behind explicit flag / tests only                                   |
| Week 0 finals   | 6 FBS scores locked on live schedule objects                | Same                                                                               |
| Team priors     | Packaged real-roster + SP+ compose                          | Same sources; indices already match frozen SoT                                     |
| Research stamp  | `v0.9-inseason`                                             | **`cfb-season-engine-v0.15-power-sot`** everywhere research is served              |
| Product `as_of` | Artifacts `2026-08-31`; live status does not always echo it | Live research payloads should carry `as_of` / `power_as_of` consistent with frozen |

---

## In-season evolution: what it does, whether it is default

- Module: `in_season_update.py` — ingest result → efficiency deltas on disk/state.
- HTTP: `POST …/projections/{id}/result` with `apply_inseason=false` by default; separate ingest/reset routes.
- `efficiency.build_efficiency_profile(..., apply_inseason=True)` layers deltas when present.
- **Today:** empty state → no delta on OSU canary (`apply_inseason` True/False identical).
- **Required:** keep hooks; research-fair default must not silently diverge from frozen Week-0 SoT. Do not make densify or in-season the default research universe.

---

## Canary: live project_game vs frozen dump (before)

Dumped on `bfe5b0b5` (read-only probe):

| Canary                   | Frozen dump / SoT                                                     | Live (before unify)                                                                      |
| ------------------------ | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Engine stamp             | JSON `engine_version=v0.9-inseason`; preview claims `v0.15-power-sot` | Live responses `v0.9-inseason`                                                           |
| OSU / USF / Utah power   | 1.6168 / 1.2601 / 1.4841                                              | Live off/def match SoT; power_index on SoT only                                          |
| OSU / USF / Utah E[wins] | 9.537 / 8.382 / 9.634                                                 | Frozen artifact only (live simulate is a separate n_sims path; do not replace 10k board) |
| BALL@OSU WP              | 0.98                                                                  | **0.98**                                                                                 |
| FRES@USC WP              | 0.9278                                                                | **0.9278**                                                                               |
| MASS@RUT WP              | 0.9147                                                                | **0.9147**                                                                               |
| Official schedule        | yes                                                                   | **yes** (`official_schedule=true`)                                                       |
| Week-0 locked scores     | 6 finals                                                              | **6 finals** on live universe                                                            |

**Implication:** Phase 1 is a **stamp + honesty/docs + gates** pass unless something regresses. Do **not** retune WP/shock/power to “unify.” If re-stamping somehow forces a new 10k board that moves E[wins] outside ±0.05, **blocker**.

---

## Shared NFL/CBB risk

- CFB loaders / priors / routes are CFB-scoped.
- `pr-check.yml` path-based DepthSot skip stays as-is (Law 7). Do not widen the mute.
- Do not edit `nfl_*` / CBB / MLB trees.

---

## Phase 1 allowlist

Only these paths (plus regenerating CFB JSON `engine_version` fields they already own):

### Docs

- `docs/CFB_ENGINE_UNIFY_LIVE_API_BRIEF.md`
- `docs/CFB_ENGINE_AUDIT_UNIFY_LIVE_API.md`
- `docs/CFB_ENGINE_UNIFY_LIVE_API_SCORECARD.md`
- `docs/CFB_ENGINE_GATES.md` (add live==frozen assertion only)
- `docs/CFB_ENGINE_BLOCKER.md` (**one** “not this pass” line only)

### Engine / routes (stamp + default honesty — no WP/shock/power knobs)

- `services/model-service/src/services/cfb_season_engine/priors.py` — **`ENGINE_VERSION` string only**
- `services/model-service/src/routes/cfb.py` — fallback stamp / optional `as_of` echo; no NFL routes
- `services/model-service/src/services/cfb_season_engine/loaders.py` — `documentation()` schedule_policy honesty; densify remains non-default
- `services/model-service/src/services/cfb_season_engine/__init__.py` — only if status payload must surface frozen `as_of` (no math)
- `services/model-service/src/services/cfb_season_engine/power_sot.py` — only if needed to write the new `ENGINE_VERSION` into packages **without** changing indices

### Artifacts (re-stamp `engine_version` only — same numbers)

- `services/model-service/src/services/cfb_season_engine/data/cfb_{power_sot,season_projections,futures,kei_w0_w1}_2026.json`
- `apps/web/lib/data/cfb-{power-sot,season-projections,futures,kei-w0-w1}-2026.json`

### Scripts / tests / preview regen

- `scripts/cfb/cfb_dump_canaries.py` (print unified stamp)
- Optional tiny regen helper for preview `modelNote` engine substring from `ENGINE_VERSION` / dump — **no hand-typed 9.54**
- `apps/web/lib/cfb-previews.ts` — only via regen of engine stamp string in modelNote
- `services/model-service/tests/test_cfb_enterprise_gates.py` (or sibling) — live==frozen gates

### Explicitly excluded

- `team_projection.win_prob_from_expected_scores` / `WIN_PROB_MARGIN_SD` / `WP_*`
- `SCORE_NOISE_SD` / `STRENGTH_NOISE` / early mults
- `cfb_futures` logistic / field constructor redesign
- Utah / USF team branches
- NFL / CBB / MLB / DepthSot mute widening
- `cfb_v2/`
- New 10k projection board with moved canary E[wins]

---

## Blockers already visible

| ID                           | Note                                                                                                                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stamp triplicity             | JSON+live=`v0.9-inseason`, preview=`v0.15-power-sot`, power_version=`cfb-power-sot-v0.15-week0-close…`. Unify engine stamp to `cfb-season-engine-v0.15-power-sot` without changing power numbers. |
| Docs lie                     | `loaders.documentation()["schedule_policy"]` still claims densify default.                                                                                                                        |
| Utah blocker                 | `docs/CFB_ENGINE_BLOCKER.md` stands — **not this pass**.                                                                                                                                          |
| Live simulate ≠ 10k artifact | `/simulate` uses small `n_sims` by design. Do not treat a live simulate response as a new win-total SoT; frozen proj JSON remains the published E[wins] board.                                    |
| Re-sim risk                  | If packaging scripts re-roll 10k and move canaries &gt;0.05 → **write unify blocker and stop** (do not retune shock/WP).                                                                          |

---

## Phase 0 freeze confirmation

No WP, shock, power, Utah, or publisher math edits in Phase 0. Next commit: docs-only (`docs: CFB unify live API audit`), then Phase 1 strictly on the allowlist above.
