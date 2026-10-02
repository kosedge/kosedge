# CFB QB Layer A reconstruction (2022–2024)

**Date:** 2026-09-11  
**Contract:** `cfb-qb-feature-v1`  
**Kill switch:** ON. No PLAY. No public CFB. No λ. No Line Curve.  
**Coefficients:** frozen (`MATCHUP_RESPONSE=1.40`).  
**2025:** sealed. **2026 W1/W2:** not inspected.

## Evidence gate: **STOP** (Layer A reconstruction: **GO**)

Blocker: Train-0 close+actual n<700 (2022 SDV betting sparse; Layer A features are not the miss)

| Check | OK | Detail |
|---|---|---|
| contract_version_v1 | PASS | `"cfb-qb-feature-v1"` |
| leakage_audit | PASS | `{"n_failures": 0}` |
| coverage_2022 | PASS | `{"coverage": 1.0, "d": 131, "n": 131}` |
| established_location_2022 | PASS | `{"mean": 71.0676, "n": 129, "sd": 6.683}` |
| not_placeholder_2022 | PASS | `{"max": 84.67, "mean": 70.8456, "min": 54.62, "n": 131, "p10": 60.75, "p25": 65.16, "p50": 71.97, "p75": 75.13, "p90": 8` |
| coverage_2023 | PASS | `{"coverage": 1.0, "d": 133, "n": 133}` |
| established_location_2023 | PASS | `{"mean": 70.7259, "n": 123, "sd": 6.6996}` |
| not_placeholder_2023 | PASS | `{"max": 85.58, "mean": 69.4098, "min": 47.5, "n": 133, "p10": 58.274, "p25": 64.08, "p50": 70.5, "p75": 75.39, "p90": 79` |
| coverage_2024 | PASS | `{"coverage": 1.0, "d": 134, "n": 134}` |
| established_location_2024 | PASS | `{"mean": 70.4147, "n": 123, "sd": 6.9693}` |
| not_placeholder_2024 | PASS | `{"max": 83.22, "mean": 68.9635, "min": 48.0, "n": 134, "p10": 57.62, "p25": 63.905, "p50": 69.07, "p75": 75.2775, "p90":` |
| train_0_n | FAIL | `{"n": 9, "n_close_and_actual": 9, "seasons": [2022], "weeks": "1-14"}` |
| val_0_n | PASS | `{"n": 769, "n_close_and_actual": 769, "seasons": [2023], "weeks": "1-14"}` |
| val_1_n | PASS | `{"n": 792, "n_close_and_actual": 792, "seasons": [2024], "weeks": "1-14"}` |
| 2025_sealed | PASS | `"not opened"` |
| 2026_not_in_objective | PASS | `"confirmatory only; not read"` |
| coefficients_unchanged | PASS | `"MATCHUP_RESPONSE=1.40 frozen"` |

## Coverage

| Season | Mapped FBS | Layer A | Coverage | Portal n | Low-sample n | Misses |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 131 | 131 | 100.0% | 30 | 2 | 0 |
| 2023 | 133 | 133 | 100.0% | 40 | 10 | 0 |
| 2024 | 134 | 134 | 100.0% | 54 | 11 | 0 |

### Failures preventing 90% (if any)

None — every mapped FBS team produced a Layer A QB1.

## Talent distributions (not just the mean)

### All Layer A QB1s

| Season | n | mean | sd | p10 | p25 | p50 | p75 | p90 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 131 | 70.8456 | 6.8713 | 60.75 | 65.16 | 71.97 | 75.13 | 80.35 |
| 2023 | 133 | 69.4098 | 7.9762 | 58.274 | 64.08 | 70.5 | 75.39 | 79.222 |
| 2024 | 134 | 68.9635 | 8.3012 | 57.62 | 63.905 | 69.07 | 75.2775 | 79.29 |

### Established (prior attempts ≥ 80)

| Season | n | mean | sd | p10 | p25 | p50 | p75 | p90 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 129 | 71.0676 | 6.683 | 61.762 | 65.37 | 72.05 | 75.17 | 80.362 |
| 2023 | 123 | 70.7259 | 6.6996 | 61.58 | 65.71 | 71.08 | 75.83 | 79.408 |
| 2024 | 123 | 70.4147 | 6.9693 | 61.186 | 65.2 | 69.93 | 75.485 | 79.762 |

## Class / portal

| Season | class counts | portal % | low-sample % |
|---|---|---:|---:|
| 2022 | `{'incumbent': 100, 'portal': 30, 'true_freshman': 1}` | 22.9% | 1.5% |
| 2023 | `{'incumbent': 90, 'portal': 40, 'open_competition': 2, 'true_freshman': 1}` | 30.1% | 7.5% |
| 2024 | `{'incumbent': 74, 'portal': 52, 'open_competition': 6, 'true_freshman': 2}` | 40.3% | 8.2% |

## Game counts (forward-chain structure, labels only)

