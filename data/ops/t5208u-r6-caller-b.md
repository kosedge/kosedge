# t5208u R6_CALLER_V1 B — offline manifest/caller/ledger (CERT=0)

OWNER CLEAR 84308754 · Cos LAUNCH a0a88a33 · Cos ACCEPT A ec40cda9.
Preserve package 8f3c5580. Algorithm pins from 455a8e43. POINT_MARGIN only.
No W-FIX transport reopen. No science EXEC. No fabricated IF mean.

## INTEGRATE (A 1487e9f0)

A artifacts checked out onto this #708 branch (byte-identical to 1487e9f0):
- `data/ops/t5208u-r6-caller-v1/demo_result.json` (IF/C means — consumed)
- `data/ops/t5208u-r6-caller-v1/synthetic_demo.json` (packet/history only; remaps to demo_result)
- API bind: `from src.services.nfl_t5208u.caller import call_r6_point_margin` (imported, not invoked)

```
T5208U_A_SYNTHETIC_JSON=data/ops/t5208u-r6-caller-v1/demo_result.json \
PYTHONPATH=services/model-service python3 scripts/nfl/t5208u-r6-caller-e2e.py
# EXIT 0
```

```
package t5208u-r6-caller-v1
algorithm_tip 455a8e43eccc1ed2c39e91821790cce968ffdadb
if_tip 6ca03716fe52930332d5ffba302c312a651980cc
c_formula 0.5*IF+0.5*Q2
output_kind POINT_MARGIN
real_mode_authorized false
REAL_MODE_REFUSED REFUSE_REAL_MODE
DUP_REFUSED REFUSE_DUPLICATE
RACE_REFUSED REFUSE_RACE
PARTIAL_WRITE_REFUSED REFUSE_PARTIAL
LEFTOVER_TMP_REFUSED REFUSE_PARTIAL
a_path data/ops/t5208u-r6-caller-v1/demo_result.json
a_api call_r6_point_margin
a_tip 1487e9f0195132916d9a6742d9d36d1493610e9d
means_source A demo_result.json artifact only
sealed_n 1
seal SYNTHETIC_2018_W05_KC_NE if=0.8675824382397918 q2=1.2472862060776504 c=1.057434322158721 seed=282632 id=cc63fb5b9106f2797a4f296d5ece0dc84fe722bf68197f71a8e2fff5a4733541
INTEGRATION OK
OK
```

IF/Q2/C/seed copied from A's `demo_result.json` only (schema_hash ce3747cc).
C check 0.5*IF+0.5*Q2 = 1.057434322158721. `call_r6_point_margin` was not invoked.

## Hashes

| item | sha256 / id |
| --- | --- |
| A demo_result.json | e00de4a560bf82524072f4cb11c2c76df959b2584b6e0c09a481209897e71ba0 |
| A synthetic_demo.json | 349779164a23374991bb89a3f28a60ab4882c12a785eff162c87e62043b2b97a |
| A schema_hash | ce3747cc7d5368dfbb60ebfa4fff87ae52890afd60ba3b596bc5baa5849e50d8 |
| paired-arm seal_id | cc63fb5b9106f2797a4f296d5ece0dc84fe722bf68197f71a8e2fff5a4733541 |

Real mode is not authorized by this CLEAR. CERT=0 DRAFT. No merge. No Alex start from B.
