# Market info_overlap MVP (2026-08-29)

**After #307 + #308 on e253.** Last KEI/game-card leg.

## Contract

On KEI / game card:

| Field | Meaning |
|-------|---------|
| `kei_situation_flags` | Applied KEI factor labels |
| `market_line` | Current market spread (home) |
| `market_as_of` | Market snapshot time |
| `info_overlap` | `unknown` \| `kei_ahead` \| `market_ahead` \| `aligned` |

v1:

- Market moved ≥ 0.5 toward **same side** as KEI delta after pack commit → `market_ahead` (**no extra KEI juice**)
- Pack commit + market flat → `kei_ahead`
- Same side and |move − kei| ≤ 0.75 → `aligned`
- Missing inputs / opposite side → `unknown`

No auto-bet. No accepts. No ingest rewrites.

## Files

- `nfl_market_info_overlap.py`
- `nfl_kei_week1_reprice.py` — optional market_* kwargs; attach on log
- `tests/test_nfl_market_info_overlap.py`
