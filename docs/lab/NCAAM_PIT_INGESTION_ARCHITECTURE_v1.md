# NCAAM PIT ingestion architecture (design only — Phase 2.5)

**Status:** DESIGN ONLY. Not deployed. No external pulls scheduled.  
**Purpose:** Make it impossible for a future model run to silently use current or end-of-season ratings for a historical prediction.

## Locked problem statement

Historical PIT KenPom for post-Test-A windows cannot be reconstructed from later ratings. Archive API pulls that were never captured for a tip date are permanently missing. The next NCAAM season must capture snapshots contemporaneously.

## Layers (strict separation)

| Layer | Contents | Mutability |
|---|---|---|
| **raw** | Exact source response bytes (KenPom archive JSON, ESPN scoreboard JSON, odds snapshots) | Immutable after write |
| **normalized** | Typed tables with schema_version, team-id resolution, quality flags | Append-only versions |
| **model-ready** | Lab fair inputs joined as-of tip with fail-closed eligibility | Rebuildable from raw+normalized by run_id |

Reconstruction must be possible from `run_id` alone: raw objects + manifests + code SHA.

## KenPom snapshot ingestion

### Storage

- Object store path: `s3://…/ncaam/kenpom/raw/season=YYYY/asof_date=YYYY-MM-DD/captured_at=<iso>/payload.json`
- Companion sidecar: `…/meta.json` with:
  - `captured_at` (ingestion clock, UTC)
  - `source_as_of` (KenPom archive date requested)
  - `source_response_sha256`
  - `schema_version`
  - `source` / `license` / `endpoint` (`archive&d=`)
  - `http_status`, `byte_length`
  - `operator`, `run_id`

### Cadence

- Daily during season (approved scheduled job), plus on-demand backfill **only** via KenPom archive endpoint for the requested `d=`.
- Backfill policy: never fabricate; if archive returns empty/error, record miss — do not substitute current ratings.

### Quality gates

- Team-identity resolution to B7; missing-team + duplicate detection receipts
- Completeness threshold (e.g. ≥350 D1 teams) or mark snapshot `incomplete`
- Late/missed-run alerts within SLA (e.g. 06:00 UTC next day)
- Retry with exponential backoff; exhausted retries → `missed` row in index, never silent skip

### Index / DB

- Table `kenpom_snapshot_index(asof_date, captured_at, object_uri, sha256, schema_version, completeness, status)`
- Lab as-of join: latest `asof_date ≤ tip` with `status=ok` only; else fail closed

### Forbidden

- End-of-season ratings assigned backward
- Current KenPom for historical dates
- Interpolation from future snapshots
- Reconstruction using games after target tip
- Annual CSVs treated as PIT
- Inferred historical ratings without separately governed model

## Schedule SoT + venue-status ingestion

Equivalent raw→normalized→model-ready stack:

- Raw ESPN (or designated SoT) scoreboard payloads per day/season
- Normalized games with: tip, B7 ids, `venue_status ∈ {home, neutral, unknown}`, scores when final, lineage
- Fail-closed unknown venue: never coerce null → home or neutral
- Conflict policy: single SoT; conflicting duplicates dropped with receipt
- Completeness / late-run / retry rules parallel to KenPom
- Manifests bind pack SHA-256 + as_of + season

## Lineage to model input

```
raw object (sha256) → normalize(run_id, code_sha) → model-ready join(run_id)
                                                  ↘ Lab materialize receipt
```

Every Lab parquet must embed:

- `kenpom_snapshot_uris` / hashes used per side
- `schedule_pack_uri` / hash
- `venue_status` + `venue_status_source`
- `materialize_run_id`

## Access control & secrets

- KenPom API key / odds credentials in secret manager only
- Raw bucket: write via ingestion role; read via analytics role
- No notebook path that can overwrite raw

## Monitoring

- Status endpoint: `/ops/ncaam/pit-ingest/status` → last success, misses, completeness
- Dashboard: season progress, gap list, alert state
- Disaster recovery: cross-region raw replica + quarterly restore drill
- External backup: offline cold copy (operator-owned) without weakening cloud SoT

## Season-boundary initialization

- Checklist before tipoff week 1: empty season partition, schema_version pin, identity map freeze, alert routes live, first archive capture verified

## Ownership / runbook

| Role | Responsibility |
|---|---|
| Data owner (Ryan) | License, offline archive policy, unseal authority |
| Platform | Object store, secrets, schedulers, alerts |
| Lab | Consume model-ready only; refuse non-PIT |

Runbook sections: daily verify, missed-run recovery, season open, season close seal, restore drill.

## Explicit non-goals for this phase

- No deploy, no schedule enablement, no API pulls, no backfill execution.
