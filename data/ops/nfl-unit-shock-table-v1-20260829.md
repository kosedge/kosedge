# Unit shock table v1 — keystone outs on accept → remat (2026-08-29)

**Branch:** `cursor/unit-shock-table-v1-7d1e` → `deploy-vercel`  
**Depends on:** #301 defense DepthSot (merged; e253 `55eb4b32ee64`)  
**Doctrine:** One pack. Accept → remat/KEI. **One** role shock from `shock_table_v1` for C / LT / EDGE1 / CB1 / S1. **No** player-deletion + full unit wipe double-count.

## What shipped

| Piece | Change |
|-------|--------|
| Table | `SHOCK_TABLE_V1` in `nfl_unit_shock_table.py` |
| Roles | **C, LT, EDGE1, CB1, S1** only |
| Path | DepthSot accept → pack write → Week 1 KEI reprice (remat smoke / board) |
| Anti double-count | Role shock replaces flat `ol_out` / `defense_out` for that row; `unit_wipe` logged as **not applied** |
| Fixtures | Pinter-class C (BAL) + Adams-class S (MIN) — tests only; no live desk accepts |

## Magnitudes (team weaker)

| Role | Spread | Total |
|------|--------|-------|
| C | 0.65 | 0.30 |
| LT | 0.80 | 0.35 |
| EDGE1 | 0.85 | 0.25 |
| CB1 | 0.70 | 0.20 |
| S1 | 0.55 | 0.18 |

Flat `ol_out` / `defense_out` still apply for non-keystone rows (LG/RG/RT/DL/LB/NB/…).

## Out of scope (explicit)

- Rest / travel stacking changes
- Weather
- Snap shares
- Auto-accept
- Full unit wipe as an applied factor

## Tests

`services/model-service/tests/test_nfl_unit_shock_table.py`
