# INV-1 erratum — C-1..C-4

INV-1 MANIFEST `7d93380e` remains the inventory. This file amends it.

## C-1 MAJOR — NR-2 withdrawn

**NR-2 is not Needs-Ryan.** Cursor VM miss, not missing institutional
memory.

On-box (CoS / IMV-inspected) registers:

| path | pin |
| --- | --- |
| `/workspace/kosedge-registers/DATA_ASSETS.md` | sha8 `8ca7c553` |
| `/workspace/ops/nfl_data_inventory_t4183u/INVENTORY_v1.md` | sha12 `cf9ebb2ffb27` |

This Cursor VM still cannot open those paths (`sha256sum` = file not
found). The hashes above are **IMV-inspected / CoS-confirmed**, not a
sha256sum run on this VM. That is the same visibility miss as INV-1.
It does **not** reopen NR-2.

**B9 / G5 reclassified:** register exists; no week-aware roster/depth
asset row. (IMV §4: conclusion HOLDS.)

**Needs-Ryan remaining:** NR-1 only (confirm KosEdgeData / research-store
weekly archives). No spend. Odds API ON HOLD.

Withdrawn everywhere INV-1 named NR-2: `INV-1.C-gaps.md`,
`COS-HANDOFF.md`, `INV-1.B-owned-sources.md` B9-as-MISSING,
`INV-1.B-owned-sources.json` B9, `STOP.md`/`README.md` if they implied
NR-2 as an open ask.

## C-2 MINOR — A6 path:line or drop

The INV-1 A6 sentence that the v6 package “freezes the defective
pre-kickoff claim” without path:line is **dropped**.

Exact “pre-kickoff” / `as_of <= kickoff` cites in the v6 deposit
(files searched; producer deposited under `cited/` sha `ae8f9585`):

| path | lines | text |
| --- | --- | --- |
| `holdout_delta_producer.py` | 12 | `pre-kickoff information only, with as_of <= kickoff` |
| `holdout_delta_producer.py` | 78–81 | `_pre_kickoff_only` — post-game score fields only |
| `holdout_delta_producer.py` | 84–99 | `_assert_as_of_before_kickoff` — `listing_as_of` only |
| `holdout_delta_producer.py` | 130–131 | both checks called |

Searched, **no match** (claim dropped for these surfaces):

- `run_injury_holdout_opening.py`
- `t_expected/HOLDOUT_HAND_CHECK.md`
- `t_expected/HOLDOUT_EXPECTED.json`
- `gate-table.md`
- `plans/`, `notes/`, `out/`

Seeded IMV ruling copies inside v6 mention “pre-kickoff” (e.g. v2 L74).
Those are IMV text, not Cursor expected-answers.

## C-3 MINOR — SECONDHAND labels

Labeled **SECONDHAND** (not re-proven on this VM; not deposited):

- leftover untracked `run_injury_residual_holdout_v3.py` `load_holdout_rosters` L812–840
- `services/data-platform-nfl/.../ingest.py` `materialize_depth_chart_weekly` L1735–1795
- production `injury_paths.py` “no load_rosters” claim
- `deploy-vercel` HEAD `20d51f22` as the location of residual-fit scripts (they are not there)

Deposited for IMV re-hash: `cited/holdout_delta_producer.py` sha256
`ae8f9585cca6400fe1f9c73b71c480bea1fb77ff75467b9d5536f614ac8dd630`.

A1/A2/A4/A5 line cites that IMV already inspected on runner-v6 copies
are unchanged.

## C-4 MINOR — B2b holdout-era DO-NOT-OPEN

`nfl_depth_chart_2024_w1.json` and `nfl_depth_chart_2025_w1.json` under
`services/model-service/src/services/nfl_season_engine/data/historical/`:

| file | classify | contents |
| --- | --- | --- |
| `nfl_depth_chart_2024_w1.json` | name + size **70910** | **DO-NOT-OPEN** |
| `nfl_depth_chart_2025_w1.json` | name + size **78884** | **DO-NOT-OPEN** |

Class: EXISTING BUT UNVERIFIED — holdout-era **DO-NOT-OPEN**.
Name/size only. Contents not read this pass or in INV-1.

## Not changed

NR-1, G1–G4, G6, D, E, F, G (except G5 reclass), holdout sealed,
no lock, no Step 2.
