# t5208u R6_CALLER_V1 A receipt (CERT=0)

Worker A pure caller. Not integration owner. IMPLEMENTED≠VERIFIED≠ACCEPTED. No merge.

- schema_id: `nfl-t5208u-r6-caller-v1`
- schema_hash: `ce3747cc7d5368dfbb60ebfa4fff87ae52890afd60ba3b596bc5baa5849e50d8`
- CONTRACT_27 n=27 frozen from recon_contract.py@455a8e43
- IF tree: `/workspace/services/model-service` status=PRESENT_PIN_MATCH
- sim_sha256: `52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385`
- fw_sha256: `a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3`
- DEFAULT_IF_TREES used: `False` (ABSENT mounts; not created)
- IF: `0.8675824382397918`  Q2: `1.2472862060776504`  C: `1.057434322158721`
- seed: `282632` simulations=4000 replay_ok=True
- formula: `C=0.5*IF+0.5*Q2`

B: use `synthetic_demo.json` + `demo_result.json`; import `call_r6_point_margin`; do not fabricate IF means; real-mode refuse; CERT=0 DRAFT only.
