# GATE1_EXECUTION_PACKET_57347d888

**Label:** `GATE1_EXECUTION_PACKET_READY`  
**Clears Gate 1:** **NO**  
**Executor:** Cursor only (execute this packet; no redesign; no merge/deploy; no cloud agents)  
**Frozen parent:** `57347d888d2832a735bb826f6105c44b34d9cc72`  
**Repo:** https://github.com/kosedge/kosedge  
**Branch to create:** `gate1-cert-wrapper-57347d888`

This packet does **not** clear Gate 1. It wraps the Alex Rourke CERT_CONTRACT_READY thresholds and the GO→PUNT test-expectation fix onto the frozen parent so Cursor can recert honestly under contract abs_delta_max (**not** ±0.05).

---

## 0. Forbidden

- Do **not** promote Gate C isolation **±0.05/game** into Gate 1 thresholds.
- Do **not** fit or widen thresholds to observed deltas at `57347d888`.
- Do **not** redesign the model, touch `_fourth_down_decision`, or edit any `services/model-service/src`.
- Do **not** merge, deploy, launch cloud agents, start R14, or touch held-out.
- Do **not** declare Gate 1 cleared while `field_goal_makes_per_game` FAILs.

---

## 1. Wrapper contents (ONLY these two paths)

1. `data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json`  
   ← copy from `commit/certification_thresholds.json` in this packet  
   content sha256: `e581653295e07372948df83507df8fe0a2e62472c0079ce486538624412ac66d`
2. `services/model-service/tests/test_nfl_clock_play_simulator.py`  
   ← apply `commit/test_assert.patch` (single line: `"go"` → `"punt"` at clock_seconds=350.0)

---

## 2. GO vs PUNT (already ruled)

| Field | Value |
| --- | --- |
| Test | `test_rz_q4_trail3_regulation_clock_blocks_early_fg_range_field_goal` |
| File | `services/model-service/tests/test_nfl_clock_play_simulator.py` |
| Parent line | 556 |
| State | Q4, clock **350.0**, yl 65, 4th&5, home 17 away 20 (trail−3) |
| Soft ceiling (test config) | 327.0; max_clock 265.0 |
| Observed at parent | `punt` |
| Stale expected | `go` |
| **Ruling** | **TEST_EXPECTATION_STALE_WRONG** — implementation CORRECT |
| Exact fix | change assert `"go"` → `"punt"`; keep 300/240 → `field_goal` |
| Do not touch | `_fourth_down_decision` or any simulator source |

---

## 3. Hard-gate precompute (contract; reuse-until-rebind)

Train/sim from prior Gate 1 receipt at parent (`builder_827` / GATE_1_NOT_CLEARED). Reuse until rebind; if recert re-measures differently, rebind — do **not** retune thresholds.

| metric | train | sim | abs_delta | abs_delta_max | expected_verdict | hard_gate | source_receipt |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| field_goal_makes_per_game | 3.2644079637 | 4.0239257812 | 0.7595178176 | 0.119987 | **FAIL** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| final_total_mean | 45.5951798812 | 44.6455078125 | 0.9496720687 | 1.7637 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| offensive_td_per_game | 4.8204680405 | 4.6801757812 | 0.1402922593 | 0.2966 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| red_zone_entries_per_game | 6.6975200838 | 6.8237304688 | 0.1262103849 | 0.2474 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| core_drives_per_game | 22.5640936081 | 22.3203125 | 0.2437811081 | 0.7439 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |

### Structural / pytest / thresholds-present (expected after wrapper)

| metric | train | sim | abs_delta | abs_delta_max | expected_verdict | hard_gate | source_receipt |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| freeze_state_invariants_and_structural_checks | — | expected all true (unchanged model) | — | — | **PASS** | true | prior freeze at parent; wrapper does not touch simulator src |
| train_denominator_lock | 2863 games; anchors match denom receipt | — | — | — | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| exclusive_routing_pytest_all_pass | — | after wrapper: GO->PUNT assert fix; 38/38 expected | — | — | **PASS** | true | Alex contract go_vs_punt ruling TEST_EXPECTATION_STALE_WRONG |
| certification_thresholds_artifact_present | — | PRESENT after wrapper commit at data/ops/.../certification_thresholds.json | — | — | **PASS** | true | this packet commit/certification_thresholds.json |

---

