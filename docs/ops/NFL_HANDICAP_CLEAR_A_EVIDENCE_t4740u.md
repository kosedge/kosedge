# HANDICAP CLEAR-A evidence packet (t4740u)

**Status:** DRAFT PR only · not merged · not deployed · not sealed by CoS  
**Authority:** COS_ORDER_CURSOR_t4740u · DECISION_RYAN_t4740u · paper **243a384e** · PASS_PAPER **a31035eb**  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF

CoS seal destination after this tip: `ops/nfl_enterprise_green_t4359u/` (not written here).

## Identity

| Field | Value |
|---|---|
| Branch | `cursor/handicap-clear-a-if-ledger-ed4b` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| Tip SHA | *(filled after commit — see git tip on this branch)* |
| DRAFT PR | *(filled after open)* |
| Agent run | https://cursor.com/agents/bc-727fa738-c4c8-596c-934f-86d7241eed4b |

## What landed (CLEAR-A only)

1. **Independent Fair path** — explicit `independent_fair=True` / `simulate_nfl_game_independent_fair()`. Forces `market_blend=0` and labels `forecast_label=independent_fair`. Default `simulate_nfl_game(...)` is unchanged (flag OFF). Production callers (`tasks.py`, `routes.py`) were **not** wired. `NFL_INDEPENDENT_FAIR_PATH` is a constant `False`; the simulator does **not** read an env kill-switch.
2. **Append-only IF/HF/MIF ledger schema** — Python contract + in-memory/JSONL store + DEVELOPMENT_ONLY DDL. Immutable `prediction_id`. L0/L1/L4 fields, as-of provenance, source refs, missingness, `schema_version=handicap-ledger-v0-clear-a`. Duplicate id ⇒ REJECT (never overwrite). **Not** added to `infra/db` (would enter the migrate/Railway path).
3. **D3 fail-closed tests** — all three required reject tests exist and pass on this branch.
4. **Baseline / prod behavior preserved** — D3(ii) sha256 match on flag-OFF blended output.

## Files touched

- `services/model-service/src/services/nfl_simulator.py` — opt-in IF path; default return shape unchanged
- `services/model-service/src/services/nfl_handicap_ledger/__init__.py`
- `services/model-service/src/services/nfl_handicap_ledger/schema.py`
- `services/model-service/src/services/nfl_handicap_ledger/identity.py`
- `services/model-service/src/services/nfl_handicap_ledger/validate.py`
- `services/model-service/src/services/nfl_handicap_ledger/store.py`
- `services/model-service/src/services/nfl_handicap_ledger/ddl_clear_a.sql` — schema only; not a numbered migration
- `services/model-service/tests/test_nfl_handicap_clear_a_d3.py`
- `docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` — this packet

Not touched: `tasks.py`, `routes.py`, `infra/db/*`, web/F2/CERT/Coming Soon, Railway #655, S1/EPA, H-QB, Lane B, KEI, overlays, capture.

## Test commands + results

```bash
cd services/model-service
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py -vv --tb=short
```

Result (this run): **5 passed in 0.05s**

```
test_d3_i_if_mus_match_pre_blend_helper_within_tol PASSED
test_d3_ii_flag_off_prod_path_byte_identical_to_baseline PASSED
test_d3_iii_missing_required_l1_field_or_future_as_of_rejects PASSED
test_d3_iii_valid_l1_appends_and_never_overwrites PASSED
test_if_hf_mif_coexist_without_overwrite PASSED
```

Fixed fixture for (i)+(ii): `game_id=d3ii-clear-a-baseline`, seed **47401**, simulations **800**, `market_spread_home=3.5`, `market_total=43.5`, week 8.

Related existing tests also executed: `test_nfl_simulator.py`, `test_nfl_model_handicap.py`, `test_nfl_play_band_lock.py`. Two **pre-existing** failures in this environment are unrelated to CLEAR-A (`framework_version` expect `v1` vs live `v3.1`; `sqlalchemy` missing for one week-1 guard). D3 module does not depend on them.

## D3 results

### (i) blend=0 ⇒ IF equals pre_blend — **PASS**

`pre_blend_model_markets_from_diagnostics` on the flag-OFF blended projection vs IF mus from `simulate_nfl_game_independent_fair` (same seed/inputs):

| Market | IF mu | helper | abs delta | tol |
|---|---|---|---|---|
| margin (spread) | 0.15714686663257818 | 0.16 | 0.002853133367421823 | ≤ 0.01 |
| total | 43.8164760328315 | 43.82 | 0.003523967168497677 | ≤ 0.01 |

IF diagnostics: `spread_weight=0.0`, `total_weight=0.0`, `market_blend=0`, label `independent_fair`.

### (ii) flag OFF ⇒ prod-path byte-identical — **PASS**

Canonical sha256 (`json.dumps(..., sort_keys=True, separators=(',', ':'), default=str)`):

`75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`

Pinned on `deploy-vercel` `209e90aa` **before** CLEAR-A edits; reproduced after edits with default `simulate_nfl_game` and with `independent_fair=False`. Output keys remain `decomposition, diagnostics, game_id, inputs, markets, model_version, simulation_count` (no IF payload on default path).

### (iii) missing L1 field or as_of_ts > decision_ts — **PASS**

Each of `capture_id`, `as_of_ts`, `baseline_ref`, `registry_id`, `source_snapshot_id` omitted ⇒ `HandicapLedgerReject`, stage fails, store length 0 (no impute).  
`as_of_ts > decision_ts` ⇒ REJECT, store length 0.  
Valid L1 appends; second write of same `prediction_id` ⇒ `never overwrite`.

## Default path unchanged

- `NFL_INDEPENDENT_FAIR_PATH is False`
- Live callers still invoke `simulate_nfl_game` without the IF flag
- No `infra/db` migration (Railway migrate path untouched)
- Overlays not enabled on any env

## Hard-stop checklist

| Stop | Held |
|---|---|
| data capture | yes — schema/tests only, no rows captured |
| vendor purchases | yes |
| Handicap overlays ON any env | yes — overlay OFF |
| predictive experiments | yes |
| model promotion | yes |
| scoring | yes |
| merges | yes — DRAFT PR only |
| deployments | yes |
| API restore | yes |
| F2 / CERT / Coming Soon changes | yes |
| S1/EPA | yes |
| H-QB | yes |
| Lane B | yes |
| KEI mint | yes |
| Railway #655 | yes |

## Next (not this PR)

Codex challenge + IMV validation of this sealed evidence. **Do not merge. Do not deploy.** CLEAR-B (capture) is a later CLEAR after prereg + IMV PASS on CLEAR-A.
