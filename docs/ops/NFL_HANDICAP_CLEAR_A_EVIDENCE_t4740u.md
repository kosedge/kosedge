# HANDICAP CLEAR-A evidence packet (t4740u) — remotion D1–D4

**Status:** DRAFT PR only · not merged · not deployed  
**Authority:** COS_ORDER_CURSOR_t4740u v2 · DECISION d744fa87 · IMV RETURN **5c616db5** · Codex **3aa21f63** · CoS ACCEPT  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF

CoS seal destination after this tip: `ops/nfl_enterprise_green_t4359u/` (not written here).

## Identity

| Field | Value |
|---|---|
| Branch | `cursor/handicap-clear-a-if-ledger-ed4b` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| Challenged tip | `c525210170fd09864b7232974b37dfc56f2ef4ab` |
| Remotion SHA | `REMOTION_SHA_PENDING` |
| Sealed tip | `git rev-parse HEAD` on this branch after the remotion stamp (F12) |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 |
| Agent run | https://cursor.com/agents/bc-727fa738-c4c8-596c-934f-86d7241eed4b |

## What closed (D1–D4 only)

| Defect | Codex | Close |
|---|---|---|
| D1 L0 blend gate | F1 | `is_exact_zero`: accept `0`/`0.0` only; reject `0.3`, `False`, `True`. `int(blend)` removed. |
| D2 append-only / identity | F2 F3 F4 F13 | Validated-only append; always re-derive `prediction_id`; JSONL load rejects duplicate id (no last-wins); Python identity = DDL unique key (no payload hash); `commit_l1_stage` validate+dup-check all before any write (rollback). |
| D3 as-of / no-impute / L1 set | F5 F6 F7 | Naive timestamps REJECT; mixed-offset tests; no as_of←captured_at, no baseline_ref←baseline_personnel_ref, no empty-string refs, no IF mu→0.0; L1 requires factor, entry_point, delta, uncertainty + original five; L0 required set matches 243a384e. |
| D4 hygiene | F9 F11 F12 | L1 label = `handicap_delta` (not HF); L4 forced `market_informed_fair`; `make_prediction_id` raises `HandicapLedgerReject`; this packet restamped. |

## Residuals (NON_BLOCKING — not closed)

| Residual | Note |
|---|---|
| R1 / F8 | D3(i) oracle still payload-vs-helper at week 8; does not lock `if_out["markets"]` or weeks 1–4. |
| R2 / F10 | DDL `REVOKE FROM PUBLIC` is not an owner lock. Not in `infra/db`. Do not apply. |
| created_at / schema_version defaults | Documented write metadata only; not as-of identity. |

## Files touched (remotion)

- `services/model-service/src/services/nfl_simulator.py` — no IF mu impute; exact blend=0 assert
- `services/model-service/src/services/nfl_handicap_ledger/*`
- `services/model-service/tests/test_nfl_handicap_clear_a_d3.py`
- `services/model-service/tests/test_nfl_handicap_clear_a_d1_d4_remotion.py` — new
- `docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md`

Not touched: `tasks.py`, `routes.py`, `infra/db/*`, web/F2/CERT/Coming Soon, Railway #655, capture, overlays.

## Test commands + results

```bash
cd services/model-service
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py tests/test_nfl_handicap_clear_a_d1_d4_remotion.py -q
```

**15 passed** (5 D3 + 10 remotion probes).

### D3 (still required)

| Test | Result | Hash / delta |
|---|---|---|
| (i) IF vs pre_blend ≤ 0.01 | **PASS** | margin abs 0.00285; total abs 0.00352 |
| (ii) flag OFF sha256 | **PASS** | `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` |
| (iii) missing L1 / future as_of | **PASS** | REJECT, no impute |

### D1–D4 Codex probe regressions

| Probe | Result |
|---|---|
| F1 exact blend=0 | **PASS** |
| F2 attacker id bypass | **PASS** |
| F3 JSONL last-wins | **PASS** |
| F4 payload-hash overwrite | **PASS** |
| F5 naive / mixed-offset TZ | **PASS** |
| F6 no-impute as_of/refs/IF mu | **PASS** |
| F7 L1+L0 required sets | **PASS** |
| F9 HF/MIF smear | **PASS** |
| F11 ValueError→HandicapLedgerReject | **PASS** |
| F13 atomic stage | **PASS** |

## Default path unchanged

- `NFL_INDEPENDENT_FAIR_PATH is False`
- D3(ii) pin reproduced
- Live callers unwired
- No `infra/db` migration

## Hard-stop checklist

| Stop | Held |
|---|---|
| data capture | yes |
| vendor purchases | yes |
| overlays ON any env | yes |
| scoring / experiment / promotion | yes |
| merge / deploy | yes — DRAFT only |
| API / CERT / F2 / Coming Soon | yes |
| S1/EPA · H-QB · Lane B · KEI · #655 | yes |
| tasks/routes wiring · infra/db apply | yes |

## Next

Stop for Codex deltas re-challenge + IMV re-grade. **Do not merge. Do not deploy.**
