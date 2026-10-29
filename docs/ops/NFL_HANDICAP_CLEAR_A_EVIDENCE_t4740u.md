# HANDICAP CLEAR-A evidence packet (t4740u) — R7 close

**Status:** DRAFT PR only · not merged · not deployed  
**Authority:** COS_ORDER_CURSOR_t4748u R7 · DECISION **39fe2d9d** · IMV PASS_CONTROLS **a9d44516** · tip parent **1443d567**  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF

CoS seal destination after this tip: `ops/nfl_enterprise_green_t4359u/` (not written here).

## Identity

| Field | Value |
|---|---|
| Branch | `cursor/handicap-clear-a-if-ledger-ed4b` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| Parent tip | `1443d567277b7e97271536dbe63871dbf194b00c` |
| R7 remotion SHA | `b2cc5d666b391559fa040e0b716cc1628cb6b383` |
| Sealed tip | stamp commit on this branch (parent R7 remotion `b2cc5d66`); confirm `git rev-parse HEAD` / PR `headRefOid` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 |

## Closed this remotion (R7 only)

| Item | Close |
|---|---|
| R7 | JSONL load no longer prefers top-level over payload. `validate_l0/l1/l4` reject top-level vs payload conflicts (no precedence). L0 rejects any present `market_blend` that is not exact 0 (top-level **and** payload). Contaminated disk row `top=0` + `payload=0.3` REJECT. Clean write+reload ACCEPT; identity unchanged. |

## Still closed (do not regress)

N1–N4 · D1 (F1 exact blend=0) · D3 (F5/F6/F7) · D4 (F9/F11/F12) on validator path. D3(i)(ii)(iii) still PASS. Append-only + prediction identity preserved.

## Residuals (NON_BLOCKING)

R1/F8 D3(i) oracle · R2/F10 DDL owner lock (not applied) · R8 as_of second-grain vs timestamptz microsecond · created_at/schema_version defaults

## Tests

```bash
cd services/model-service
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py tests/test_nfl_handicap_clear_a_d1_d4_remotion.py tests/test_nfl_handicap_clear_a_n1_n4_remotion.py tests/test_nfl_handicap_clear_a_r7.py -q
```

**26 passed** (5 D3 + 10 D1–D4 remotion + 5 N1–N4 + 6 R7).

D3(ii) pin unchanged: `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`

## Hard stops

No capture · no overlay ON · no infra/db apply · no live caller wiring · no merge · no deploy.

## Next

Stop for Codex challenge + IMV grade of the new sealed tip. **Do not merge.**
