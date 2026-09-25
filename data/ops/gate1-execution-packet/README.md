# Gate 1 execution packet (exported for Max / Cursor)

**Label:** `GATE1_PACKET_EXPORTED_FOR_MAX`  
**Clears Gate 1:** **NO**  
**Frozen parent / base SHA:** `57347d888d2832a735bb826f6105c44b34d9cc72`  
**Repo:** `kosedge/kosedge`  
**Wrapper branch to create:** `gate1-cert-wrapper-57347d888`  
**Authority:** Alex Rourke `CERT_CONTRACT_READY` + `GATE1_EXECUTION_PACKET_READY`  
**CoS red-team:** ACCEPT with live-rebind / PBP-hash / no-±0.05 conditions

This directory is the **repo-accessible** copy of `/workspace/gate1-execution-packet/` so Max/Cursor can execute without Grok Bot box paths.

## Do not

- Redesign the simulator / touch `services/model-service/src`
- Start arms / touch held-out / start R14 / merge / deploy
- Promote Gate C **±0.05/game** into Gate 1 thresholds
- Fit or widen thresholds to this SHA
- Declare Gate 1 cleared while `field_goal_makes_per_game` FAILs

## Contents

| Path | Role |
| --- | --- |
| `commit/certification_thresholds.json` | Slim contract thresholds → copy to `data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json` |
| `commit/test_assert.patch` | One-line assert `go`→`punt` at clock 350s |
| `commands/00_create_wrapper_commit.sh` … `03_run_gate1_recert.sh` | Exact Cursor sequence |
| `commands/apply_contract_thresholds.py` | Contract abs_delta_max eval helper |
| `hard_gate_precompute.json` | Expected hard-gate table (reuse-until-rebind from builder_827) |
| `EXPECTED_RECERT_OUTCOME.md` | Pre-declared **GATE_1_NOT_CLEARED** on FG |
| `GATE1_EXECUTION_PACKET_57347d888.{md,json}` | Full packet |

## Exact Cursor sequence

```bash
export KOSEDGE_ROOT="$(git rev-parse --show-toplevel)"
export PACKET_DIR="$KOSEDGE_ROOT/data/ops/gate1-execution-packet"
export PARENT_SHA=57347d888d2832a735bb826f6105c44b34d9cc72

bash "$PACKET_DIR/commands/00_create_wrapper_commit.sh"   # prints NEW_SHA
export NEW_SHA=...   # from 00
bash "$PACKET_DIR/commands/01_prove_no_model_change.sh"
bash "$PACKET_DIR/commands/02_bind_hashes.sh"
# Required: locked PBP whose content sha256 == 823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c
export PBP_PATH=/path/to/locked-pbp.ndjson
bash "$PACKET_DIR/commands/03_run_gate1_recert.sh"
```

After live certify/freeze: **rebind** hard-gate rows from measured receipts (do not treat precompute-only `gate1-contract-eval.json` as final).

## Bindings (unchanged vs parent)

- config_sha256: `2b3a8ac22569206b620ad5efe4d5dfb8c3b848894eae33b0ae934d4f242812b1`
- inputs_sha256: `982a5a03e4e519cbdc8f9a344000f8391f3a17a8a71e61dc8e4a8ce21afacf30`
- pbp_sha256: `823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c`
- seed_manifest_sha256: `46de6deb6fde81d366aa8191e48e4e58e9938abe0be576fa9f60efe5c7cfcad2`
- certification_thresholds.json content sha256: `e581653295e07372948df83507df8fe0a2e62472c0079ce486538624412ac66d`

## Expected after wrapper + recert

**GATE_1_NOT_CLEARED** — FG hard gate FAIL (Δ≈0.7595 ≫ 0.119987); pytest GO/PUNT PASS; thresholds PRESENT; other 4 hard metrics PASS under contract.
