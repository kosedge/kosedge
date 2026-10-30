# t4833u — research-only snap-share `_5g` exposure ledger (MATERIALIZE)

Authority: DECISION_RYAN_t4833u_RESEARCH_5G_EXPOSURE_LEDGER **09f8a926** ·
ORDER **65c1b150** · Accept FEASIBLE_RESEARCH **b7e3a32a** · PR PASS_PULL **bc59decd** ·
as-of CLOSED **cf514078** · tip **1010b86f** · contract `d4acc170` / `0614bdcc`.

**Status:** DRAFT research artifact only. ≠admit ≠merge ≠live ingest ≠scoring
≠injury weights ≠experiments ≠publication. NFL NO-GO · CERT=0 · Coming Soon ON ·
F2 frozen. E1 / W8 / #663 / #664 / C10 / CERT / F2 untouched.

CC-BY-4.0 research attribution (nflverse-data). RETURN_UNCREDITED.
`starter_label_derived` (≥50%) is a descriptive label only.

## Seal

| Item | Value |
|---|---|
| Artifact | `data/research/nfl/t4833u/snap_share_5g_exposure_ledger.parquet` |
| Rows / cols / bytes | 3,398 / 51 / 263,601 |
| **output sha256** | `2454f0948a649e02f4319a4ae07fa173327a7a895fae6d3be0b2397318001f88` |
| Schema | `research-snap-share-5g-exposure-ledger-v0-t4833u` |

### Input pins (verified before use; no additional acquisition)

| File | sha256 |
|---|---|
| snap_counts_2026.parquet | `81a1e6f5838be0bc5fa11155ed95e39cd535dcb61745aec0ca2bba9287421241` |
| players.parquet | `b6dd0c868c68b4854d212fbb71ea8f7b562beae6daf5d5dc83c3d88c7c40a647` |
| roster_weekly_2026.parquet | `7ba8d815277b2ea49a82282d9e22b0ce11d38508a11781ddf8b155f9111a76f2` |
| bundle zip (attached) | `4cf83bffcd018d180b7ebef3a3386232bc8c8118d8e949c2777422b342443b0b` |

Completion inferred from snap presence (no schedule/score file in the batch).
`game_date` bound from `pfr_game_id` YYYYMMDD (108/108 games one date).

## What was written

Isolated production builder (`nfl_snap_share_exposure_ledger`) is **unchanged**
and still fail-closes on unresolved / conflict / incomplete. Research path:

| Path | Role |
|---|---|
| `services/model-service/src/services/nfl_research_5g_exposure.py` | Materializer (flags states; never invents) |
| `services/model-service/tests/test_nfl_research_5g_exposure.py` | Coverage / consistency / completeness / leakage |
| sealed parquet above | One populated research ledger |
| this file | Engineering receipt |

Window = IF `_5g` via `resolve_if_5g_window` (#666 as-of): `rating_week = target_week - 1`;
every frame game completed and `game_date <` target; target `game_id` cannot enter
its own window; no latest-five / `MAX(week)` substitute.

## Coverage

- Source: 2026 REG W1–8 · 10,073 snap rows · 108 games · 32 teams.
- Eligible team-games week ≥6: **58**. Populated `_5g` windows: **52**.
- Skipped **6** (`RATING_WEEK_UNRESOLVED` — bye in week W−1; not filled):
  CAR W6, KC W6, CIN W7, DET W7, MIA W7, MIN W7.
- Window rows: **3,049**. Residual flag rows: **349**.
- Measured windows: 2,624 (starter_label_derived 1,042). Share range 0.0–1.0.
- Denominators = team-game **max** offense/defense snaps (not pct).

## Flagged residuals (do not invent)

| Bucket | n | State | Who |
|---|---|---|---|
| Unresolved identity | **18** | `unresolved_identity` | AndeAl01 Alec Anderson BUF C (6) · WhitCo05 Cody White LV WR (7) · OkoyCJ00 CJ Okoye NYG DL (5) |
| PFR/roster GSIS conflict | **6** | `conflict` | WoodPe00 Peter Woods KC · players `WOO547869` ≠ roster `00-0041545` |
| ACT-absent unconfirmed | **325** | `unknown` | roster ACT in a played team-week, absent from snaps |

Alex ~367 UNKNOWN = 325 + 24 no-roster + 18 unresolved, where the 24 **are**
18 + 6. Distinct flagged rows = 18 + 6 + 325 = 349 (no double-count).

Distinct tokens preserved: `verified_zero` · `missing` · `unknown` ·
`unresolved_identity` · `conflict` · `measured`. UNKNOWN / unresolved / conflict
/ missing ⇒ `embedded_snap_share` and `starter_label_derived` are **null**.

## Tests

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest -q \
  tests/test_nfl_research_5g_exposure.py \
  tests/test_nfl_if_pregame_asof.py \
  tests/test_nfl_snap_share_exposure_ledger.py
# 67 passed
```

Leakage: 0 window rows contain the target `game_id`; all window dates < target;
all window weeks < target_week; `rating_week == target_week - 1`.

## Suitability / gaps (OWNER report)

**Suitable for further research?** Yes — as a research-only snap-share `_5g`
participation ledger: identity QA, as-of window reconstruction, and descriptive
exposure means on the 52 team-targets where the contiguous IF window resolves.

**Not suitable** for replacement-value or injury-interaction modeling yet.

Still missing for those:

1. ACT-absent rule not ratified (325 UNKNOWN; cannot treat as 0 or as injured).
2. 18 unresolved + 6 conflict IDs unadjudicated (no GSIS for those rows).
3. No official injury report / practice participation / IR dates.
4. No replacement-level or player-point engine (RETURN_UNCREDITED stands).
5. No injury weights; this ledger is participation, not value.
6. Six W−1-bye targets have no contiguous `_5g` window (fail closed).
7. W8 is one game (CAR/GB); season incomplete; completion = snap presence only.
8. ST-only K/P/LS have no O/D side (unknown; not guessed).
9. Commercial/PFR-origin rights HOLD — research attribution only.

baseline_personnel_ref remains snap-share-weighted `_5g` (`d4acc170`).
≥50% binary = derived label only. No production admission on this seal.
