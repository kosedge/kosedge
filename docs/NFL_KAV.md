# KAV — Kos Edge Adjusted Value

KAV is Kos Edge’s **owned** opponent-adjusted team efficiency metric. It is
inspired by the _idea_ of Football Outsiders / FTN DVOA (situation + opponent),
but it is **not** official DVOA, does not use FO/FTN numbers, and must never be
confused with them in product copy or training labels.

## Why it exists

Raw EPA/play is polluted by strength of schedule. A team that faced three elite
defenses will look worse than its true talent; a team that feasted on soft
schedules will look better. KAV iteratively removes that bias from owned
nflverse play-by-play so the simulator and supervised overlay can use a
first-class efficiency signal that we fully control.

## Definition

1. **Play filter** — `nfl_dp_play_by_play` rows with `play_type IN ('pass','run')`
   and non-null EPA.
2. **Game aggregation** — per `(season, week, game_id, team)`:
   - offense: EPA/play, success rate, explosive rate (12+ yards)
   - defense: EPA allowed/play, success allowed, explosive allowed
3. **Iterative opponent adjustment** (as-of end of week `W`):
   - Restrict to games with `week <= W`
   - Initialize team ratings from play-weighted raw EPA
   - Repeat (~12× or until convergence):
     - `adj_off = raw_off + (league_def − opp.def)`
     - `adj_def = raw_def + (league_off − opp.off)`
   - Soft schedules (high opp.def EPA allowed) deflate offense; tough schedules
     inflate it. Same logic on defense with opposite polarity.
4. **KAV percentage** — `(adj_epa − league_mean) / 0.15`
   - `0.15` EPA/play ≈ 100% KAV (tunable constant `KAV_PCT_SCALE`)
   - Offense: higher is better
   - Defense: lower (more negative) is better (suppresses EPA)
   - **Net KAV** = offense KAV − defense KAV

## Tables

Migration: `infra/db/041_nfl_kav_efficiency.sql`

| Table                    | Grain     | Meaning                             |
| ------------------------ | --------- | ----------------------------------- |
| `nfl_dp_team_kav_game`   | team-game | Raw + adjusted game efficiency      |
| `nfl_dp_team_kav_weekly` | team-week | As-of ratings through end of `week` |
| `nfl_dp_team_kav_latest` | view      | Latest weekly row per team          |

Matchup pack columns (nullable until materializer runs):
`home/away_kav_*_5g`, `home/away_kav_*_ytd`, `diff_kav_*`, `kav_as_of_week`.

## Leakage rule (non-negotiable)

For a game in week `W`, features join KAV from week `W − 1` only.

- Week 1 → KAV features are null (no prior)
- Materializer sets `kav_as_of_week = week - 1`
- Unit tests assert `as_of_week < game_week`

Never train or simulate with same-week KAV.

## How it enters the model

| Layer            | Path                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| Materialize      | `data_platform_nfl.kav.materialize_kav` / CLI `--materialize-kav`         |
| Matchup pack     | `nfl_matchup_features.matchup_pack_to_sim_input_kwargs`                   |
| Simulator inputs | `NflGameInputs.home_kav_*` / `away_kav_*`                                 |
| Handicapping     | factor `kav_efficiency` in `nfl_handicapping_framework` (v3)              |
| Supervised       | `FEATURE_KEYS` includes `home/away_kav_*` + `diff_kav_net_5g` (schema v3) |

`external_dvoa` is a separate optional handicapping placeholder for a future
public second opinion. It is **disabled by default**, contributes zero unless
explicitly enabled, and must **not** be used as a training label or feature.

## CLI

```bash
export DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge

# After PBP normalize + usage/matchup features:
cd services/data-platform-nfl
PYTHONPATH=./src /Users/ryankos/kosedge/.venv/bin/python -m data_platform_nfl.cli \
  --seasons 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025 \
  --materialize-kav --replace-kav
```

Sync the vendored copy into model-service when shipping:

```bash
./scripts/nfl/sync-model-service-vendor.sh
```

## Tests

```bash
cd services/data-platform-nfl
PYTHONPATH=./src /Users/ryankos/kosedge/.venv/bin/python -m pytest tests/test_kav.py -q
```

## Product language

- Say **“KAV (Kos Edge Adjusted Value)”** or **“owned opponent-adjusted efficiency”**
- Do **not** say “our DVOA” or imply Football Outsiders affiliation
