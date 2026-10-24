# INV-1.B — owned source candidates

Classifications are IMV's four: EXISTING AND VERIFIED | EXISTING BUT
UNVERIFIED | MISSING | SUPERSEDED.

No candidate below is pinned as SoT. Usable-for-pre-2024-fit means
"could this file, as it sits, supply G-PIT `availability_ts` for
week-aware membership/depth without opening 2024/25?" — almost none can.

## Rechecks performed this pass

1. Local repo + owned-data dump + season-engine packs (opened 2019–2023
   and 2026 metadata only; 2024/2025 W1 pack **contents unread**).
2. `/Volumes/KosEdgeData` — **not mounted** on this box.
3. Google Drive MCP search (`DATA_ASSETS.md`, `INVENTORY_v1.md`,
   `KosEdgeData`, `nflverse roster`, `research-store`) — **zero files**.
   `list_recent_files` returned unrelated website docs. Grant appears
   `drive.file` (app-visible files only), so absence here is **not**
   proof the Mac drive is empty.
4. Notion search — no DATA_ASSETS / weekly-roster register page found.
5. Local `DATA_ASSETS.md` / `INVENTORY_v1.md` / `research-store` —
   **not on this checkout**. IMV cited `DATA_ASSETS.md` sha8 `8ca7c553`
   and box `INVENTORY_v1.md` sha12 `cf9ebb2ffb27`; those bytes were not
   hashed here.

See `evidence/drive-research-store-check.md`.

## Candidates

### B1. Season-level `roster_YYYY.csv` (injury-fit raw-le2023)

- Coverage: 2012–2023, one row per `(team, gsis_id)`.
- Schema: nflverse seasonal roster including `week`, `game_type`,
  `status`, `depth_chart_position`.
- `availability_ts`: **none**. `week` is a snapshot stamp (often 17/18
  REG or 18–22 playoff), unused by loaders.
- Revisability: nflverse re-release can rewrite the file.
- Class: **SUPERSEDED** as a holdout / "pre-kickoff" SoT.
  **EXISTING AND VERIFIED** as the leaky source (structure counted
  2013–2023; 2023 sha `f98283e6`).
- Usable for pre-2024 week-aware fit: **NO**.

### B2. Historical W1 depth packs (2019–2023 opened)

Path: `services/model-service/src/services/nfl_season_engine/data/historical/nfl_depth_chart_{2019..2023}_w1.json`

- Coverage: week **1 only**, skill slice, seasons 2019–2023 verified.
- Schema: `season, week, as_of, cutoff_rule, source, rows[]`
  (`team, position, depth_order, player_id, player_name, depth_slot`).
- `availability_ts`: **week-label only**. Example 2023:
  `as_of: "2023-W1-REG"`, `cutoff_rule: "nflverse week=1 game_type=REG"`.
  No capture-time UTC. README: `≤2024` = nflverse week=1 REG.
- Revisability: derived from current nflverse release
  (`source: nflverse_depth_charts_historical`).
- Class: **EXISTING AND VERIFIED** as W1 week-label packs; **not**
  archived capture-time PIT.
- Usable for pre-2024 week-aware fit: **NO** for weeks 2–18; **NO** as
  certifiable W1 PIT (no capture-time).

2024/2025 W1 files exist on disk (sizes 70910 / 78884). Contents were
**not read**. Class for those two files: **EXISTING BUT UNVERIFIED**
(filename/size only). Not used.

### B3. 2026 W1 packs + UTC filename snapshots

- `nfl_depth_chart_2026_w1.json`: `as_of_timestamp: 2026-08-13T12:00:00Z`
- `data/snapshots/nfl-depth-2026-w1-20260813T120000Z.json`
- `data/snapshots/nfl-depth-2026-w1-20260809T190000Z.json`
- Coverage: 2026 week 1 only.
- Class: **EXISTING AND VERIFIED** capture-time *filename / as_of_timestamp*,
  **wrong era** for pre-2024 fit.
- Usable for pre-2024 fit: **NO**.

### B4. Owned-DB NDJSON `data/ops/nfl-owned-data-20260705T201049Z/`

