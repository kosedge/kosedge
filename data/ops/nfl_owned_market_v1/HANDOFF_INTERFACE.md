# Worker B → Worker A hand-off (RETURN 47318)

CERT=0. Isolated `nfl_owned_market_v1`. B does **not** register.
Preserves prior Cos ACCEPT `5c86d228` / handoff `5b7ee2e4` as engineering base.

Machine copy: `data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json`
(`sha256=c2e717fbe60a93b09973e9cc9ff549d0aff057a200debd97db2f4c5adc7753a8`).

## Profile names (separate roles)

| profile | role | producer | validator |
|---|---|---|---|
| `OWNED_MARKET_TRACE_V1` | **OWNED_READINESS** | `owned_readiness:build_owned_readiness_document` | `validate_owned_market_trace` |
| `SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1` | **FICTIONAL_ECONOMIC** | `produce:build_events_document` | `validate_synthetic_market_economic_events` |

`validate_join` keeps them separate (`joined=false`, `owned_completion_claimed=false`).
Do not treat risk1 tickets as owned-source completion.

## Schemas / fixtures

| profile | schema_hash | fixture_sha256 | document_hash |
|---|---|---|---|
| OWNED_MARKET_TRACE_V1 | `122053db82d465c5a7be30ca19e3dd9dbcae09229edaeb758450ce8f5fa4a643` | `e9d92dac09de61401da4e6d707d8b4e32fa22059bfe5179dc261359adeb1732c` | `3cb74f833d85a49547decba5a49e891ce13fee3f767ba81627d5d65a59ff962b` |
| SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 | `86069d05211bfe8e57de14fd48a0de5fec30a9f937c618b398ee17490c0d9cfe` | `ca25354581ae94d87d7bc09aece6829711da6bbe8fd15414e6856e100d5f4b2e` | `2eac30395dad758b0194d361fdb363147e36b38c0927e8b90667cb4d1237937e` |

Owned fixture: `fixtures/owned_market_trace.readiness.json` (`OWNED_SOURCE_UNAVAILABLE`).
Economic fixture: `fixtures/synthetic_market_economic_events.risk1.json` (risk1 ATS/ROI/line-CLV).

## 86257 arithmetic (economic only)

Exact copies of desk-record American profit, book_ledger ATS, nfl_clv_semantics line-CLV.
risk1_u=1. Push/void excluded from ROI risked. Missing juice → refuse (no flat −110).

## Owned 187/400/clock

See `OWNED_187_400_CLOCK_UNAVAILABLE.md`. All three required SoT paths UNAVAILABLE on this VM.
