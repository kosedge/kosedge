# Worker B → Worker A hand-off (DELTA 58426 / RETURN 47318)

CERT=0. Isolated `nfl_owned_market_v1`. B does **not** register.
Preserves Cos ACCEPT `ff45970b` @ `9ce485e9` (risk1 ATS/ROI/CLV + profile split + no outcome join).

Machine copy: `data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json`
(`sha256=9b190d38e11ebaebe53cfb46047c19f2f3abf3f5f8f51fecd2a3c470568f33b4`).

| profile | role | fixture_sha256 | schema_hash |
|---|---|---|---|
| OWNED_MARKET_TRACE_V1 | OWNED_READINESS · `OWNED_IDENTITIES_PROJECTED` | `f38418cd4ab2e02738717b4ce23ad341209dc956b7604aa4eb0e1d2f93c2278c` | `f972f0fa34a7c91536208ddace21c5cdd94383c7a8990ae8736003d8479964a7` |
| SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 | FICTIONAL_ECONOMIC (unchanged risk1) | `ca25354581ae94d87d7bc09aece6829711da6bbe8fd15414e6856e100d5f4b2e` | `86069d05211bfe8e57de14fd48a0de5fec30a9f937c618b398ee17490c0d9cfe` |

document_hash owned `c223b5db67921d55429660f17675655a445c9f9d857ab0e71563ee77ba654aea` ·
econ `2eac30395dad758b0194d361fdb363147e36b38c0927e8b90667cb4d1237937e`.

History restore + locators: `OWNED_187_400_CLOCK_UNAVAILABLE.md`.
Remaining blocker: original freeze clock timestamps **unverified** (not invented).
