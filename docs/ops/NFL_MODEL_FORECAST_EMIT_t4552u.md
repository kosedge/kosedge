# NFL model forecast emit — t4552u / t4559u (DRAFT, CERT_CANDIDATE=0)

**Status:** RESEARCH/ENG only. NFL NO-GO / Coming Soon ON. Do not merge. Do not deploy.

Alex eval-record paper **ACCEPTED** sha8 `f1fa86e7` (G1–G8) is the emit contract.

## Where the schema lives

`services/model-service/src/services/nfl_model_forecast_emit/schema.py`  
(`SCHEMA_VERSION = nfl-model-forecast-artifact-v1`)

Emit: `emit.py`. Engine adapter: `engine_adapter.py`. Completeness: `completeness.py`. Bind hook: `binding.py`.

## Later seal binding (not this PR)

Join a prospective Odds seal later by `game_id + forecast_ts_utc + record_sha256`.  
Emitter writes empty `grades` and reserved `close_anchor` — it does **not** write close.  
Do **not** touch #641 tip `385767a2`, first-seal slug `w8_first_seal_b_t4525u_a896cfd0`, or F2 PHI@WAS.

## t4559u / t4564u Week 8

Current-input slate (`run_week_slate`) still fail-closes when completeness is incomplete.

t4564u **research** path emits timestamped G1–G8 artifacts from the packaged engine with **explicit `missing_inputs` flags**. Landed on box (not git, not seals/):

`/workspace/ops/nfl_enterprise_green_t4359u/research_runs/nfl-mfe-2026-w08-20261027T212104Z-f50f15a8/`

SOP `4a017f22`. CERT=0. Not a CLEAR.
