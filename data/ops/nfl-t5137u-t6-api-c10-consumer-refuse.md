# t5137u addendum — T6-API-C10-CONSUMER-REFUSE

Authority: OWNER CLEAR t5136u **a5f7c364** §7 · t5137u **574dde7f** · COS_ORDER sha8 **6407ff19**
CERT=0 · DRAFT≠merge · no deploy · no EVAL · no G5 · no #6 PASS claim

Institutional memory: **no prior grades** (engineering fail-closed check; not a recurring desk product).

## Chosen check

| Field           | Value                                                                                                                                               |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Check id        | `T6-API-C10-CONSUMER-REFUSE`                                                                                                                        |
| Map             | NFL GREEN eight-target **#6** (fail closed on missing/invalid data) + ACCESS_MATRIX **G1** consumer APIs + **E1 FAIL_CLOSED** C10/model unreachable |
| Classification  | **EXISTING BUT UNVERIFIED**                                                                                                                         |
| Preference rank | (1) consumer refuse when C10/model API unreachable                                                                                                  |
| Surfaces        | `GET /api/nfl/fair-lines` · `GET /api/nfl/edges-desk` · `GET /api/edge-board/nfl/assemble?slate=week1`                                              |
| Policy reused   | `throwOnTransportError` + `pageDataUpstreamErrorResponse` (503/504, no invented `lines`/`rows`/`count`, `private,no-store`)                         |
| Fixtures reused | G1 `getProAccessState` mock · `PAGE_DATA_NO_STORE` · helper contract from `nfl-page-data-timeout.test.ts`                                           |

## Preflight inventory (API / export / cache only)

| Check id                                                       | Class                               | Why                                                                                                                                                  |
| -------------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1-A4 cache Control (`private,no-store` / no cross-user share) | EXISTING AND VERIFIED               | Sealed #676 merge `29b536b1`; `pro-gated-access-cache.test.ts` A4/A6. **Skipped** (preference 3; already PASS).                                      |
| `#6.1` INPUTS_INCOMPLETE / `#6.3` pin+asof                     | EXISTING AND VERIFIED               | Diagnostic IF packet (#667). Not API/export/cache. **Skipped**.                                                                                      |
| `#6.4` IF+HL+market E2E                                        | SUPERSEDED / HOLD                   | HL/Odds HOLD; COND. Out.                                                                                                                             |
| Assemble missing governed full snapshot                        | EXISTING AND VERIFIED               | `nfl-edge-board-assemble-window.test.ts` (no invent). **Skipped**.                                                                                   |
| Page-data helper 503/504                                       | EXISTING AND VERIFIED (helper only) | `nfl-page-data-timeout.test.ts` maps helper + `fetchNflFairLines`; does **not** call route GET with C10 down. FB-kill short-circuits G1 route tests. |
| Export KEI C10 refuse (`export_kei_lines_nfl.py` exit 1)       | EXISTING BUT UNVERIFIED             | Impl exists; no test. **Not picked** (preference 2).                                                                                                 |
| Export/schedules missing → refuse invent                       | EXISTING AND VERIFIED / mixed       | Slate cards keep schedule identity + em-dash KEI (`nfl-slate-schedule-fallback.test.ts`). Not C10 consumer refuse.                                   |
| `T6-API-C10-CONSUMER-REFUSE`                                   | **EXISTING BUT UNVERIFIED**         | Impl on the three page-data routes; **no** sealed route-level C10-unreachable assertion (FB-kill 503 is a different gate). **Picked.**               |

## Evidence this DRAFT adds

- `apps/web/__tests__/api/nfl-c10-consumer-refuse.test.ts`
  - FB-kill / cert-surface mocked **off** so the C10 path runs.
  - Authorized GET + mocked unreachable C10 → **503**, no invented slate fields, dual `private,no-store`.
  - Timeout → **504**.
  - Mutation oracle: routes still contain `throwOnTransportError: true` + `pageDataUpstreamErrorResponse`.
- No production route/policy/threshold change. No Odds live HTTP. No env secret reads.

## Tests run (offline, no Odds HTTP)

```
vitest run __tests__/api/nfl-c10-consumer-refuse.test.ts \
  __tests__/lib/nfl-page-data-timeout.test.ts \
  __tests__/api/pro-gated-access-cache.test.ts
# Test Files  3 passed (3)
# Tests      14 passed (14)  — new file 5/5
```

## Holds

Do **not** relabel eight-target #6 PASS. Independent RO next. CERT=0.
