# T1 transform — port notes (t4893u)

Contract b41f4b43 §4: T1 = `nfl_dp_team_situational_weekly` columns produced by the existing approved SQL in `data_platform_nfl/ingest.py` @ `1b39f4e9` (this-tree sha256 **5fc97157…**).

This packet ports that SQL to pandas over the owned 2017 parquet. It does **not** invent a new feature set.

## Play filter (T1 SQL)

```
play_type IN ('pass', 'run')
AND posteam IS NOT NULL
AND week IS NOT NULL
```

Observed 2017 `play_type` values excluded by that filter: `no_play`, `kickoff`, `punt`, `extra_point`, `field_goal`, `qb_kneel`, `qb_spike`, null.

This packet additionally restricts `season_type='REG'` and `week=1` under cf514078 (pre-kickoff / same-season only). PRE/POST were not consumed.

## Pressure — matched

T1 SQL:

```
offensive_pressures_allowed = SUM(play_type='pass' AND (sack OR qb_hit))
offensive_dropbacks         = SUM(play_type='pass')
pressure_rate_allowed       = pressures / dropbacks

defensive_pressures_generated / defensive_dropbacks_faced  (same, defteam)
```

- This **is** `(sack OR qb_hit) / play_type='pass'`.
- `qb_dropback` exists on the parquet and was **not** used as the denominator (would be a substitute).
- Hurries are not in the T1 SQL and were not invented.
- **Decision:** DERIVED_PREGAME. No escalation for mismatch.

## Red-zone TD rate — matched to T1 SQL; trips paraphrase refused

T1 SQL:

```
red_zone_plays      = SUM(yardline_100 <= 20)
red_zone_touchdowns = SUM(yardline_100 <= 20 AND touchdown)
red_zone_td_rate    = touchdowns / plays
```

`T1T4_PLAIN_ENGLISH_DEFS.md` says “share of RZ trips (inside opp 20) ending in TD.” That is a drive-trip definition. Using trips would be a substitute feature / contract change. **Refused.** Play-based SQL used.

**Note for Alex (not a STOP):** plain-English “trips” ≠ T1 SQL plays. Reconstruct-as-written chose the cited SQL. If RO requires trips, that is a contract amendment, not a silent fill.

## T2 / T3 as-of

- T2 window SQL: `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` partitioned by team, ordered by week.
- W1-only frame ⇒ `games_in_window_5 = 1` for every T2 row. Contract T2 = last **≤5** played games.
- T3 consumption: join T2 at `rating_week = 1`, never at week 2 (contract §4 leakage key / cf514078).

## T3 / T4 signs (SQL, not the home-minus-away paraphrase where they differ)

| field | formula used |
|---|---|
| `matchup_diff_off_epa_5g` | home off − away off |
| `matchup_diff_def_epa_allowed_5g` | **away** def allowed − **home** def allowed |
| `matchup_diff_pressure_generated_5g` | home − away |
| `matchup_diff_pressure_allowed_5g` | **away** allowed − **home** allowed |
| `matchup_diff_red_zone_td_rate_5g` | home − away |
| `matchup_diff_success_rate_5g` | mean of (h_off_succ − a_off_succ, a_def_succ − h_def_succ); both terms required |

Plain-English “home − away” for def-allowed and pressure-allowed is a paraphrase. SQL signs used.

## Verification gate

| Gate | Result |
|---|---|
| SQL-to-pandas code review | Ported CTE for CTE |
| Synthetic fixture (abs_tol 1e-12) | PASS (`T1_TRANSFORM.json`) |
| Rebuild T1 vs 2023+/2025 backbone | **NOT POSSIBLE** on this box (2023 PBP not owned; 2025 PBP not owned; 2024–25 not opened) |
| Fail-closed fallback | Would have been MISSING if SQL could not be matched. Not triggered |

## EPA retro-fit

nflverse `epa` / `success` are retro-scored by a later EP model. Metric-definition look-ahead; not W2+ outcome leakage. Labeled on matrix rows.

## Identity remaps (join only)

PBP 2017 uses `LA` / `WAS` / `LV`. Sealed `games.csv` uses `LAR` / `WSH` / `OAK`. Mapped for the join. Not a prior-season fill.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
