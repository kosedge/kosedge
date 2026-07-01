# NFL Props + Fantasy Foundation

This document defines the enterprise-safe player projection, props, and fantasy layer built on top of the existing NFL game-level simulator and data platform.

## Architecture

- Data platform computes weekly projection features in `nfl_player_projection_features_weekly` using normalized PBP + usage/situational aggregates.
- Identity graph resolves every player row to canonical `player_uid` before downstream joins:
  - `nfl_player_identities` (canonical node)
  - `nfl_player_source_id_map` (source + external id map with confidence, trust flags, first/last seen)
  - `nfl_player_aliases` (name variants + normalized alias + context window)
  - `nfl_player_mapping_events` (resolver version, rule, confidence, status, full audit payload)
  - `nfl_player_mapping_review_queue` (unresolved/conflict/manual-guardrail queue)
  - `nfl_player_mapping_quality_snapshots` (weekly SLA metrics + readiness state)
- Model-service materializes player baseline projections in `nfl_player_projection_baselines` with deterministic bounded math and uncertainty blocks.
- Market ingestion stores player prop snapshots in `nfl_player_prop_market_snapshots`.
- Props model computes projection-vs-market edges into `nfl_player_prop_model_edges`.
- Fantasy transformer writes profile-specific outcomes/ranks/tiers into `nfl_fantasy_weekly_projections`.
- Layer-level ops/readiness audits are persisted in `nfl_projection_audit_runs`.

## Pipeline Tasks

- `src.tasks.pull_nfl_player_prop_market_snapshots(season, week)`
- `src.tasks.materialize_nfl_player_baseline_projections(season, week, model_version)`
- `src.tasks.materialize_nfl_player_props_edges(season, week, model_version)`
- `src.tasks.materialize_nfl_fantasy_projections(season, week, model_version)`
- `src.tasks.run_nfl_player_projection_cycle(season, week, model_version, pull_market_snapshots=true)`
- `src.tasks.run_nfl_identity_refresh(season, week, model_version)`
- `src.tasks.apply_nfl_identity_manual_resolutions(limit=200, reviewer="system-weekly-identity-sync")`
- `src.tasks.run_nfl_identity_quality_snapshot(season=None, week=None, source_system=None)`

## API Surfaces

- `GET /nfl/projections/players`
- `GET /nfl/props/board`
- `GET /nfl/fantasy/rankings`
- `GET /nfl/ops/projections-readiness`
- `POST /nfl/ops/materialize-player-baselines`
- `POST /nfl/ops/materialize-player-props`
- `POST /nfl/ops/materialize-fantasy`
- `POST /nfl/ops/run-player-cycle`
- `GET /nfl/identity/queue`
- `POST /nfl/identity/queue/{queue_id}/action`
- `POST /nfl/identity/refresh`
- `POST /nfl/identity/manual-reconciliations`
- `POST /nfl/identity/quality-snapshot`
- `GET /nfl/identity/quality/latest`

## Operating Model

### Weekly cadence

1. Run `run_nfl_identity_refresh` for target season/week (this also runs baseline/props/fantasy materialization).
2. Run `apply_nfl_identity_manual_resolutions` for queued guardrail remaps and approved queued mappings.
3. Run `run_nfl_identity_quality_snapshot` and read `GET /nfl/identity/quality/latest`.
4. Run `GET /nfl/ops/projections-readiness` for layer readiness and `GET /health/nfl-production-readiness` for model gate.
5. Publish props/fantasy only when identity + projection gates are in approved states.

### Manual review workflow

1. Query `GET /nfl/identity/queue?queue_status=pending`.
2. For each unresolved/conflict item, approve/reject via `POST /nfl/identity/queue/{queue_id}/action`.
3. Approved actions must include canonical `player_uid` to create a trusted source-id mapping.
4. Re-run `POST /nfl/identity/quality-snapshot` after material queue changes.

### SLA thresholds (publish/no-publish)

- **Identity coverage rate:** target `>= 0.94`; warning below `0.94`; no-publish below `0.90`.
- **High-confidence auto-map rate:** target `>= 0.75`.
- **Unresolved rate:** no-publish above `0.06`.
- **Conflict rate:** no-publish above `0.02`.
- **Source freshness:** warning above 12h since last source-id update.
- **Guardrail policy:** no silent remap of trusted links (`confidence >= 0.95`) without explicit mapping event + queue record.

## Data Source Matrix

| Source | Free/Paid | Fields Used | Ingestion Cadence | Reliability / Risk Notes | Implementation Status |
| --- | --- | --- | --- | --- | --- |
| nflverse / nflreadpy | Free (open data, dataset terms apply) | PBP (`load_pbp`), schedules, rosters, injuries, weekly stats | Daily + weekly rebuilds | Broad coverage and reproducible dictionaries; must respect upstream data-owner terms | Integrated now |
| The Odds API (NFL event odds, player props markets) | Free tier + paid quotas | Player prop lines/prices (`player_pass_yds`, `player_rush_yds`, `player_reception_yds`, `player_receptions`, `player_anytime_td`) | Hourly near slate + pre-kickoff refresh | Practical for V1 but quota cost/coverage variance by sportsbook/region | Integrated now |
| ESPN public scoreboard endpoints (unofficial) | Free | Schedule/status fallback and context snapshots | Daily + hourly | Unofficial and undocumented; no SLA, endpoint change risk | Integrated now (fallback context source) |
| SportsDataIO (FantasyData) NFL feeds | Paid | Official depth charts, richer injury status, projections/fantasy metadata, prop/archive feeds | Near real-time + scheduled | Better depth-role confidence and injury freshness than free stack; commercial contract required for full live feeds | Not integrated (recommended paid upgrade) |
| Sportradar Odds Comparison Player Props | Paid (enterprise) | Multi-book player props, mappings, structured change-log feeds | Minute-level polling / change-log driven | Enterprise-grade normalization and bookmaker mapping; contract onboarding required | Not integrated (recommended for production props scale) |
| Stats Perform / Opta | Paid (enterprise) | Advanced player/team context, tracking-derived features, premium betting/fantasy context | Real-time + batched historical | Highest quality for advanced role/usage and proprietary context; expensive and sales-led | Not integrated (recommended for advanced model quality) |

## Paid Gap Analysis (What Is Still Needed)

- Depth chart quality: free rosters/injuries do not consistently provide definitive role ordering near kickoff.
- Injury latency/precision: free feeds are strong but still weaker than official/enterprise injury status updates.
- Props market continuity: free quota and sportsbook coverage can miss low-liquidity or alternate lines.
- Player/entity mapping: robust cross-provider IDs are needed for long-term enterprise reconciliation and audit.

## Recommended Paid Adoption Order

1. SportsDataIO for depth-chart + injury + fantasy operational hardening.
2. Sportradar player props for market coverage normalization and change-log driven updates.
3. Stats Perform/Opta only when premium tracking-driven features are required for model edge expansion.
