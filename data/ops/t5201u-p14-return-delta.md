# t5201u P14 RETURN_DELTA (CERT=0)

Digest bind after `produce_fixture_chain`: `digest == EXPECTED_DIGEST == pinned`
else `PRODUCED_DIGEST_MISMATCH` exit 2 before consume.

Node/vitest leg (`T5201U_CHAIN_JSON`): wraps fetch / net.connect /
Socket.connect / dns.lookup / http(s).request / DB imports. Prints
`ts_forbidden_call_attempts N`. Parent refuses unless N==0 and folds into
`forbidden_call_attempts`. `--probe-ts-forbidden` is the negative TS probe.

```
PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py
PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py --probe-forbidden
PYTHONPATH=services/model-service python3 scripts/nfl/t5194u-ab-chain.py --probe-ts-forbidden
```
