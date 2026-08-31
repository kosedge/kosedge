# CFB Chapter 2 Phase 2B — SP+ carry shrink **s=0.85** (FIT)

**Stamp:** `cfb-season-engine-v0.15-power-sot` + 1C–1E QB path + **`EFF_CARRY_SHRINK=0.85`**  
**Brief:** `docs/CFB_CH2_EFF_CARRY_BRIEF.md`  
**Lever:** one global shrink toward league 50 on packaged 2025 SP+ carry

```text
eff' = 50 + 0.85 * (eff_2025 - 50)
```

Applied to `off_eff` / `def_eff` / `success_*` / `explosiveness`. Raw SP+ (`sp_offense` / `sp_defense`) unchanged. Pre-shrink 0–100 kept as `off_eff_pre_shrink` / `def_eff_pre_shrink`.

---

## Where it lives

| Piece        | Location                                                                                                                           |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| Constant     | `priors.py` → `EFF_CARRY_SHRINK = 0.85`                                                                                            |
| Compose read | `efficiency.build_efficiency_profile` (pack stamped `carry_shrink=0.85` → no double-shrink; legacy raw packs still shrink at load) |
| Packager     | `scripts/cfb/package_efficiency_2025_carry.py` (`CARRY_SHRINK=0.85`)                                                               |
| Snapshot     | `cfb_efficiency_snapshot_2025_carry_2026.json` (`as_of=2026-08-31`, `carry_shrink=0.85`)                                           |
| Power        | live `build_power_sot` → rematerialized `cfb_power_sot_2026.json` (+ web mirror)                                                   |
| KEI          | `build_cfb_kei_futures_2026.py --kei-only` (futures **not** rewritten)                                                             |

---

## Live compose vs paper-sim 0.85

| Gate           |      Paper-sim |                              Live | Result   |
| -------------- | -------------: | --------------------------------: | -------- |
| OSU #1         |           PASS |                        **OSU #1** | PASS     |
| BALL@OSU WP    |         ~0.979 | **0.9791** (KEI −40.51 / WP 0.98) | PASS     |
| STAN off_eff   |          31.45 |             **31.45** (pre 28.18) | PASS     |
| UNC off_eff    |          28.68 |             **28.68** (pre 24.92) | PASS     |
| TCU off_eff    |          62.53 |             **62.53** (pre 64.74) | PASS     |
| TCU raw margin |          15.11 |               **15.14** (< 16.48) | PASS     |
| HAW off_eff    |         ~50.18 |                         **50.18** | PASS     |
| HAW@STAN KEI   |         ~+5.90 |     **+5.93** (flip not required) | reported |
| Membership     | near-ties only |        **ND→TEX**; ORE↔MISS order | PASS     |

Live top-7: **OSU, MISS, ORE, MIA, TAMU, IU, TEX** — enter `{TEX}` / leave `{ND}` only.

---

## Other canaries

| Gate                                                                                            | Result                                |
| ----------------------------------------------------------------------------------------------- | ------------------------------------- |
| Utah natty%                                                                                     | **6.2%** (futures not rewritten) PASS |
| USF vs OSU E[wins]                                                                              | futures not cloned PASS               |
| No team if / RESPONSE / WEIGHT_OFF_EFF / STRENGTH_NOISE / roster blend / PBP SoT / 1C–1E revert | PASS                                  |

---

## Forbidden check

No `if team == Stanford/UNC/Hawaii/TCU`. No `MATCHUP_RESPONSE`. No `WEIGHT_OFF_EFF` / roster blend. No `STRENGTH_NOISE` edit. No invented s. No warehouse PBP as live KEI SoT. No Utah / NFL/CBB/MLB trees.

**2B landed at s=0.85.** Corpses partially regressed; cupcake and rewritten membership gates hold.
