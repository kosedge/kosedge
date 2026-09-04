# NCAAM Odds Path A — lake integrity (2026-09-04)

**Task:** Kos Edge #14 / #3 — Scorecard v1.2 on CURRENT Path A lake
**As of:** `2026-09-04T18:09:05.917785+00:00`
**Rules:** NO Odds API · NO `fetch_historical` · NO credit spend · Path A only
**Verdict:** **PASS**
**Scorecard gate:** `ok_to_rerun_locked_scorecard`

> Integrity receipt only. Does **not** retune Lab cuts, thresholds, features,
> or model. Does **not** light Edge Board / PLAY. B2 quarantine + board dark restated
> after scorecard grades land (see Scorecard v1.2).

## Inventory vs densify receipt (PR #482)

| | Expected | Observed |
|--|--------:|---------:|
| Open JSON | 463 | 463 |
| Close JSON | 463 | 463 |
| Open=close pairing | yes | yes |
| Parquet rows | 189609 | 189609 |
| Unique events | 15459 | 15459 |
| Matches expected inventory | — | yes |

### Pockets

| Start | End | Expected | Open present | Missing |
|-------|-----|--------:|-------------:|--------:|
| 2022-11-05 | 2023-04-11 | 158 | 158 | 0 |
| 2023-10-10 | 2024-04-15 | 189 | 189 | 0 |
| 2024-10-27 | 2025-01-16 | 82 | 82 | 0 |
| 2025-11-01 | 2025-12-04 | 34 | 34 | 0 |

Open span: `2022-11-05` → `2025-12-04`

## Open/close timestamp honesty (>7d)

- Open honest: **463**
- Open dishonest (>7d): **0**
- Open missing timestamp: **0**
- Close dishonest (>7d, informational): **0**
- Open honesty clean: **True**

## Event / team identity (fail-closed)

- Unique event_ids in open files: `15463`
- Empty event_id rows (raw): `0`
- Cross-day team-string diffs (raw): `16`
- Parquet event_id+book repeats (any open_time): `4759`
- True dups (same open_time): `0` (must be 0)
- Snapshot-grain repeats (diff open_time): `4759` (expected Path A)
- Home/away flips across snapshots: `12` (Odds API neutral-site quirk)
- Real non-flip team conflicts: `0` (must be 0)
- B7 both-sides resolve rate (Lab omit grain): `0.692` (home_unresolved=2520, away_unresolved=3463)

_Note:_ B7 unresolved is fail-closed Lab omit (not lake corruption). Multi-day event_id in open files is expected (same tip reappears across snapshot days). Home/away flips across days are a known Odds API neutral-site quirk.

## Line / price validity + missingness + outliers

- Null counts (parquet): `{"event_id": 0, "home_team": 0, "away_team": 0, "commence_time": 0, "book": 0, "open_time": 0, "close_time": 0, "open_spread_home": 1742, "close_spread_home": 1912, "open_total": 2778, "close_total": 3610}`
- Empty event_id / home / away rows: `0` / `0` / `0`
- open_time span: `{'min': '2022-11-05T12:00:00Z', 'max': '2025-12-04T12:00:00Z'}`

### Band checks (hygiene only — not Lab grade gates)

```json
{
  "open_spread_home": {
    "n_non_null": 187867,
    "min": -44.0,
    "max": 32.5,
    "mean": -5.380215790958498,
    "soft_outlier_n": 98,
    "hard_outlier_n": 0
  },
  "close_spread_home": {
    "n_non_null": 187697,
    "min": -64.5,
    "max": 43.0,
    "mean": -5.4551084993366965,
    "soft_outlier_n": 209,
    "hard_outlier_n": 3
  },
  "open_total": {
    "n_non_null": 186831,
    "min": 0.0,
    "max": 191.5,
    "mean": 143.15130519025215,
    "soft_outlier_n": 90,
    "hard_outlier_n": 19
  },
  "close_total": {
    "n_non_null": 185999,
    "min": 0.0,
    "max": 210.5,
    "mean": 143.1496083312276,
    "soft_outlier_n": 176,
    "hard_outlier_n": 20
  },
  "bands": {
    "spread_abs_soft": 40.0,
    "spread_abs_hard": 55.0,
    "total_soft": [
      100.0,
      180.0
    ],
    "total_hard": [
      80.0,
      220.0
    ]
  }
}
```

## Blockers / warnings

- Blockers: none
- WARN: event_id+book repeats across snapshot days (Path A grain): 4759 — expected
- WARN: Odds API home/away flips across snapshot days (neutral-site quirk): 12 events — Lab SoT D fail-closed / consensus; not densify corruption
- WARN: raw open home/away flips across days: 16
- WARN: hard line outliers (band check): 42
- WARN: soft line outliers (band check): 573
- WARN: B7 both-sides resolve rate 0.692 (<0.85) — Lab omit grain, not lake fail

## Explicit non-actions

- No Odds API / no `fetch_historical` / no Path B invent
- No Lab cut / threshold / feature / peek-tune changes
- No model rebuild (even if grades later land AMBER/RED)
- No Edge Board / PLAY / Conf%

## Machine receipt

`data/ops/ncaam-odds-lake-integrity-20260904.receipt.json`

## Next

If verdict PASS → rematerialize Train-A/Test-A from current Path A parquet (locked cuts) → Scorecard v1.2 vs frozen v1.1 (same protocol gates).
If FAIL → stop; diagnose here; do not rebuild model.

