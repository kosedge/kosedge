# W8 prospective capture — acceptance criteria build

**Filed:** 2026-10-22  
**Package:** `services/model-service/src/services/nfl_w8_capture/`  
**CLI:** `scripts/nfl/w8_capture/dry_run.py`  
**Isolated from:** `nfl_eval_prep` (AC-10). No publish (AC-11). Grader is not this builder (AC-9).

Official seal time (AC-1) is **when the custodian receives the sha**, not when this process writes files. Default one seal by **2026-10-29 19:15 ET**. Minimum lead **60 minutes** before kickoff.

Odds MS-1..MS-10: official IMV memo is **not in this public repo**. Local contract in `constants.py` implements the AC-4 text (book / captured_at / price; gaps = MISSING, never backfilled). Difference vs the off-repo memo: **UNKNOWN**.

| AC | Implementation |
| -- | -------------- |
| AC-1 | `DEFAULT_SEAL_BY_ET`, `MIN_LEAD_MINUTES`, `record_custodian_receipt` |
| AC-2 | `validate_input_proof` — UTC as-of must equal source capture; week-number matching refused |
| AC-3 | `pins.json` — model_version, code_sha, input_shas, criteria, protocol |
| AC-4 | `odds_ms.snapshot_record` — MISSING never filled |
| AC-5 | `SHA256SUMS` + hash-chained `evidence_log.jsonl` |
| AC-6 | `market_informed` and `independent` directories; forbidden-key check |
| AC-7 | Post-seal file edit fails SHA256SUMS verify |
| AC-8 | Missing snapshot or late as-of/seal → `FAIL` |
| AC-9 | `blind_grade_handoff.json` with `grader=NOT_CAPTURE_BUILDER`, outcomes omitted |
| AC-10 | `isolation.historical_rebuild_import_hits` must be empty |
| AC-11 | `refuse_publish` |

| Dry-run | What |
| ------- | ---- |
| DR-1 | End-to-end synthetic seal + custodian receipt |
| DR-2 | Edit after seal detected |
| DR-3 | Late timestamp → FAIL |
| DR-4 | Missing snapshot → FAIL |
| DR-5 | Evidence-log edit detected |
| DR-6 | Market input on independent stream detected |

Dry-run refuses `DATABASE_URL` / Odds keys. Credentials are operator-supplied off-agent only.

## Fail-closed flags (RA-1 / RA-6)

| Flag | Behavior |
| ---- | -------- |
| F-0 | `efficiency_backbone.blend_packages` raises if `continuity_score` import fails; no silent 0.0 boost |
| F-1 | Missing SQLAlchemy no longer drops the tendency signal (`tendency_game_signals` is pure math). If the pricing module itself cannot be imported, `nfl_simulator` fail-closes instead of 0.0 |
| F-2/F-3 | Six continuity loaders raise `ContinuitySourceError` instead of emptying roster/QB/skill/coaching. Corrupt packaged QB1/coaching JSON and official-depth DB failures also fail closed |
| F-4 | Each W8 build records `NFL_*` names in `manifest.json`. Any override is STOP. A non-float `NFL_*` value no longer reverts to the framework default |
| F-5 | W8 builder refuses a regular or earlier `src` on `sys.path` that would shadow the namespace package |
| F-6 | W8 builder STOP if `DATABASE_URL` is set, a DB session is passed, or a continuity/tendency DB fetcher is invoked during the build |

**Still missing for a live W8 seal:** operator Odds snapshots (or honest MISSING rows) per game; real code sha of the deploy pin; custodian identity and receipt channel; live kickoff list; no publish.

**ETA:** dry-run ready now (target 10-27). Deliver dry-run evidence by **10-28 12:00 ET**. Live seal window: **10-29 19:15 ET** (custodian receipt is official).
