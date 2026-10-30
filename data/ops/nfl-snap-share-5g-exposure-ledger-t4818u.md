# t4818u — snap-share `_5g` baseline_personnel_ref EXPOSURE LEDGER (DRAFT)

Authority: DECISION d48d15bc · ORDER 4f5811dc · contract 0614bdcc · IF window 205f33e0 (`5G_ONLY`) · RATIFY d4acc170 · autonomy 2497781d

**Status:** DRAFT engineering only. Not wired. Not admitted. Not scored.

t4822u as-of correction (separate DRAFT): `data/ops/nfl-if-665-asof-correction-t4822u.md`.
Pin `1b39f4e9` same-week matchup join is preserved as the original reference;
do not treat this t4818u note as the corrected join.

## What was built

Isolated package (no IF / nowcast / index / #664 activate / routes / tasks imports):

| Path | Role |
|---|---|
| `services/model-service/src/services/nfl_snap_share_exposure_ledger/` | Ledger builder |
| `…/schema.py` | Types, reject codes, `window=5g`, IF contract cite |
| `…/window.py` | Exact IF `_5g` game-set resolver |
| `…/builder.py` | Game-level snap-share mean; fail-closed UNKNOWN |
| `…/identity.py` | Canonical JSON + content hashes |
| `services/model-service/tests/test_nfl_snap_share_exposure_ledger.py` | Synthetic +/− tests |
| this file | Data-dependency report + next-decision |

**Question answered:** which players, and how much of their participation, sit in each team's IF `_5g` historical rating window.

**Question not answered (and not attempted):** how many points those players are worth.

## Window contract (exact IF `_5g`, not latest-five)

Independent Fair consumes `*_5g` fields on `NflGameInputs` (`nfl_simulator.py` @1b39f4e9). Those fields are the rolling row at `(season, rating_week, team)` from:

```
nfl_dp_team_situational_weekly WHERE season=:season
PARTITION BY team ORDER BY season, week
ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
```

Cite: `services/model-service/data_platform_nfl/ingest.py@1b39f4e9` L1305–1314.

`nfl_dp_team_rolling_features_weekly` stores aggregates + `games_in_window_5` only. **Game IDs are not persisted.** The builder reconstructs them from caller-supplied situational rows (same grain) plus a schedule join (exactly one completed `game_id` per selected week).

A convenient “latest five scheduled games” query **can disagree** (bye with no situational row; week present on the schedule but missing from situational because of ingest filters). Tests prove the divergence and reject using the convenient set.

CURRENT ROW at `rating_week` is included because that is what the IF-consumed SQL frame does. Contract 0614bdcc prose also said “weeks < target week” as as-of language — see residuals.

## Missing-data semantics (binding)

| Case | Result |
|---|---|
| Verified complete participation record; player not in that game’s snap list | explicit `verified_zero` (0), **kept in the 5-game mean** |
| Incomplete or missing snap source for a window game | `SNAPS_INCOMPLETE` / `SNAPS_MISSING` — UNKNOWN, fail closed |
| Empty bundle marked complete | `SNAPS_INCOMPLETE` |
| Missing PFR→GSIS link | `ID_UNMAPPED` |
| Invalid pct / snaps contradiction | `INVALID_SNAP_DENOMINATOR` |
| Window shorter than 5 situational rows | `WINDOW_SHORT` (week &lt; 5) or `WINDOW_INCOMPLETE` |
| Multi-game week / two schedule ids | `GRAIN_MISMATCH` |
| Unsupported `source_id` | `SOURCE_UNSUPPORTED` |

Verified 0 and UNKNOWN are not interchangeable. Zeros are never fabricated for unknown participation.

## Data-dependency report (independently verified on `deploy-vercel` @1b39f4e9)

### Required inputs to produce a live ledger

| Input | In-repo status | Notes |
|---|---|---|
| IF `_5g` window definition | EXISTING AND VERIFIED (code) | ingest SQL cited above; no persisted game-id list |
| `nfl_dp_team_situational_weekly` rows for the rating season | SCHEMA EXISTS; 2026 rows NOT in git | Runtime DB only; builder does not query DB |
| `nfl_dp_schedules` join (season, week, team) → `game_id` | SCHEMA EXISTS; data NOT in git | Required to recover game IDs |
| Game-level snap counts (offense_pct / defense_pct) | SCHEMA EXISTS (`nfl_dp_snap_counts_weekly` in `infra/db/037` + `038`) | Ingest path: `snap_depth_ingest.ingest_snap_counts` via `nfl.load_snap_counts` |
| 2026 snap rows | **MISSING in-repo** | No `*.parquet` snap files; no `research-store/snaps`; find over workspace for `*snap*count*` = empty |
| 2013–2025 snap parquets | **MISSING in-repo** | Contract 0614bdcc cited a research parquet that is **not present** on this tree |
| PFR→GSIS identity map | **NO static artifact** | Runtime only: `snap_depth_ingest._pfr_to_gsis_map()` → `nfl.load_players()`. DB graph `nfl_player_source_id_map` is schema-only here |
| Position → offense/defense side | EXISTING BUT UNVERIFIED (code convention) | Builder uses an explicit allow-list; ST-only fails closed |
| Official injury report | NOT USED | Delta-only in 0614bdcc; out of scope |
| `games_in_window_5` cross-check | OPTIONAL | If supplied and ≠ 5 resolved games → `WINDOW_MISMATCH` |

### Honest support verdict

**Approved in-repo data cannot support a live 2026 (or any season) exposure ledger today.**

The builder is a pure function over caller-supplied facts. This checkout has:

- no NFL snap parquets
- no research-store
- no checked-in PFR↔GSIS map
- no 2026 snap facts
- no persisted IF `_5g` game-id lists

A future data CLEAR must admit (with provenance/as-of):

1. the exact situational weeks that fed each IF `_5g` row, **or** a new materialized `rolling_5g_game_ids[]`
2. complete game-level snap bundles for those game IDs
3. a certified PFR→GSIS map covering every snap-keyed player
4. completed schedule rows for the same weeks

Until then the only valid outputs are synthetic ledgers.

## Deterministic test evidence

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest -q tests/test_nfl_snap_share_exposure_ledger.py
# 28 passed in 0.06s
```

Coverage: IF `_5g` situational frame ≠ latest-five schedule; verified 0 kept in the mean; incomplete/missing source = UNKNOWN (not 0); short/incomplete windows; identity unmapped + mid-window PFR change; provenance; invalid denominators; ST/unknown position; as-of; grain mismatch; fingerprints; isolation.

## Isolation / HOLD preserved

- Does not import `nfl_simulator`, `injury_nowcast`, `nfl_hhl1_capture`, `src.tasks`, `src.routes`, `data_platform_nfl`, or nflverse
- Does not activate #664, alter offense/defense index, or modify Independent Fair
- No merge / deploy / E1 / Odds / C10 / CERT / subscriber-facing
- `starter_label_derived` is the demoted ≥50% descriptive label only

## Residuals (do not silently resolve)

1. **CURRENT ROW vs “weeks &lt; target week”.** t4818u followed the pin join (CURRENT ROW at the consumed `rating_week`, which was same-week). t4822u DRAFT binds `rating_week = target_week − 1` and keeps CURRENT ROW only as completed-data. See `nfl-if-665-asof-correction-t4822u.md`.
2. **offense_index / defense_index lookback** still untraced (205f33e0 residual). Ledger must not be applied to those indices.
3. **injury_nowcast overlap** if anyone later applies this ledger as a second personnel Δ.
4. **Railway runtime bytes** UNVERIFIED.
5. Mid-window team changes: only this team’s window games are counted; other-team snaps are out of scope.
6. Return-from-absence uplift remains RETURN_UNCREDITED (not in this builder).

## Next-decision recommendation (Needs Ryan / data CLEAR)

1. **Data CLEAR (blocking for any non-synthetic use):** admit 2026 (or research) snap source + provenance + PFR↔GSIS map. Do not assume nflverse runtime fetch is certified.
2. **Ryan CLEAR (window as-of):** confirm CURRENT ROW at the IF-consumed `rating_week` is the intended personnel window vs a strictly lagged `weeks < target` window.
3. **Not yet:** impact weights, injury points, IF wiring, nowcast activate, #664 live capture, merge/deploy.

Smallest useful follow-up after (1)+(2): a read-only loader that materializes `rolling_5g_game_ids[]` from situational+schedule without changing ingest averages — still DRAFT, still not scored.
