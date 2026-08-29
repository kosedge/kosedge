# Defense depth SoT — EDGE / DL / LB / CB / S / NB (2026-08-29)

**Branch:** `cursor/defense-depth-sot-7d1e` → `deploy-vercel`  
**Doctrine:** One pack. One `DepthSotWorkItem` queue. No second SoT. No auto-accept. No unit shocks / snap shares / weather in this PR.

## What shipped

| Piece | Change |
|-------|--------|
| Pack schema | `defense_positions` + `defense_roles[]` (parallel to `ol_roles`) |
| Positions | **EDGE, DL, LB, CB, S, NB** first-class on the same SoT pack |
| Accept path | `layer=defense_roles` via existing `apply_intel_overrides` → pack write → remat |
| KEI | Week 1 reprice reads `defense_roles`; starter out uses `defense_out_spread` / `defense_out_total` |
| Seed | SF starters (Bosa EDGE1, …) for desk accept / fixture only |

## Flow (unchanged)

```
note / feed → DepthSotWorkItem (proposed_patch) → human accept → pack → remat → board
```

Notes and Sleeper/txn feeds **propose only**. They cannot write KEI or invent starters.

## Out of scope (explicit)

- Unit shocks
- Snap shares
- Weather
- Auto-accept from feed
- Full 32-team defense charts (seed is SF fixture room)

## Follow-up after txn scanner (#300)

`index_pack_players` should include `defense_roles` in `PACK_SOT_LAYERS` (shared constant in `nfl_daily_intel.py`).

## Tests

`services/model-service/tests/test_nfl_defense_depth_sot.py`