| Split | Seasons | Weeks | n | Gate |
|---|---|---|---:|---|
| train_0 | [2022] | 1-14 | 9 | FAIL (≥700) |
| val_0 | [2023] | 1-14 | 769 | PASS (≥1) |
| train_1 | [2022, 2023] | 1-14 | 778 | PASS (≥1) |
| val_1 | [2024] | 1-14 | 792 | PASS (≥700) |

SDV skip reasons: `{'missing_line': 808, 'missing_score': 1, 'unmapped_team': 391, 'fcs_or_unknown': 0}`

## Missingness (reason codes)

```json
{
  "overall": {
    "RECRUITING_UNAVAILABLE_LAYER_B": 398,
    "CAST_UNAVAILABLE_LAYER_B": 398,
    "OVERRIDE_UNAVAILABLE": 398,
    "W1_CONFIRM_UNAVAILABLE": 398,
    "ESPN_EXPERIENCE_IGNORED": 398,
    "PORTAL_ROSTER_JOIN": 398,
    "EXPERIENCE_RECONSTRUCTED": 398,
    "LAYER_A_OK": 398,
    "CLASS_LEFT_CENSORED": 22,
    "STATS_404": 1
  },
  "by_season": {
    "2022": {
      "RECRUITING_UNAVAILABLE_LAYER_B": 131,
      "CAST_UNAVAILABLE_LAYER_B": 131,
      "OVERRIDE_UNAVAILABLE": 131,
      "W1_CONFIRM_UNAVAILABLE": 131,
      "ESPN_EXPERIENCE_IGNORED": 131,
      "PORTAL_ROSTER_JOIN": 131,
      "EXPERIENCE_RECONSTRUCTED": 131,
      "LAYER_A_OK": 131,
      "CLASS_LEFT_CENSORED": 21
    },
    "2023": {
      "RECRUITING_UNAVAILABLE_LAYER_B": 133,
      "CAST_UNAVAILABLE_LAYER_B": 133,
      "OVERRIDE_UNAVAILABLE": 133,
      "W1_CONFIRM_UNAVAILABLE": 133,
      "ESPN_EXPERIENCE_IGNORED": 133,
      "PORTAL_ROSTER_JOIN": 133,
      "EXPERIENCE_RECONSTRUCTED": 133,
      "LAYER_A_OK": 133,
      "CLASS_LEFT_CENSORED": 1
    },
    "2024": {
      "RECRUITING_UNAVAILABLE_LAYER_B": 134,
      "CAST_UNAVAILABLE_LAYER_B": 134,
      "OVERRIDE_UNAVAILABLE": 134,
      "W1_CONFIRM_UNAVAILABLE": 134,
      "ESPN_EXPERIENCE_IGNORED": 134,
      "PORTAL_ROSTER_JOIN": 134,
      "EXPERIENCE_RECONSTRUCTED": 134,
      "LAYER_A_OK": 134,
      "STATS_404": 1
    }
  }
}
```

## Leakage audit

- rows: 398
- ok: True
- no leakage failures

## Representative provenance

- **2022 ALA** Bryce Young (4685720): class=incumbent talent=83.29 att/yds/td=462/4322/43 portal=False first=2020
- **2023 OSU** Kyle McCord (4433971): class=incumbent talent=53.71 att/yds/td=20/190/1 portal=False first=2021
- **2023 SYR** Garrett Shrader (4426966): class=incumbent talent=69.59 att/yds/td=266/2310/17 portal=False first=2019
- **2024 ORE** Dillon Gabriel (4427238): class=portal talent=81.94 att/yds/td=384/3660/30 portal=True first=2019
- **2022 ARMY** Christian Anderson (4258447): class=incumbent talent=58.43 att/yds/td=59/653/5 portal=False first=2019
- **2024 JVST** Tyler Huff (4574356): class=portal talent=67.94 att/yds/td=299/1863/10 portal=True first=2019

## Unresolved limitations

- Layer B recruiting / OL / weapons / expert overrides / W1 confirms are MISSING.
- ESPN group-80 mapped codes are the year-Y FBS denominator (not the 2026 136-team lock).
- Class years are first-appearance reconstructions; left-censored at 2017 stats floor.
- Identity/option slice not built (would need prior-year team rush/pass; not proxied from 2026).
- P4/G5 year-Y affiliations not stored on Layer A rows (2026 conference map would leak realignment).
- Frozen 1.40 game scoring deferred — Layer B cast is missing; filling 50 would re-introduce hist-cal semantics.
- Warehouse parquet / CFBD / Odds-API lake were not used. ESPN core + SDV betting/box/linescores only.
- 2022 SDV espn_cfb_betting has closes on ~125/904 rows (mostly early/FCS). Train-0 close+actual n fails the 700 gate until the warehouse lake is mounted.

## GO / STOP

**STOP** against the full #540 minimum-evidence gate (close+actual train n, 2024 val n, coverage, location).

**Layer A reconstruction: GO** — year-locked QB1 / prior-year stats / portal join / first-appearance class are built for 2022–2024 at 100% mapped-FBS coverage.

Do not weaken the QB contract to pass Train-0. The miss is 2022 *closes* (SDV betting sparse; warehouse Odds-API lake not mounted).

Coefficients were not moved. Recalibration is not authorized by this report.

CFB remains dark.
