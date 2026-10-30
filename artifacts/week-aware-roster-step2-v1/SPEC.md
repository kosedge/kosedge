# Revised week-aware implementation SPEC (Step 2)

Normative parent: `evidence/IMV_SPEC_NFL_WEEK_AWARE_ROSTER_LEAKAGE_v1.txt`
sha8 `8eb532c1`. INV-1 D/E draft accepted as draft; this file is the
implementation SPEC for the leakage-test package. It does **not** pin a
production roster SoT or invent weekly coverage.

## G-PIT (HARD)

No historical model input may have `availability_ts` later than
`prediction_cutoff` for that game.

```
prediction_cutoff = min(kickoff_utc, decision_ts) if decision_ts else kickoff_utc
```

Cutoff must be `<= kickoff`. Ingest/`updated_at` is never
`availability_ts`.

Inequality (fail closed; no closed-at-cutoff freeze yet):

- `availability_ts < prediction_cutoff` → eligible
- `availability_ts == prediction_cutoff` → **not eligible**
- `availability_ts > prediction_cutoff` → FAIL / blocked
- missing/naive `availability_ts` → MISSING_TS; refuse; do not coerce

## Reconstruction (membership / depth / role)

Grain: `(season, week, game_type, team, player_id)`.

Eligible row for a REG game:

- `season` match
- `game_type == REG` (playoff rows ineligible for REG)
- `week` of the row `<=` game week (look-back only)
- `availability_ts < prediction_cutoff`
- If several: latest `week`, then latest `availability_ts`

Missing weekly row → `MISSING_ROW`. Never infer from a later week,
season snapshot, or W1 week-label pack.

Depth: `depth_order` on an eligible depth row. Starter = `depth_order == 1`
for that position group. **Not** `STARTER_SLOTS` token membership.
Default `depth=2` is forbidden. Missing depth → `MISSING_ROW` for role.

QB1: the single eligible `position==QB` and `depth_order==1` player.
Multiple QB-slot rows are not all QB1.

Identity: `TEAM_MATCH` only if week-aware member. Season-union fallback
is removed. Unresolved → NULL per existing null contract.

Continuity: current side = week-aware membership. Prior side = last
eligible prior-season REG weekly book, or UNKNOWN/`None` if missing
(E-1). Current-season union is forbidden. R-6 is **not** claimed for
the old path.

Injury status: listings only, `report_time < kickoff`. Roster `RES`/`INA`
on a later snapshot must not mark week-1 status (T-PIT-5).

## Sources (not SoT pins)

| candidate | use in Step 2 |
| --- | --- |
| Season-level `roster_YYYY.csv` | SUPERSEDED; G-PIT mode hard-STOPs this loader (T-PIT-10) |
| W1 packs 2019–2023 | week-label `as_of`; **not** capture-time; **ineligible** for reconstructible |
| W1 packs 2024–2025 | holdout-era **DO-NOT-OPEN** |
| 2026 UTC snapshots | wrong era |
| owned-DB NDJSON | ingest timestamps; 2025-W1 only; not used |
| weekly archive with capture-time | MISSING (NR-1). Until it exists, development weeks are ineligible |

No candidate is pinned as SoT. Reconstructible count must stay 0 until
a later Step 3-approved source with real `availability_ts` exists.

## Missingness codes

`OK` | `MISSING_ROW` | `MISSING_TS` | `INELIGIBLE_PLAYOFF_FOR_REG` |
`INELIGIBLE_WEEK_LABEL` | `BLOCKED_SEASON_SNAPSHOT` | `TS_AFTER_CUTOFF` |
`TS_EQUAL_CUTOFF`

Fail closed: never invent; never zero-fill a missing PIT field to keep
a game eligible.

## Feature manifest (T-PIT-8)

Classes: injuries, rosters, depth, transactions, QB changes, odds,
weather. Each must declare `availability_ts` or
`EXEMPT-WITH-RYAN-REASON`. None are exempt in this package.

## Scoring

See `scoring-rule-delta.md`. No delta.

## Tests

T-PIT-1..10 on synthetic 2098/2099. Then development coverage on
`leakage/fixtures/dev_game_keys_le2023.json` (schedule keys 2013–2023
REG only; no roster bytes; no 2024/25). Expected answers are under
`leakage/expected/` and were committed before the harness sha.
