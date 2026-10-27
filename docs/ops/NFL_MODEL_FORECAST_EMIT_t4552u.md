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

## t4559u Week 8 slate

Packaged VM inputs **fail** current-input completeness (W1 camp depth, empty `injury_paths`, no `DATABASE_URL`, prior-season EPA only). The slate runner fail-closes. No invented W8 numbers were emitted.
