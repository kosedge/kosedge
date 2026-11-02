# t5178u M0 — ONE shared typed contract

SoT: `services/model-service/src/services/nfl_fixture_assembly/contract.py`
TS mirror (W-FIX-B): `apps/web/lib/nfl-fixture-assembly-contract.ts`

CERT=0 · OPT-IN · INTERNAL · FIXTURE-ONLY · IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED

## Envelope (forecast + provenance + capability)

```
FixtureEnvelope
  channel: "FIXTURE"                 # only legal channel
  fixture: true
  production_mode: false             # hard refuse if true
  honor_env_bypass: false            # hard refuse if true
  cacheable: false                   # hard refuse if true (page-data private,no-store)
  requested_output: RequestedOutput
  forecast: ForecastRecord
  provenance: ProvenanceRecord
  capability: CapabilityRecord
  l1_candidate: mapping              # #664 L1 row; no market_* fields
  quote_spec: SyntheticQuoteSpec     # exact book/event/side/period/line/price/time
```

### ForecastRecord
- `forecast_id` (sha256 hex)
- `game_id`
- `period` (`full_game` only in this package)
- `side` (`HOME` | `AWAY`)
- `point_margin` (home − away; finite number)
- totals / ml / cover_prob / economic fields **absent**

### ProvenanceRecord
- `source_id`, `source_url`, `source_snapshot_id` (sha256)
- `parser_version`, `protocol_sha`, `schema_version`
- `source_published_at`, `captured_at`, `decision_ts`, `kickoff_ts`, `as_of_ts` (UTC Z)

### CapabilityRecord
- `bits`: frozenset of `POINT_MARGIN` | `JOINT_SCORE`
- Point-margin vs joint-score is a **declared bit**, not a joint spread/total/ML law
- This package **does not compute** joint-score (no scientific EXEC)

## Capability vs requested output

| Input capability | Requested output | Result |
|---|---|---|
| `POINT_MARGIN` | `POINT_MARGIN_SPREAD` | may proceed (fixture channel) |
| `POINT_MARGIN` | `TOTAL` | **hard refuse** `REFUSE_TOTALS` — no partial object |
| `POINT_MARGIN` | `MONEYLINE` | **hard refuse** `REFUSE_MONEYLINE` |
| `POINT_MARGIN` | `COVER_PROBABILITY` | **hard refuse** `REFUSE_COVER_PROBABILITY` |
| `POINT_MARGIN` | `ECONOMIC_ELIGIBILITY` | **hard refuse** `REFUSE_ECONOMIC_ELIGIBILITY` |
| `JOINT_SCORE` set | any total/ML/prob | **hard refuse** `REFUSE_QUALIFICATION` (bit declared; production not authorized) |

## Synthetic quote (transport only)

```
SyntheticQuote
  book, event_id, side, period, line, price, time
  fixture: true
  transport_only: true
  injury_policy_approved: false
```

Quote is **not** attached onto the L1 row (would trip `reject_market_fields`: `price` / `odds` / `spread_line`).

Sign convention: `home_spread = -point_margin`. HOME quote.line must equal `home_spread`; AWAY quote.line must equal `point_margin`.

Synthetic **adjusted** raw/multipliers prove transport through `#664` validation only. **Not** an approved injury policy.

## ONE eligibility / refusal enum

`FixtureEligibilityResult`

- `ALLOW_FIXTURE` — fixture-channel-only (Alex X1). Never subscriber / betting / production / honesty-board.
- Faults: `REFUSE_IDENTITY` `REFUSE_HASH` `REFUSE_VERSION` `REFUSE_GAME` `REFUSE_PERIOD` `REFUSE_LINE` `REFUSE_SIGN` `REFUSE_TIME` `REFUSE_CUTOFF` `REFUSE_CAPABILITY` `REFUSE_QUALIFICATION` `REFUSE_MISSING` `REFUSE_STALE` `REFUSE_PARTIAL` `REFUSE_CACHE` `REFUSE_TOTALS` `REFUSE_MONEYLINE` `REFUSE_COVER_PROBABILITY` `REFUSE_ECONOMIC_ELIGIBILITY` `REFUSE_PRODUCTION_CHANNEL` `REFUSE_ENV_BYPASS` `REFUSE_MARKET_FIELDS` `REFUSE_VALIDATION`

`ALLOW_FIXTURE` payload always:

```
fixture: true
subscriber_consumable: false
betting_consumable: false
production_consumable: false
env_bypass_honored: false
cacheable: false
```

Env (`NFL_EDGE_BOARD_INTERNAL`, public flags, `HHL1_*`) **cannot** upgrade `ALLOW_FIXTURE` to a production allow.

## Assembly sequence (W-FIX-A)

1. Channel / production / env-bypass / cache gates
2. Capability vs requested output (typed hard refuse; no partial)
3. Cross-checks: identity / hash / version / game / period / line / sign / time / cutoff
4. `#664` `validate_l1_candidate` / `validate_l1_batch` / `reject_market_fields`
5. Emit synthetic quote + ONE eligibility result

No simulator / `produce_mu` / forecast loader / result-loader / network / DB / jobs.
No mutation of pinned artifacts. Synthetic inputs / temp outputs only.
