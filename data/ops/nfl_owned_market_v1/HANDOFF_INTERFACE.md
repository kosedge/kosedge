# Worker B → Worker A hand-off

CERT=0. Isolated `nfl_owned_market_v1`. B does **not** register these
profiles. A (`R7_CORRECTNESS_V1`) is the sole shared-gate registrar.

Machine copy: `data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json`
(`sha256=5b7ee2e4fb849e1bcaf7d09f888d2e61ff6f9993550727f66b66d0126545b553`).

## Profile names

| profile | schema_version | producer | validator |
|---|---|---|---|
| `OWNED_MARKET_TRACE_V1` | `owned-market-trace-v1` | `src.services.nfl_owned_market_v1.produce:build_trace_document` | `src.services.nfl_owned_market_v1.validate:validate_owned_market_trace` |
| `SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1` | `synthetic-market-economic-events-v1` | `src.services.nfl_owned_market_v1.produce:build_events_document` | `src.services.nfl_owned_market_v1.validate:validate_synthetic_market_economic_events` |

Join (not a third profile): `src.services.nfl_owned_market_v1.validate:validate_join`.

## Schemas

| profile | path | schema_hash (canonical body) | schema_sha256 (on-disk bytes) |
|---|---|---|---|
| OWNED_MARKET_TRACE_V1 | `data/ops/nfl_owned_market_v1/schemas/OWNED_MARKET_TRACE_V1.schema.json` | `cd564061cb12a45b0cf813d3e23b6e1166e3fefb77d6b3525e6a997a819dfc57` | `680a4c9756cab6d3055ee91ce70769f846305470cf450e38b6ceab2f58761e4e` |
| SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 | `data/ops/nfl_owned_market_v1/schemas/SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1.schema.json` | `326c18108d90ce4b2de5cbbfdb499274abe2aca37baf7a2046a91aa24e3ac021` | `a06b15d1507a44ddd0306f3b22314c89ce9a82c9c56996e8e34101862e670e55` |

## Fixture hashes

| profile | path | document_hash (canonical, hash field stripped) | fixture_sha256 (on-disk bytes) |
|---|---|---|---|
| OWNED_MARKET_TRACE_V1 | `data/ops/nfl_owned_market_v1/fixtures/owned_market_trace.synthetic.json` | `dda58e0bccc509784cb32326f679463c58db8f203c104a1d635c2ceb7f460d59` | `7e412d1f701929ae963ff0d50d2ee11af93a9b928f14d770e46b310e20da9a4b` |
| SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 | `data/ops/nfl_owned_market_v1/fixtures/synthetic_market_economic_events.synthetic.json` | `ab6e0f4ec87a109dee07024ae186c252e6a6643b09fa9ec3538858e283341efd` | `37b21de21c6bb68493b87b8ac908c89f2cf0ebe03ec996d867646386957eb87f` |

`document_hash` = sha256 of canonical JSON with `source_byte_hash` removed.
`fixture_sha256` / `schema_sha256` = sha256 of on-disk bytes (indent=2,
sort_keys, trailing newline).

## Join contract

- Shared `envelope.game_id` = `SYNTHETIC_2026_99_AAA_ZZZ`
- Shared timing: `seal_utc = cutoff_utc = kickoff-60` (`2026-12-06T17:00:00Z`)
- `observations[].caused_by_event_id` → `events[].event_id` when set
- Bound event `available_at` must strictly precede the observation
- Both sides strictly precede seal (cutoff-1s valid; exact seal / +1s refuse)
- Book id is `OWNED_SYNTH_BOOK` only (real books refuse)
- No `play` / `lean` / `stake` / `clv` / `edge` keys

## How A should consume

```text
PYTHONPATH=services/model-service python3 -m src.services.nfl_owned_market_v1.run --repo-root .
```

Or import validators and fixtures; do not copy schemas by hand. Register
the two profile names above on `R7_CORRECTNESS_V1` only from Worker A.

## Pins B consumed (not a base merge)

| pin | full sha |
|---|---|
| R6 A | `54b08a301cf824c79ee3203180a51e2d832bb6f9` |
| R6 B | `afb13301b5c7e3b8780a8dd1f85145e91bebef55` |
| #713 gate tip | `679dbdaf8c9044edffb34ffca1543c33eea77db7` |
| #714 PARTIAL (not a base) | `5558890b5f8a66c16c658fce2971f0a7e2f2c7de` |
| this branch start | `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f` |

Package `code_hash` (isolated bind files):
`f3e6f54f8d15c47f4a240c19cd15a2bf7a06d73daf23c19aaa7d33e66a3ed7aa`.
