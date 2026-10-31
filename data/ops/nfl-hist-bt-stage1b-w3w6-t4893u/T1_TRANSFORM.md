# T1 transform — port notes (t4893u W3–W6)

Contract b41f4b43 §4: T1 = `nfl_dp_team_situational_weekly` columns produced by the existing approved SQL in `data_platform_nfl/ingest.py` @ `1b39f4e9` (this-tree sha256 **5fc97157…**).

This packet **reuses** the W2 pandas port (`t1_from_plays`, `rolling_5g`, `lookup_t2`, synthetic fixture). It does **not** invent a new feature set.

W1 T1 rows vs W2 packet `t1_team_week_2017_w1.csv`: max abs diff **0**.

## Play filter (T1 SQL)

```
play_type IN ('pass', 'run')
AND posteam IS NOT NULL
AND week IS NOT NULL
```

This packet additionally restricts `season_type='REG'` and `week IN (1,2,3,4,5)` under cf514078 (pre-kickoff / same-season only; rating_week = target_week−1). PRE/POST/W6 were not consumed.

## Pressure — matched

T1 SQL:

```
offensive_pressures_allowed = SUM(play_type='pass' AND (sack OR qb_hit))
offensive_dropbacks         = SUM(play_type='pass')
pressure_rate_allowed       = pressures / dropbacks
```

- This **is** `(sack OR qb_hit) / play_type='pass'`.
- `qb_dropback` exists on the parquet and was **not** used as the denominator.
- Hurries are not in the T1 SQL and were not invented.

## Red-zone TD rate — matched to T1 SQL; trips paraphrase refused

```
red_zone_plays      = SUM(yardline_100 <= 20)
red_zone_touchdowns = SUM(yardline_100 <= 20 AND touchdown)
red_zone_td_rate    = touchdowns / plays
```

Using drive-trips would be a substitute feature. **Refused.** Play-based SQL used.

## T2 / T3 as-of

- T2 window SQL: `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` partitioned by team, ordered by week (W2 `rolling_5g`).
- T3 consumption: join T2 at `rating_week = target_week - 1` via W2 `lookup_t2` (exact week). Never at the target week.
- W5 byes (ATL, DEN, NO, WSH) have no T2 row at week=5. W6 sides stay MISSING_RECORD. Last-played-week lookup was **not** added.

## T3 / T4 signs (SQL, same as W2)

| field | formula used |
|---|---|
| `matchup_diff_off_epa_5g` | home off − away off |
| `matchup_diff_def_epa_allowed_5g` | **away** def allowed − **home** def allowed |
| `matchup_diff_pressure_generated_5g` | home − away |
| `matchup_diff_pressure_allowed_5g` | **away** allowed − **home** allowed |
| `matchup_diff_red_zone_td_rate_5g` | home − away |
| `matchup_diff_success_rate_5g` | mean of (h_off_succ − a_off_succ, a_def_succ − h_def_succ); both terms required |

## Verification gate

| Gate | Result |
|---|---|
| Reuse W2 functions | `t1_from_plays` / `rolling_5g` / `lookup_t2` / `synthetic_t1_selfcheck` |
| W1 T1 vs W2 packet | max abs **0** |
| Synthetic fixture (abs_tol 1e-12) | PASS |
| Rebuild T1 vs 2023+/2025 backbone | **NOT POSSIBLE** on this box |
| Fail-closed fallback | MISSING when exact rating_week T2 absent (4 W6 games) |

## EPA retro-fit

nflverse `epa` / `success` are retro-scored by a later EP model. Metric-definition look-ahead; not target-week outcome leakage. Labeled on matrix rows. Soft carry from Alex W2 RO.

## Identity remaps (join only)

PBP 2017 uses `LA` / `WAS` / `LV`. Sealed `games.csv` uses `LAR` / `WSH` / `OAK`. Mapped for the join. Not a prior-season fill.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