- `nfl_dp_rosters.ndjson`: n=3133, seasons **{2025 only}**, keys
  `jersey_number, player_id, player_name, position, season, source, team, updated_at`.
  No `week`. `updated_at` sample `2026-07-05T16:10:31…` (ingest).
- `nfl_dp_depth_chart_weekly.ndjson`: n=3133, seasons **{2025 only}**,
  weeks **{(2025, 1) only}**, keys include `week` + `updated_at`
  (same 2026-07 ingest), `inferred_source: v1_usage_roster_injury`.
- Class: **EXISTING AND VERIFIED** as a 2025-W1 ingest dump with
  ingest timestamps, not as-of. Tiny / wrong era / not PIT.
- Usable for pre-2024 fit: **NO**. 2025 player rows were not used as
  holdout reconstruction.

### B5. Injury listings le2023 (week-keyed)

v6 seeded `listings_{2013..2023}.csv` with `date_modified`.
`last_report_before_kickoff` already clips `report_time < kickoff`.
- Class: **EXISTING AND VERIFIED** for *injury status* as-of (IMV
  judged safe). Not a roster/depth reconstruction source.
- Usable for pre-2024 *roster* fit: **NO** (wrong feature).

### B6. Live nflverse / `nfl.load_rosters` ingest path

`ingest.py` calls `nfl.load_rosters(seasons=)` into `nfl_dp_rosters`
(season grain). `materialize_depth_chart_weekly` reads that season
table and stamps a week from usage (post-game).
- Class: **EXISTING AND VERIFIED** as code path; output on this box
  is B4. Not an archive.
- Revisability: high (live pull).
- Usable for pre-2024 certifiable PIT: **NO**.

### B7. KosEdgeData drive (`/Volumes/KosEdgeData`)

Documented in ops notes as the Mac HD lake (`clean/nfl/research`,
`raw/odds`, CFB pbp). **Not mounted** here. Drive MCP did not list it.
- Class: **EXISTING BUT UNVERIFIED**.
- Usable: **unknown**. Needs-Ryan to confirm contents (see C). No buy.

### B8. Research-store

No local directory, no Notion page, no Drive hit for `research-store`.
- Class: **MISSING** on this box; **EXISTING BUT UNVERIFIED** if it
  exists only on Ryan's Mac.
- Usable: **unknown**. Needs-Ryan (see C). No buy.

### B9. Register entry for a week-aware roster asset

`DATA_ASSETS.md` / week-aware register — not on this checkout.
- Class: **MISSING** (this box).

### B10. Permanent T-PIT automated suite

This INV-1 files the **plan** (F). Code + expected answers + receipts
are not implemented (Step 2 after INV-1 PASS).
- Class: **MISSING**.

### B11. Odds / weather / transaction archives

Odds API purchase **ON HOLD**. No owned historical transaction feed
with announcement `availability_ts` was found on this box.
- Class: **MISSING** for certifiable PIT of those classes.
  Not proposing purchase.

## Summary

| id | class | pre-2024 week-aware usable |
| --- | --- | --- |
| B1 season roster CSV | SUPERSEDED (as SoT) / EXISTING AND VERIFIED (as leak) | NO |
| B2 W1 packs 2019–23 | EXISTING AND VERIFIED (week-label, not capture-time) | NO |
| B2b W1 packs 2024–25 | EXISTING BUT UNVERIFIED (unread) | NO (unread; holdout era) |
| B3 2026 capture-time W1 | EXISTING AND VERIFIED (wrong era) | NO |
| B4 owned-DB NDJSON | EXISTING AND VERIFIED (2025 ingest ts) | NO |
| B5 listings as-of | EXISTING AND VERIFIED (injury status only) | NO for roster |
| B6 live nflverse ingest | EXISTING AND VERIFIED (code; not archive) | NO |
| B7 KosEdgeData | EXISTING BUT UNVERIFIED | unknown |
| B8 research-store | MISSING here / UNVERIFIED on Mac | unknown |
| B9 register entry | MISSING | NO |
| B10 T-PIT suite | MISSING | n/a |
| B11 txn/odds/weather PIT | MISSING | NO |