## 4. Bindings (unchanged vs parent)

| Binding | Value |
| --- | --- |
| config_sha256 | `2b3a8ac22569206b620ad5efe4d5dfb8c3b848894eae33b0ae934d4f242812b1` |
| inputs_sha256 | `982a5a03e4e519cbdc8f9a344000f8391f3a17a8a71e61dc8e4a8ce21afacf30` |
| pbp_sha256 | `823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c` |
| seed_manifest_sha256 | `46de6deb6fde81d366aa8191e48e4e58e9938abe0be576fa9f60efe5c7cfcad2` |
| root seeds | neutral-structural 114729; home-offense-edge 228451; away-defense-edge 336182; tempo-contrast 443917 |
| train window | 2013–2023 REG; 2863 games |
| sim games | 2048 |

---

## 5. Diagnostics only (do not hard-fail Gate 1)

`yl_55_79_fourth_arrivals_per_game`, `exact_final_margin_3_rate`, `exact_final_margin_7_rate`, `overtime_games_rate`, `equalizing_fg_per_game`, `equalizing_td_per_game`, `td_per_red_zone_entry`, `fourth_down_go_share`, `third_down_conversion_rate`, `certify_drives_per_game_possession_start`

---

## 6. Exact Cursor command sequence

```bash
export PACKET_DIR=/workspace/gate1-execution-packet
export KOSEDGE_ROOT=/path/to/kosedge   # Cursor's checkout
export PARENT_SHA=57347d888d2832a735bb826f6105c44b34d9cc72

bash "$PACKET_DIR/commands/00_create_wrapper_commit.sh"   # prints NEW_SHA
export NEW_SHA=...   # from 00
bash "$PACKET_DIR/commands/01_prove_no_model_change.sh"
bash "$PACKET_DIR/commands/02_bind_hashes.sh"
# Optional: export PBP_PATH=... to locked PBP ndjson
bash "$PACKET_DIR/commands/03_run_gate1_recert.sh"
```

Receipts land in `/tmp/gate1-recert-$NEW_SHA/`.

---

## 7. Expected Gate 1 status after executing this packet

**GATE_1_NOT_CLEARED** — FG hard gate still FAIL (mechanism Δ≈0.7595 ≫ 0.119987); pytest GO/PUNT PASS; thresholds artifact PRESENT; other 4 hard metrics PASS under contract. Cursor must **not** clear Gate 1.

See `EXPECTED_RECERT_OUTCOME.md`.

---

## 8. Artifact index

| Artifact | Path |
| --- | --- |
| This packet (MD) | `/workspace/gate1-execution-packet/GATE1_EXECUTION_PACKET_57347d888.md` |
| This packet (JSON) | `/workspace/gate1-execution-packet/GATE1_EXECUTION_PACKET_57347d888.json` |
| Thresholds to commit | `/workspace/gate1-execution-packet/commit/certification_thresholds.json` |
| Thresholds sha256 | `e581653295e07372948df83507df8fe0a2e62472c0079ce486538624412ac66d` |
| Test assert patch | `/workspace/gate1-execution-packet/commit/test_assert.patch` |
| Command 00 | `/workspace/gate1-execution-packet/commands/00_create_wrapper_commit.sh` |
| Command 01 | `/workspace/gate1-execution-packet/commands/01_prove_no_model_change.sh` |
| Command 02 | `/workspace/gate1-execution-packet/commands/02_bind_hashes.sh` |
| Command 03 | `/workspace/gate1-execution-packet/commands/03_run_gate1_recert.sh` |
| Contract eval helper | `/workspace/gate1-execution-packet/commands/apply_contract_thresholds.py` |
| Hard-gate precompute | `/workspace/gate1-execution-packet/hard_gate_precompute.json` |
| Expected outcome | `/workspace/gate1-execution-packet/EXPECTED_RECERT_OUTCOME.md` |

Authority contract: `/workspace/gate1-cert-contract/GATE1_CERTIFICATION_THRESHOLDS_57347d888.json`  
Prior measured packet: `/workspace/gate1-cert-extract/builder_827.txt`

---

## 9. Completeness

**GATE1_EXECUTION_PACKET_READY** — Cursor is executor only; no reasoning left. Apply wrapper, prove no model change, recert under contract, record GATE_1_NOT_CLEARED on FG mechanism fail.
