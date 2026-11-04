# t5289u Worker A interface stub — shared evidence-gate profiles

CERT=0 · DRAFT · Worker A is the sole registrar.

## Profiles

| profile | owner | status at stub | registrar |
|---|---|---|---|
| `SYNTHETIC_WFIX_AB_CHAIN` | Primary A (#713) | ACTIVE (narrow reuse `679dbdaf`) | lineage |
| `R7_CORRECTNESS_V1` | Worker A | ACTIVE | `bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8` |
| `OWNED_MARKET_TRACE_V1` | Worker B | REGISTERED after Cos ACCEPT `5c86d228` | Worker A only |
| `SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1` | Worker B | REGISTERED after Cos ACCEPT `5c86d228` | Worker A only |

## B handoff (consumed, not invented)

- tip `f6566c9271ae16e53f67d08555814c4df94fe751`
- DRAFT PR https://github.com/kosedge/kosedge/pull/715
- `data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json`
- sha256 `5b7ee2e4fb849e1bcaf7d09f888d2e61ff6f9993550727f66b66d0126545b553`

Validators **imported**, not copied:

- `validate_owned_market_trace`
- `validate_synthetic_market_economic_events`
- `validate_join`

B isolated area stays `nfl_owned_market_v1`. A does not widen B ownership. B does not self-register. No global real-mode widening.

## Cos pins bound on registration

| profile | schema_hash | document_hash | fixture |
|---|---|---|---|
| OWNED_MARKET_TRACE_V1 | `cd564061…819dfc57` | `dda58e0b…7f460d59` | `7e412d1f…20da9a4b` |
| SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 | `326c1810…3e3ac021` | `ab6e0f4e…83341efd` | `37b21de2…957eb87f` |

## R7 core (does not stall on B)

Opt-in synthetic IF/Q2 producer → shared evidence gate (`R7_CORRECTNESS_V1`) → paired recorder.

- `REST_ACTUAL_ET_CALENDAR_V1`
- franchise key
- config bind
- frozen IF/sim/framework pins
- R6 A `54b08a30…` · R6 B `afb13301…` · #713 `679dbdaf…`
- #714 stays PARTIAL / not wholesale base
