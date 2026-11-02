# t5194u P14 RETURN_DELTA — real forbidden-call guard (A)

- parent tip: `cd0ecbd2`
- OWNER `e1fac795` · P14 `0470ad38`
- CERT=0 · DRAFT · IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED
- Prior chain digest PRESERVED: `27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124`

## Guard

`src.services.nfl_fixture_assembly.guard` installs while `produce_chain` / assemble runs:

1. `sys.meta_path` finder → `forbidden_import_names()`
2. `socket.socket.connect` + `socket.getaddrinfo`
3. wrap loaded `forbidden_name_tokens()` symbols

Attempts route to `note_forbidden_call`.

B helper (do not reimplement):

```
from src.services.nfl_fixture_assembly.guard import last_guard_report
# after produce_fixture_chain / produce_chain
assert last_guard_report()["guard_active"] is True
```

## Commands / results

```
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_fixture_assembly_t5194u_guard.py \
  tests/test_nfl_fixture_assembly_t5194u_return_fix.py \
  tests/test_nfl_fixture_assembly_wfix_a.py \
  tests/test_nfl_hhl1_capture_plumbing.py --tb=short
```

**134 passed in 0.28s**

```
PYTHONPATH=. python3 -m src.services.nfl_fixture_assembly.produce_chain \
  --out /tmp/t5194u-guard-check.json
```

```
digest 27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124
guard_active true
forbidden_call_attempts 0
```

Negative: real `import src.services.nfl_simulator` + `socket.connect` / `getaddrinfo` under the chain guard → count > 0 and refuse. Simulator module never loaded.

## Untested / not this tip

B `scripts/nfl/t5194u-ab-chain.py` guard_active assert (B lane). Live/network/DB. Merge/deploy.
