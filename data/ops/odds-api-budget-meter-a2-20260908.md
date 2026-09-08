# Odds API budget warehouse meter + snapshot skip-dup (A2)

**Date:** 2026-09-08  
**Status:** draft PR only — **do not merge** until Validation skim + CoS gate  
**Scope:** hottest warehouse path = Celery `pull_odds_snapshot` (PROD_LIVE beat)

## What shipped (code)

1. **Credit ledger attribution** on `odds_api_credit_ledger` (additive DDL):
   - `bucket` (default `UNATTRIBUTED`; beat sets `PROD_LIVE`)
   - `caller` (beat: `celery.pull_odds_snapshot`)
   - `run_id` (one UUID per task invocation, shared across sports)
   - denorm `markets` / `regions` from request params when present
2. **Beat metering:** after each `fetch_odds_with_metadata` (success or failed),
   `_record_odds_api_request` writes the ledger. Historical densify/backfill
   callers pass `bucket=HIST_BACKFILL` (no HIST behavior change; no new bulk pulls).
3. **Snapshot write de-dupe:** `_persist_odds_events` skips INSERT when
   `(game_id, sportsbook_id, market_id, captured_at)` already exists; returns
   `snapshots_skipped_dup`. Different `captured_at` values still insert.
4. **Optional** `ingest_run_id` on `odds_snapshots` (nullable ALTER IF NOT EXISTS);
   beat passes the shared `run_id`.

## Hard stops

- **Do not merge** this PR as an ops “done” claim — Validation skim first.
- **No HIST backfill** / densify / plan upgrade from this change.
- **No live Odds API calls** in CI/tests (mocked fetch only).
- **No beat-path fetch cache** / assemble / fair-lines live fetch de-dupe —
  Platform owns WS-02 (B/D). Ledger upsert into `odds_api_request_cache` remains
  the existing record-helper side effect; beat does **not** skip fetches from it.
- **No alerts** 50/70/85/95 in this PR.
- Fair-lines GET `persist=0` (#503) must stay green.

## Verify (mocked / warehouse)

```sql
-- After a beat pull_odds_snapshot on Railway:
SELECT bucket, caller, run_id, sport_key, status, credits_used, credits_remaining, markets, regions
FROM odds_api_credit_ledger
WHERE bucket = 'PROD_LIVE'
ORDER BY requested_at DESC
LIMIT 20;

SELECT COUNT(*) AS snaps, COUNT(DISTINCT ingest_run_id) AS runs
FROM odds_snapshots
WHERE ingest_run_id IS NOT NULL;
```

## Out of scope (explicit)

- Assemble / fair-lines Odds fetch de-dupe (WS-02)
- Alerts thresholds
- HIST bulk credit spend
- Merging / promoting this branch
