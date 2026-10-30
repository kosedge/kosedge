# t4822u — IF matchup as-of join + #665 lag guard (DRAFT)

Authority: DECISION 312d4c65 · ORDER 9c9f7cfc · Alex finding 4219a1bb (ACCEPT) ·
prior as-of 5e572074 · #665 tip `877e2f95` · IF pin `1b39f4e9`.

**Status:** DRAFT engineering only. Not merged. Not rematerialized. Not scored.
Sealed #657 / `1b39f4e9` remains the original IF lineage reference. This note
documents the corrected join on the #665 DRAFT lineage.

HARD preserved: ≠snap admit ≠historical rescore ≠E1 ≠capture ≠merge ≠deploy
≠Odds ≠C10 ≠CERT ≠weights ≠publication. W8 DATA_READY unchanged. NFL NO-GO ·
CERT=0 · Coming Soon ON · F2 frozen.

## Trace (verified on this tree)

| Token | Meaning | Pin @1b39f4e9 | This DRAFT |
|---|---|---|---|
| `_5g` SQL frame | `PARTITION BY team ORDER BY season, week ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` on `nfl_dp_team_situational_weekly` | L1305–1314 | **Unchanged** |
| `rating_week` | Completed-data week = CURRENT ROW of that frame | Implicitly the schedule week | Explicit completed-data week |
| `target_week` | Forecast target (schedule week of the game being forecast) | Not distinguished | Required |
| Matchup join | Rolling row attached to a schedule game | `h.week = s.week` (L1497–1501) | `h.week = (s.week - 1)` |
| #665 resolver | Window at caller `rating_week` | No `target_week`; CURRENT ROW at that week | `rating_week = target_week - 1`; reject target/future |

CURRENT ROW is legal only when that row is completed historical information
available before the target forecast cutoff. Same-week join made CURRENT ROW
the target game itself on historical / backtest materialization.

## Changed historical forecast semantics (not rescored here)

If matchup features are rematerialized later (not authorized in this task):

- A Week-W game's `*_5g` fields become the rolling row at Week W−1, not Week W.
- Backtests that previously ingested the target game's own situational stats
  into raw Independent Fair will move to a strictly pregame window.
- Week-1 targets have no prior rating week → NULL `_5g` (fail closed).
- Bye / missing Week W−1 rolling row → NULL `_5g`. No `MAX(week) < target`
  substitute. Contiguous pipeline only.

Stored `nfl_dp_matchup_features_weekly` rows are **not** rewritten by this PR.
SQL is the future materialization contract. #657 pin remains citable.

#665 ledger schema version `snap-share-exposure-ledger-v0-t4818u` →
`snap-share-exposure-ledger-v0-t4822u`. Fingerprints now include `target_week`
and the pregame contract string. Same facts without a target context are
rejected (not silently hashed). Hash algorithm unchanged.

## Shared admissible window

`src/services/nfl_pregame_asof.py` is the single lag rule:

1. Every consumed underlying game completed, required source available before
   the target forecast cutoff.
2. `rating_week = target_week - 1` (contiguous weekly IF pipeline).
3. Target-week and future games cannot enter the IF baseline or the ledger.
4. Stale / bye / missing-week / incomplete-source → explicit reject.

`tasks.py` `_fetch_rolling_feature_latest_rows` (`week <= week_cap`) is a
different consumer and is **out of this bounded correction**.

## Follow-up (ORDER 5071e31a) — Alex `5f2e9756` defects

Closed on this DRAFT lineage (not a new PR):

1. `forecast_cutoff_ts` is mandatory on ledger / window entry. Every window game must have `kickoff_ts` or `game_date`; absence fails closed (GAP-A).
2. `_lookup_target_schedule` raises `SCHEDULE_UNRESOLVED` when the target-week game is missing — never `None` that skips the date guard (GAP-B).
3. Executed sqlite fixture runs `IF_MATCHUP_PREGAME_FROM_SQL`: Week-W gets the W−1 rolling row; target-week stats cannot enter; W−1 bye → NULL.
4. `fetch_latest_matchup_feature_pack` no longer has the priority-1 latest-week `UNION ALL`. Missing `game_id` or NULL core `_5g` raises `MatchupFeatureReject`.

## Tests

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest -q \
  tests/test_nfl_if_pregame_asof.py \
  tests/test_nfl_snap_share_exposure_ledger.py \
  tests/test_nfl_matchup_features.py::test_matchup_pack_sql_has_no_latest_week_fallback \
  tests/test_nfl_matchup_features.py::test_fetch_matchup_pack_rejects_missing_game_id \
  tests/test_nfl_matchup_features.py::test_fetch_matchup_pack_rejects_null_5g \
  tests/test_nfl_matchup_features.py::test_fetch_matchup_pack_returns_game_id_row
# 54 passed in 0.22s
```

## Isolation / HOLD

No IF wiring, nowcast, index, #664 activate, Odds, C10, CERT, E1, snap admit,
or historical rematerialize. Ledger package still does not import simulator /
tasks / routes / data_platform_nfl.
