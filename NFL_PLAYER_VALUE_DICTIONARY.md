# NFL Player Value Dictionary

**Owner lock:** Ryan Kos · 2026-09-03  
**Product name in copy:** “player value (pts of KEI)” — never call this DVOA or WAR on a subscriber surface.

## What this is

A **dictionary** of role → points of spread / total vs replacement for desk / KEI honesty.

It is **not**:

- FanGraphs-style season WAR
- A public leaderboard or tile
- A second projection engine

Units: **spread pts + total pts** (team weaker when the role is out), same scale as `shock_table_v1`.

## v1 live roles (KEI applies)

Wired today via `SHOCK_TABLE_V1` / `shock_table_v1`. Magnitudes are frozen for Week 1 unless Ryan flips them.

| Role   | Spread | Total | `kei_live` |
|--------|--------|-------|------------|
| C      | 0.65   | 0.30  | true       |
| LT     | 0.80   | 0.35  | true       |
| EDGE1  | 0.85   | 0.25  | true       |
| CB1    | 0.70   | 0.20  | true       |
| S1     | 0.55   | 0.18  | true       |

Doctrine:

- **No double-count** with unit wipe (role shock replaces wipe; wipe logged not applied).
- **QB stays on `qb_confirmation` / backup drop-off** — QB is **not** in the shock table.
- Flat `ol_out` / `defense_out` still cover non-dictionary OL/DEF depth when needed.

## v2 research roles (log only)

Named by DepthSot packs (`ol_roles`, `defense_roles`, skill rows) that a handicapper would price. Each row is `kei_live: false`.

Week 1 KEI **does not** apply these magnitudes. Ops / subscriber factor logs see them on `keiReprice.consideredNotApplied` (factor `player_value_dictionary`) with a stated point value: “this WR1 would have been X pts.”

| Role  | Pack slot                         | Spread | Total | `kei_live` |
|-------|-----------------------------------|--------|-------|------------|
| RT    | `ol_roles` RT                     | 0.70   | 0.30  | false      |
| LG    | `ol_roles` LG (IOL class)         | 0.45   | 0.22  | false      |
| RG    | `ol_roles` RG (IOL class)         | 0.45   | 0.22  | false      |
| WR1   | skill WR depth_order 1            | 0.70   | 0.35  | false      |
| TE1   | skill TE depth_order 1            | 0.50   | 0.25  | false      |
| RB1   | skill RB/HB depth_order 1         | 0.55   | 0.28  | false      |
| DL1   | `defense_roles` DL (IDL)          | 0.60   | 0.20  | false      |
| LB1   | `defense_roles` LB                | 0.50   | 0.18  | false      |
| EDGE2 | `defense_roles` EDGE order 2      | 0.45   | 0.15  | false      |
| CB2   | `defense_roles` CB order 2        | 0.40   | 0.12  | false      |

Magnitudes sit on the **same scale as v1** (no invented 3-point WR shocks). Skill research outs (WR1 / TE1 / RB1) skip flat `skill_out` so the dictionary path does not move KEI; OL/DEF research rows keep existing flat paths so Week 1 games that already move on non-keystone outs stay bit-identical.

## KEI-wire of v2

Promoting any research role to `kei_live: true` requires:

1. Unused holdout evidence, and
2. Explicit Ryan flip.

Do not remat, mint KEI, retune spread PLAY 2.5–7, or flip `TOTAL_PLAY_ENABLED` / `PLAY_STAKE_ELIGIBLE` for this dictionary.

## Code

- Table + resolve: `services/model-service/src/services/nfl_unit_shock_table.py`
- Log wire: `services/model-service/src/services/nfl_kei_week1_reprice.py` (`considered_not_applied`)
- Tests: `services/model-service/tests/test_nfl_unit_shock_table.py`
