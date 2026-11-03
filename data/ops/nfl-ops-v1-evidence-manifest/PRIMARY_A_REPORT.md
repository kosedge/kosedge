# Primary A — NFL_OPS_V1 evidence-manifest gate

CERT=0 · SYNTHETIC_ONLY · DRAFT · not self-accepted · not READY_FOR_REVIEW

## Identity

| Field | Value |
|---|---|
| scope_id | `chief-nflgreen-overnight-ops-20261102-0330` |
| owner_clear | `f1fb6735` |
| protocol | NFL_OPS_V1 `ed10e80f` |
| role | Primary A · heavy builder #1 · integration-side evidence gate |
| bc_id | `bc-aeae1f9f-5b28-5b1f-b88a-3afdb10513a1` |
| branch | `cursor/nfl-ops-v1-evidence-manifest-gate-13a1` |
| base | `deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f` |
| status | `GATED_OK_AWAITING_CHIEF` (passing tests ≠ acceptance) |

## Disk at start (workspace volume)

```
df -B1 /agent/repos/kosedge
Filesystem        1B-blocks       Used    Available Use% Mounted on
/dev/vdc       271966244864 8511991808 263437475840   4% /
```

`bytes_avail=263437475840` (~245.4 GiB). Cos-box `/dev/vdb` DISK-1 is not this volume.

## What landed

ONE versioned executable evidence-manifest gate on the **actual** accepted W-FIX produce→consume path (`produce_fixture_chain` → `gate_before_consume` → `consume_fixture_chain` → `gate_before_final_receipt`). Not a dashboard. Not an import-only demo. Not a saved-output replay.

Reuse (utilities only; inherited real-outcome tests **NOT_RUN**):

- #700 tip `9d436eb1` — `sha256_text` / `hash_file_list` / `require_finite` / `OutcomeReadSpy`
- #701 tip `455a8e43` — same verify_integrate helpers
- #707 tip `f2c72e8b` — accepted produce/guard/synth/hhl1 lineage
- #706 tip `644c517d` (`12bc48c0` pin) — `consume_chain` + digest bind `27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124`

`worker_handoff` is bound from Primary B DRAFT #712 tip `82683cd93ec2c231733f34b5c0372cf1d42fa68a` via `as_worker_handoff()` + `THIS_WORKER_HANDOFF.json` (content_hash `b8aa6100…`). `PLATFORM_LIMITATION` / `not_a_pass=true` / `mocked_release=false` / capability `ABSENT` preserved. SLOT_RESERVED is now an invented substitute. Mocked reclaim is not PASS.

## Exact test commands

```
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_ops_v1_evidence_manifest_gate.py -q --tb=line
# t5256u DIRECT-gate bind: exit 0 · 53 passed

PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_ops_v1_evidence_gate.py /tmp/nfl-ops-v1-evidence
# exit 0 · status GATED_OK_AWAITING_CHIEF · digest 27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124
```

Inherited #700/#701 real-outcome tests: **NOT_RUN**.

## Evidence labels (actual run)

| Check | Label |
|---|---|
| produce_fixture_chain | EXECUTED_HERE |
| consume_fixture_chain | EXECUTED_HERE |
| rehashed_faults | EXECUTED_HERE |
| spy_positive_control | EXECUTED_HERE |
| inherited_real_outcome_tests | NOT_RUN |
| primary_b_worker_handoff | SOURCE_INSPECTION (bound #712 82683cd9; not platform reclaim) |
| chief_review | NOT_RUN |
| ready_for_review | NOT_RUN |
| lineage #706/#707 / utility #700/#701 | SOURCE_INSPECTION |

## Sample manifest (actual synthetic run)

`data/ops/nfl-ops-v1-evidence-manifest/SAMPLE_MANIFEST.json`

Numerical positive: `n=1` · `game_id=2026_99_TST_SYN` · `point_margin=3.0` · `line=-3.0` · `price=-110` · common digest matches #707 pin.

## Known limitations

- CERT=0. SYNTHETIC_ONLY. Not customer/production eligible.
- Passing tests are necessary, not self-acceptance. Chief reviews.
- READY_FOR_REVIEW cannot be self-stamped.
- Primary B worker_handoff bound from #712 tip 82683cd9; PLATFORM_LIMITATION / not_a_pass preserved; not RELEASE_CONFIRMED.
- Fixture assembly + hhl1 plumbing were copied from accepted draft tips onto this branch so the gate sits on the real caller; those draft PRs stay unmerged.
- No real-data fit/calibration/forecast/scoring/outcome join.
- No merge / deploy / prod config / public output.

## Handoff record

| Field | Value |
|---|---|
| task | NFL_OPS_V1 evidence-manifest gate |
| worker | Cursor cloud Primary A `bc-aeae1f9f-5b28-5b1f-b88a-3afdb10513a1` |
| workspace_alias | `/agent/repos/kosedge` |
| dirty/untracked at handoff | see git status after this commit (expect clean on this branch) |
| running processes/jobs | none owned by this lane (pytest/cli finished) |
| pending prompts | none |
| successor | Chief + independent review (B already bound; no successor launch) |
| ownership | HANDOFF_RECORDED · not RELEASE_CONFIRMED (platform reclaim is Chief/B) |

## t5256u DIRECT-gate bind (not closed)

Package CLOSE `d468000e` SUPERSEDED. Codex probe of declaration-only `validate_manifest` is refused. DIRECT gates now build `VerificationContext` from live git + on-disk files + supplied payload/command/exit/output/log bytes. Self-consistent 64-hex hashes, `exit=17`, and `head=not-a-commit` refuse. `run_rehashed_fault_control` invokes `gate_before_consume` on a mutated copy (`gate_invoked=1`, instrumentation fired, `forbidden_calls=0`).

B `PLATFORM_LIMITATION` / `not_a_pass` preserved. Joint successor freeze on `cursor/nfl-joint-contract-v1-literal-law-13a1` @ `6f4c5b65` is NOT claimed integrated through this gate.

Readable machine delta: `data/ops/nfl-ops-v1-evidence-manifest/DIRECT_GATE_DELTA.json`.

CERT=0 · `ready_for_review=false` · `self_accept=false`.
