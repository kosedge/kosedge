# t5178u M0 tip receipt (Worker A) — Cos steer attach-path

- stamp: M0_BIND_t5178u
- worker_branch: `cursor/t5178u-wfix-a-fixture-assembly-c003`
- base_sha: `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f`
- `#664` tip: **Git commit** `7abf65a2c85708cc6d4a1cd2b4d9643a4612084a`
- attach: path-checkout of `nfl_hhl1_capture/*` + plumbing test only; blobs match `7abf65a2`
- ONE_RUN bind `4eef5d1f` CONSUMED · receipt `9a72c55b` PRESERVE · token `4fa6d856` never reset
- contract_id: `t5178u-nfl-fixture-assembly-v0`
- B wiring: `data/ops/t5178u-m0-attach-path-for-b.md`
- B inventory: #706 confirmed absence on `f5e3bb58` — accepted; attach is this Git checkout, not a helper
- CERT=0 · DRAFT · IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED

M0 tip SHA = this commit. Worker B / Cos: consume contract + attach-path; do not reopen R5.
