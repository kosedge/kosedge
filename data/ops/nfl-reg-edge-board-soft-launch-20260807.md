# NFL REG Edge Board soft launch — 2026-08-07

## Live now

| Surface | Status |
|---------|--------|
| `/edge-board/nfl` (Current week) | **16 Week 1 REG games** with KEI + market join |
| Odds slate (`?slate=all`) | Forward REG weeks with books (W1–17 market coverage varies) |
| Model vs KEI | Attached on fair-lines; shown under KEI when blend splits; full split on `/pro/nfl/fair-lines` |
| PLAY tags | Selective: **1** W1 spread PLAY (ARI@LAC); totals sides-only (no Total PLAY) |
| PRE | Filtered out — no exhibition edges |

Source: `GET /nfl/fair-lines?season=2026&days_ahead=200` on full model-service (`model-service-production-e253`).

## Forward weeks

- Fair-lines return **241 REG** rows across weeks 1–17.
- Market join is strong early (W1–4 full / near-full) and thinner later (e.g. W17 = 1 joined).
- Guest default = Current week (W1). Odds slate = forward coverage without inventing books.

## Futures / season

- Guest Power Ratings / projections still use packaged preseason sim bundle.
- **After 100k sim finishes:** publish versioned research numbers into season surfaces (do not restart Mac heavy jobs from this change set).

## Props

| Item | Status |
|------|--------|
| `/pro/nfl/props` 2026 W1 | Model scaffold present (~250 `anytime_td` rows) |
| Book join | **0** — `kosedge_only` / research posture |
| Stake PLAY | Off (`PLAY_STAKE_ELIGIBLE=false`) |
| Soft-launch call | Surface what exists; do not fake 2026 market edges |

## Honesty / gates (unchanged)

- `NFL_PRESEASON_MODE=info`
- `TOTAL_PLAY_ENABLED=false`
- `NFL_PRODUCT_GATE_STATUS=YELLOW`
- Open access preview remains default-on for guests

## Go-mode gaps after sim completes

1. Publish versioned 100k season / win-total / survivor research into guest season surfaces
2. Confirm season-engine health for Survivor / Game Boxes (no heavy-job restarts)
3. Fantasy: swap preseason-fallback → live draft ranks when materializer posts
4. Props: wait for real 2026 yardage / book join before stake tags
5. Keep `MODEL_SERVICE_URL` on the **full** Railway model-service host (not the thin `kosedge-production` shell)
