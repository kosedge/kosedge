# nfl_owned_market_v1 RECEIPT (Worker B)

CERT=0. IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED. Isolated package only.
A registers the two profiles. B does not touch the shared evidence gate.

| field | value |
|---|---|
| ticket | t5289u |
| owner_clear | 86257 |
| worker | B · `bc-02a716be-429a-56c8-ab0f-5f262aa479df` |
| scope | chief-nflgreen-model-day-20261103-1700 |
| plan_fingerprint | b15d6cec143212067b896057a048cd51071981d6ea1b3561c08db89cb6355358 |
| branch | cursor/nfl-owned-market-v1-79df |
| start_HEAD | f5e3bb58ccbe5a8892fed2a01f347c2308394a2f |
| preflight | `data/ops/nfl_owned_market_v1/START_PREFLIGHT_B.md` |
| preflight_sha256 | f4636f88f982fe5232b0179187e562182fa292a96dec11f1e889fcba3eb84229 |
| tests | `PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q` · 15 passed |
| produce | `PYTHONPATH=services/model-service python3 -m src.services.nfl_owned_market_v1.run` · EXIT 0 |
| code_hash | f3e6f54f8d15c47f4a240c19cd15a2bf7a06d73daf23c19aaa7d33e66a3ed7aa |
| ready_for_A | true |
| ready_for_review | false |
| self_accept | false |

See `HANDOFF_INTERFACE.md` for profile names, schemas, and fixture hashes.
