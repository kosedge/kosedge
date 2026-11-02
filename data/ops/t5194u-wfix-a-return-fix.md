# t5194u W-FIX RETURN-FIX (Worker A) — demonstrated scope

- tip parent: `07308512` (#707)
- OWNER CLEAR `e1fac795` · Cos LAUNCH `28c0d717`
- CERT=0 · DRAFT · IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED
- Prior t5178u artifacts **PRESERVED** (not rewritten)

## Commands / results

```
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_fixture_assembly_wfix_a.py \
  tests/test_nfl_fixture_assembly_t5194u_return_fix.py \
  tests/test_nfl_hhl1_capture_plumbing.py --tb=short
```

**130 passed in 0.25s**

```
cd services/model-service
PYTHONPATH=. python3 -m src.services.nfl_fixture_assembly.produce_chain \
  --out ../../data/ops/t5194u-wfix-a-chain/positive-output.json
```

digest `27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124`  
`forbidden_call_attempts 0`

## Demonstrated (A)

1. `_finite_number` rejects ±Infinity, NaN, bools, and non-numbers. Full assembly refuses nonfinite forecast margin and quote line while leaving canonical capture/forecast identity untouched. Invalid American prices (0, |p|<100, bool, float) refuse `REFUSE_LINE`. No cutoff/math change.
2. `consume_fixture_eligibility` requires exact `contract_id` / `schema_version` / `channel=FIXTURE` / `fixture===true` and explicit boolean-false production/cache/bypass flags **before** normalize. Bare `{result:ALLOW_FIXTURE}`, `fixture=false`, `PRODUCTION`, wrong `contract_id`, missing version, non-boolean flags refuse. Positive original fixture controls still pass.
3. Additive chain `t5194u-nfl-fixture-chain-v1` serializes candidate/game/forecast/provenance/cutoff/capability. Faults refuse before dest exists; existing OUT bytes preserved.

## Untested / not claimed

- Worker B TS `consumeFixtureEligibility` exact-field rewrite (B lane)
- B API/VM/export/cache consumers of this chain (B lane)
- Live/API/DB/network/simulator/outcome
- Merge/deploy / CERT / all-eight PASS
