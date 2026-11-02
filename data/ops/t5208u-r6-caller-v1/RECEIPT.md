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
- packet_hash: `ee71ffc65200e8ebbd59d9447bbede20b9cbab015af7deb5748bfc35b62efee8`
- history_hash: `d194de4508a30a2baa09c2c7d96f8ee26d74bd0b22587430d4d936de4fd897e8`
- config_hash: `01d61811a922f75701b080a57d00f6e0feea7e87cbe016c9e4d26903183cee29`
- code_hash: `9abbe1b74c31aca66be69dffb0782867600476e5229b4b5e3008e1c1548745fd`
- cutoff/seal: `2018-10-14T16:00:00Z` / `2018-10-14T17:00:00Z`
- t5213u 79264: cells+metadata+identity validated BEFORE IF; binds are actual hashes (not schema_hash).

B: use `data/ops/t5213u-r6-pure-function/` actual binds + cutoff; import `call_r6_point_margin`; do not fabricate IF means; real-mode refuse; CERT=0 DRAFT only. No operational acceptance from prior t5208 counts.
