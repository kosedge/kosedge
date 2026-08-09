# NFL Data Integrity Gate — Phase 1 Ops Note (2026-08-09)

Branch: `feat/nfl-data-integrity-gate-20260809` → `deploy-vercel`.

Depends on: #160 (SoT exclusive), #161 (daily WAS/intel path).

## Goal

Turn roster integrity from a one-off fix into permanent infrastructure. Fail the build / daily job on conflict, missing QB1, share blow-up, or stale policy. Every projection must answer: **which roster snapshot produced this?**

## Snapshot

| Field | Value |
|-------|-------|
| **snapshot_id** | `nfl-depth-2026-w1-20260809T190000Z` |
| **as_of** | `2026-08-09` |
| **daily_intel_as_of** | `2026-08-09` |
| **pack SHA256** | `ee1a3caa7a78cc2e48b8ef2abd5fe03f9b72a77e7812d450895b351b102f49fe` |
| **Archive** | `services/model-service/.../data/snapshots/nfl-depth-2026-w1-20260809T190000Z.json` |
| **Active pointer** | `.../data/snapshots/ACTIVE_SNAPSHOT.json` |
| **Teams touched** | 32 (full sim set) |

Design: `data/ops/nfl-data-integrity-design-20260809.md`.

## Validator results

| Check | Result |
|-------|--------|
| `stable_identity_player_id` | PASS |
| `duplicate_active_assignment` | PASS |
| `missing_qb1` | PASS |
| `critical_role_gaps` (QB1/RB1/WR1/TE1 + unique slots) | PASS |
| `usage_share_limits` | PASS |
| `stale_snapshot` (max_age_days=7 vs 2026-08-09) | PASS |
| `engine_web_roster_agreement` (sampled QB1) | PASS |
| `snapshot_id_present` | PASS |

**Gate: PASS** — downstream re-sim allowed. Phase 2 unblocked only while green.

Machine report: `data/ops/nfl-data-integrity-gate-20260809.json`.

## Hygiene fix discovered by the gate

WAS Stefon Diggs had been packaged with Davante Adams' GSIS (`00-0031381`). Corrected to **`00-0031588`** in the active pack + packager `SOT_SKILL_OVERRIDES` so re-pack cannot reintroduce the collision.

## Fail-proof

Intentional bad snapshot (ATL QB1 forced to share ARI QB1 `player_id`) → gate **FAIL** on `duplicate_active_assignment`. Pytest covers duplicate / missing QB1 / role gap / stale / share blow-up fixtures.

## Lineage attachment points

| Output | Where |
|--------|--------|
| Research `run_summary.json` | `lineage` + top-level `snapshot_id` |
| `survivor_week1_evaluate.json` | `lineage` + `snapshot_id` |
| Game-box (`project_game_player_boxes`) | `notes.lineage` / `notes.snapshot_id`; diagnostics when requested |
| Universe / schedule meta | `snapshot_id`, `pack_sha256`, `daily_intel_as_of` |
| Web depth loader | `playerId` + `snapshotId` on each `DepthRow` |

### Deferred gaps (explicit — not silent)

1. `PlayerRole` still keys sim math on synthetic `player_key`; GSIS joined at export/lineage only.
2. OL→EPA remains stub (`documented_not_magical`).
3. Fantasy season aggregates on web may omit lineage until board writers pass `snapshot_id`.
4. `player_season_totals.json` remains a bare list; lineage lives on sibling `run_summary.json`.

## Daily job hook

```bash
bash scripts/nfl/run_daily_roster_injury_intel.sh --gate     # archive + validate
bash scripts/nfl/run_daily_roster_injury_intel.sh --verify   # gate + SoT exclusive assert
bash scripts/nfl/run_daily_roster_injury_intel.sh --sim      # gate then re-sim
```

Ops notes must include: `snapshot_id`, validator pass/fail, teams touched.

## Tests

```bash
cd services/model-service
PYTHONPATH=. pytest tests/test_nfl_data_integrity_gate.py -q
```

## Phase 2

**Blocked until this gate stays green** on CI + daily intel path.
