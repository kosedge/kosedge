# Snap-share prior on DepthSot accept (2026-08-29)

**After #303 (rest+weather).** This leg only.

## Contract

- `proposed_patch` may set `snap_share_prior` (0–1) and `snap_share_package`
- Accept is the only write gate (no auto-accept)
- Missing prior → depth-rank default (or package table)
- Out player → redistribute freed share to **existing** same-pos committee
- **No new WR1/QB1 crown** (`depth_order` / `competition_status` untouched)
- Fantasy / season-engine loader reads the same pack shares
- No rest/weather/shock edits in this PR; no live desk accepts

## Files

- `services/model-service/src/services/nfl_snap_share_prior.py`
- `nfl_daily_intel.py` — ALLOWED_FIELDS + post-accept redistribute
- `nfl_season_engine/loaders.py` — pack → `PlayerRole.snap_share`
- `tests/test_nfl_snap_share_prior.py`

## Next (not this PR)

Confirmation / variance.
