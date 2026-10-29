# HANDICAP CLEAR-A evidence packet (t4740u) — remotion v3 N1–N4

**Status:** DRAFT PR only · not merged · not deployed  
**Authority:** COS_ORDER_CURSOR_t4740u v3 · DECISION d744fa87 · IMV RETURN **dafa4f94** · Codex deltas **5cc4fcc1**  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF

CoS seal destination after this tip: `ops/nfl_enterprise_green_t4359u/` (not written here).

## Identity

| Field | Value |
|---|---|
| Branch | `cursor/handicap-clear-a-if-ledger-ed4b` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| Parent tip | `10fe917534254b94307dcbb1b47ffa250cde5c9e` |
| Remotion v3 SHA | `39a640aedeadb5e79eb1bd11d17e028a77959461` |
| Sealed tip | stamp commit on this branch (parent remotion `39a640ae`); confirm `git rev-parse HEAD` / PR `headRefOid` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 |

## Closed this remotion (N1–N4)

| Item | Close |
|---|---|
| N1 | `append` / `append_many` run `validate_envelope` (layer/label + aware ts + validate_l0/l1/l4 + re-derive). Envelope L1/HF/naive/empty REJECT; L0 payload `market_blend=0.3` REJECT. |
| N2 | `append_many` checks intra-batch prediction_id and business identity before any write. `[e,e]` REJECT, len unchanged. |
| N3 | `as_of_ts` canonicalized to UTC `YYYY-MM-DDTHH:MM:SSZ` before identity/id. Z / `+00:00` / `-04:00` same instant share one id; 2nd+3rd REJECT. |
| N4 | JSONL load re-validates layer + re-derives `prediction_id`; forged id REJECT. |

## Still closed (do not regress)

D1 (F1 exact blend=0) · D3 (F5/F6/F7) · D4 (F9/F11/F12) on validator path. D3(i)(ii)(iii) still PASS.

## Residuals (NON_BLOCKING)

R1/F8 D3(i) oracle · R2/F10 DDL owner lock (not applied) · created_at/schema_version defaults

## Tests

```bash
cd services/model-service
python3 -m pytest tests/test_nfl_handicap_clear_a_d3.py tests/test_nfl_handicap_clear_a_d1_d4_remotion.py tests/test_nfl_handicap_clear_a_n1_n4_remotion.py -q
```

**20 passed** (5 D3 + 10 D1–D4 remotion + 5 N1–N4).

D3(ii) pin unchanged: `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`

## Hard stops

No capture · no overlay ON · no infra/db apply · no live caller wiring · no merge · no deploy.

## Next

Stop for Codex deltas + IMV re-grade. **Do not merge.**
