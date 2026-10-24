# C-1 — NR-2 withdrawn

**Statement:** Cursor VM miss, not missing institutional memory.

| register | path | pin | hashed on this VM? |
| --- | --- | --- | --- |
| DATA_ASSETS.md | `/workspace/kosedge-registers/DATA_ASSETS.md` | sha8 `8ca7c553` | NO — path absent; IMV-inspected / CoS-confirmed |
| INVENTORY_v1.md | `/workspace/ops/nfl_data_inventory_t4183u/INVENTORY_v1.md` | sha12 `cf9ebb2ffb27` | NO — path absent; IMV-inspected / CoS-confirmed |

`sha256sum` on this VM (2026-10-24): both paths “No such file or
directory”. INV-1 called that MISSING. That was wrong. The registers
exist on the CoS box. IMV hashed them.

**B9 / G5:** register exists; no week-aware roster/depth asset row.

**Needs-Ryan:** NR-1 only. NR-2 removed.
