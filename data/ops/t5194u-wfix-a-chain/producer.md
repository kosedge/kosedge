# t5194u A→B chain producer (Worker A)

CERT=0 · DRAFT · B consumes this JSON. Do not rewrite `data/ops/t5178u-wfix-a/`.

## Command B should run / pin against

From `services/model-service`:

```
PYTHONPATH=. python3 -m src.services.nfl_fixture_assembly.produce_chain \
  --out data/ops/t5194u-wfix-a-chain/positive-output.json
```

This repo-root equivalent:

```
cd services/model-service && PYTHONPATH=. python3 -m src.services.nfl_fixture_assembly.produce_chain \
  --out ../../data/ops/t5194u-wfix-a-chain/positive-output.json
```

## Artifacts

| File | Role |
|---|---|
| `positive-input.json` | producer knobs (synthetic) |
| `positive-output.json` | full chain record (candidate/game/forecast/provenance/cutoff/capability) |
| `positive-output.sha256` | `sha256(canonical_json(payload))` |

Shared contract: `CHAIN_CONTRACT_ID=t5194u-nfl-fixture-chain-v1` in
`services/model-service/src/services/nfl_fixture_assembly/contract.py` and
`apps/web/lib/nfl-fixture-assembly-contract.ts`.

Python consume (A): `consume_fixture_eligibility` — exact contract_id / schema_version / channel / fixture + explicit false flags before normalize.

TS consume (B lane): implement the same exact-field gate. Do not accept bare `{result:ALLOW_FIXTURE}` and do not rewrite `fixture=false` / `PRODUCTION` / wrong `contract_id`.

## Guard (t5194u P14 RETURN_DELTA)

Shared helper B should import (do not reimplement):

```
from src.services.nfl_fixture_assembly.guard import last_guard_report, guard_active
```

After produce, assert `last_guard_report()["guard_active"] is True`.
Stdout now includes `guard_active true` (not only `forbidden_call_attempts 0`).
Chain JSON digest is unchanged (guard is not added to the payload).
