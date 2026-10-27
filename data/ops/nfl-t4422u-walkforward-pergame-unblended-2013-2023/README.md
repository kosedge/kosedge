# t4422u — walk-forward per-game unblended engine export (2013–2023)

Research prep for Alex baseline. **Not a CLEAR. Not graded results.**  
NFL board **NO-GO**. Coming soon **ON**. No merge / deploy / spend.

Authority cited (filings not in this worktree):  
`DECISION_RYAN_t4422u` sha8 `dbb35c04` ·  
`ALEX_PREDICTIVE_BASELINE_STATUS_t4422u_v1.md` sha8 `7f16f829` ·  
IMV gates packet t4422u sha8 `7af96335` (adopt before graded results).

## Reproduce

```bash
python3 data/ops/nfl-team-simulator-calibration-audit/export_walkforward_pergame_2013_2023.py
```

| Pin | Value |
| --- | --- |
| Command | `python3 data/ops/nfl-team-simulator-calibration-audit/export_walkforward_pergame_2013_2023.py` |
| Git tip at generation | `a0f583d31b956ba0e7db9fd858e59014c0335600` (`a0f583d31b95`) |
| Python | `3.12.3` |
| Engine | `src.services.nfl_simulator.simulate_nfl_game` |
| `model_version` | `nfl-v1.5-matchup-sim` |
| `framework_version` | `nfl-handicap-core-v3.1` |
| HFA (engine prior, not invented) | `1.05` |
| Base total (engine prior) | `45.3` |
| Simulations / game | `4000` |
| Seed | sha256(`game_id\|t4422u-unblended-record`)[:4] → int31 |
| IFB overlays | **OFF** (no IFB module on this tip; no inputs passed) |
| Injury overlays | **OFF** |
| Personnel overlays | **OFF** |
| Market blend | **OFF** (`market_spread_home` / `market_total` omitted) |
| Market columns | **not in this file** (nflverse close is Alex-side MS-9) |
| Holdout 2024+ | **not opened** |
| Rest days | `7.0` / `7.0` (same hardcoded rest as `historical_market_backtest.py` / record-vs-EPA audit; do not invent rest from incomplete clocks) |

## PIT inputs

1. Schedule / scores spine: `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv`  
   sha256 `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed`  
   Already-filed 2013–2026 completed games from the 2026-09-16 historical OOS packet (Railway `nfl_dp_schedules` read at that time). This export **filters to 2013–2023 inclusive**.
2. nflverse `games.csv` (free; no Odds spend) for `game_id` + gameday/gametime:  
   `https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv`  
   sha256 `97f1c36ce77e9c3952b1ffe8cad3096171c28280cc5d0b48a89f7cceb5cb03a9`  
   Join key = `(season, week, normalize_join_abbr(home), normalize_join_abbr(away))` using the existing product alias `LA→LAR`, `WAS→WSH` (`nfl_epa_authority.normalize_nfl_abbr`). Exported `home`/`away` stay as the OOS labels (WSH/LAR).
3. RECORD strength: walk-forward same-season W-L, updated **after** the game, ties ignored (same rule as `backtest_record_vs_epa_signal.py`). Indices = `team_strength_from_record` (`0.90+0.22*win_pct` / `0.92+0.20*win_pct`, clamped).

## Probability columns

| Column | Status | Notes |
| --- | --- | --- |
| `home_win_prob` / `away_win_prob` | **PRESENT** | RECORD unblended Monte Carlo (`simulate_nfl_game`) |
| `cover_prob` | **MISSING** | Engine does not emit cover; would need a market spread |
| `over_prob` | **MISSING** | Engine does not emit over; would need a market total |
| `epa_home_win_prob` / `epa_away_win_prob` | **MISSING** | See `MISSING.json` — rolling-feature table not mounted |
| `epa_trailing_spread_home` / `epa_trailing_total` | repo decompose only, 2023 | Copied from historical OOS; **not** engine win probs |

Point estimates: use `record_decomp_*` for the stable unblended RECORD mean (matches filed OOS `record_spread` / `record_total` on 0–0 week-1: −1.05 / 44.8435). `record_pred_margin_home` / `record_spread_home` / `record_total` are Monte Carlo means (simulation grain).

Sign: `*_spread_home` negative = home favored. `*_pred_margin_home` positive = home favored (home − away).

## Row counts by season

| Season | n |
| --- | ---: |
| 2013 | 267 |
| 2014 | 267 |
| 2015 | 267 |
| 2016 | 267 |
| 2017 | 267 |
| 2018 | 267 |
| 2019 | 267 |
| 2020 | 269 |
| 2021 | 285 |
| 2022 | 284 |
| 2023 | 285 |
| **Total** | **2992** |

nflverse join hits: 2992 / 2992.  
`kickoff_utc` present: 2992.

## Sealed files

| File | Role |
| --- | --- |
| `games.csv` | one row per game 2013–2023 |
| `games.csv.sha256` | `07c89418ab55a6c4c781ece669ad062cbe2ebeb5de26c65d0ab57dca06db34eb` |
| `manifest.json` | machine pins |
| `MISSING.json` | blockers (do not fabricate) |
| `nflverse_games_2013_2023_join.csv` | join input copy |

## True-close / CLV

**Out of scope.** Owned odds lake / true-close JSONL not mounted (`DATABASE_URL` unset). Market columns omitted on purpose.

## Non-actions honored

- No holdout open (2024+ rows not exported)
- No frozen-test edits
- No HFA / site invention (engine priors + nflverse ET clock convention only)
- No production publish path edits
- No candidate fitting / remat / overlay unlock
