# t4643u WS-A CoS RECEIPT — IMV C0–C7 bound — stop for ACCEPT → IMV grade

DECISION **098da1dd** · IMV criteria **062197c0** (BINDING) · CERT=0
#645 DRAFT only · #648 / G34 / Exp D-R untouched · no merge/deploy/Odds/F2

## G1–G4 (exact)

| IMV | verdict | repair this tip |
|---|---|---|
| G1 warehouse | **GAP** (CLOSED ≠ CONSUMED; no SELECT) | none — C3 |
| G2 depth | **READ+GATE · PROVENANCE_ONLY · GAP_SIM_VOLUME** | labels only — C5 |
| G3 W8 official | **MISSING** (14/14 flags; overlay last designated) | no invent — C2 |
| G4 season vs game | named · **C6b DEFER + Needs-CLEAR** | no pack rewrite |

CONSUMED baseline preserved (C4): injury `impact_*` · schedule/rest · inseason EPA.

C7 clean: no MAE/CERT/invent-W8/merge as eng PASS.

## Path list

| path | role |
|---|---|
| `data/ops/nfl-t4643u-w8-forecast-integrity/IMV_ACCEPT_CRITERIA_t4643u_WS_C_ENG_CORRECTNESS_CONSUMPTION_v1.txt` | binding criteria sha8 **062197c0** |
| `…/C0_C7_CONTRACT.md` | C0–C7 targeting |
| `…/CODE_PATH_MAP.md` | file:line map |
| `…/INPUT_CONSUMPTION_MATRIX.md` | matrix |
| `…/INPUT_CONSUMPTION_MATRIX.json` | machine matrix |
| `…/WAREHOUSE_AUTHORITY.md` | do not wire |
| `…/BOUNDED_REPAIR_PLAN.md` | G1–G4 |
| `…/fixtures/C1_*.json` + `FIXTURES.sha256` | C1 oracles |
| `…/SHA256SUMS` · `SHA8_TABLE.md` | hashes |
| `data/ops/nfl-model-forecast-emit-t4559u/research_runs/nfl-w8-2026-t4643u-forecast-integrity/` | mirror |
| `services/model-service/tests/test_nfl_w8_forecast_consumption_contracts_t4643u.py` | 12 passed |

Needs CoS ACCEPT → IMV grade. Needs CLEAR to SELECT warehouse, change season SoT, or merge.
