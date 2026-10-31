# EXPECTED_RECERT_OUTCOME — Gate 1 wrapper at `57347d888`

**Honest pre-declared outcome.** Cursor executes the packet; Cursor does **not** clear Gate 1.

## After certification-only wrapper

| Check | Expected |
| --- | --- |
| Pytest GO/PUNT (`test_rz_q4_trail3_regulation_clock_blocks_early_fg_range_field_goal`) | **PASS** (assert at 350s restored to `punt`; 300/240 stay `field_goal`) |
| Full `test_nfl_clock_play_simulator.py` | **PASS** (38/38) |
| `certification_thresholds.json` artifact | **PRESENT** at `data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json` |
| Model / simulator source | **UNCHANGED** vs parent `57347d888d2832a735bb826f6105c44b34d9cc72` |
| config / inputs / PBP hashes | **UNCHANGED** (bindings below) |

## Hard gates under CONTRACT (NOT ±0.05)

| metric | train | sim | abs_delta | abs_delta_max | expected_verdict | hard_gate | source_receipt |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| field_goal_makes_per_game | 3.2644079637 | 4.0239257812 | 0.7595178176 | 0.119987 | **FAIL** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| final_total_mean | 45.5951798812 | 44.6455078125 | 0.9496720687 | 1.7637 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| offensive_td_per_game | 4.8204680405 | 4.6801757812 | 0.1402922593 | 0.2966 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| red_zone_entries_per_game | 6.6975200838 | 6.8237304688 | 0.1262103849 | 0.2474 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |
| core_drives_per_game | 22.5640936081 | 22.3203125 | 0.2437811081 | 0.7439 | **PASS** | true | builder_827 / GATE_1_NOT_CLEARED packet at parent 57347d888 (reuse-until-rebind) |

FG Δ≈**0.7595** ≫ 0.119987 is an intentional **mechanism** fail under honest thresholds. Thresholds were **not** fitted to SHA closeness.

## Gate 1 status

**GATE_1_NOT_CLEARED** unless FG mechanism is fixed (out of scope of this wrapper).

Cursor must:

1. Execute wrapper + prove no model change + recert under contract.
2. Record FAIL on `field_goal_makes_per_game`.
3. **Not** declare Gate 1 cleared.
4. **Not** widen FG `abs_delta_max` to green the gate.

Diagnostics (55–79, key3/key7, OT, EQ-FG/EQ-TD, etc.) remain report-only.

## Bindings (unchanged)

- config_sha256: `2b3a8ac22569206b620ad5efe4d5dfb8c3b848894eae33b0ae934d4f242812b1`
- inputs_sha256: `982a5a03e4e519cbdc8f9a344000f8391f3a17a8a71e61dc8e4a8ce21afacf30`
- pbp_sha256: `823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c`
- seed_manifest_sha256: `46de6deb6fde81d366aa8191e48e4e58e9938abe0be576fa9f60efe5c7cfcad2`
- certification_thresholds.json content sha256 (packet commit copy): `e581653295e07372948df83507df8fe0a2e62472c0079ce486538624412ac66d`
