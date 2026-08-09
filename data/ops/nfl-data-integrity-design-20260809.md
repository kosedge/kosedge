# NFL Data Integrity Gate — ID + Snapshot Design (2026-08-09)

Phase 1 of the formal data-integrity program. **Phase 2 feature work is blocked until this gate is green.**

## Identity scheme

| Layer | Key | Role |
|-------|-----|------|
| Depth SoT pack | `player_id` | **Primary join** — nflverse GSIS (`00-#######`) when known; unique stubs (`TEAM-POS-N` / alternate ids) only when GSIS missing |
| Pack metadata | `identity_scheme: nflverse_gsis_player_id` | Documents the rule |
| Engine `PlayerRole` | `player_key` (`TEAM-POS{n}-Name`) | Sim math key (synthetic); GSIS travels in pack rows + lineage |
| Web / fantasy depth | `playerId` + `snapshotId` | Same pack file; names are display / match-assist only |
| Future bridge | `nfl_player_identities.player_uid` | Optional UUID map via `source_system=nflverse_gsis` — not required for Phase 1 |

**Rule:** Names and team strings never join sim/fantasy/edge production paths as the source of truth.

## Snapshot scheme

| Field | Meaning |
|-------|---------|
| `snapshot_id` | `nfl-depth-{season}-w{week}-{YYYYMMDDTHHMMSSZ}` on the active pack |
| `as_of` / `as_of_timestamp` | Effective date of the depth snapshot |
| `daily_intel_as_of` | Last daily intel apply date |
| Archive | `services/model-service/.../data/snapshots/{snapshot_id}.json` + `ACTIVE_SNAPSHOT.json` |

A simulation run records `snapshot_id` (and pack SHA) on `run_summary.lineage`, survivor payloads, and game-box `notes.lineage`. Re-running a past slate: load the archived snapshot file (or pin `snapshot_id` on the run) — minimum bar is **store snapshot_id on outputs**.

## Validators (hard-fail)

| Check | Fail when |
|-------|-----------|
| `stable_identity_player_id` | Any skill row missing `player_id` |
| `duplicate_active_assignment` | Same `player_id` active on two teams |
| `missing_qb1` | Any sim-set team lacks QB depth_order=1 |
| `critical_role_gaps` | Missing RB1/WR1/TE1, or duplicate `(team,pos,depth)` slot |
| `usage_share_limits` | Modeled rush/target (+ other) off 1.0, or named sum > 1.50 |
| `stale_snapshot` | `as_of` older than `max_age_days` (default 7) vs reference date |
| `engine_web_roster_agreement` | Sampled QB1 `player_id` disagrees when both read same pack path |
| `snapshot_id_present` | Active pack lacks `snapshot_id` |

No soft warnings for these in CI or the daily job — **exit non-zero**.

## Wiring

- Module: `nfl_season_engine/data_integrity.py`
- CLI: `scripts/nfl/run_data_integrity_gate.py`
- Daily: `scripts/nfl/run_daily_roster_injury_intel.sh --gate|--verify|--sim` (gate before re-sim)
- Pytest: `tests/test_nfl_data_integrity_gate.py` (CI via model-service pytest)
- Fail-closed load: `NFL_DEPTH_INTEGRITY_FAIL_CLOSED=1`

## OL→EPA stub

`ol_roles` + `camp_intel.ol_efficiency_hooks` remain **documented_not_magical**. No invented OL→EPA power in Phase 1.
