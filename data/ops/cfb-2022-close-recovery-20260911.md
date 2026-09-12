# 2022 Odds-API / warehouse closing-line recovery

**Generated:** `2026-09-12T01:49:52Z`  
**Contract:** `cfb-qb-feature-v1` (untouched)  
**MATCHUP_RESPONSE:** `1.4` frozen; not scored  
**Scope:** market-data recovery + join audit only. CFB stays dark. No PLAY.

## Decision

**GO TO FROZEN 1.40 SCORING** — Train-0 lake close+actual n=`712` (lake-or-SDV-fill n=`713`) vs gate `700`.

Lake mounted this run: `True`. Chosen source: `hd_parquet`.

Frozen 1.40 was **not** scored. Recalibration is **not** authorized.
2025 remains sealed. 2026 remains outside the loss.

## Funnel (2022)

raw events → valid pregame closes → identity-matched → FBS/FBS → actual available → close+actual eval

| Step | n |
| --- | ---: |
| raw lake events (date, home, away) | 773 |
| raw lake snaps | 28322 |
| valid pregame lake closes | 717 |
| identity-matched | 713 |
| FBS/FBS | 713 |
| actual available | 713 |
| close+actual eval (all weeks, Layer A both) | 713 |
| **Train-0 W1–14 close+actual (lake)** | **712** |
| Train-0 W1–14 close+actual (lake or SDV fill) | 713 |

SDV fill (not the Odds-API lake) — shown so the hole is exact, not vibes:

{
  "sdv_rows_with_spread": 125,
  "sdv_fbs_fbs": 6,
  "sdv_fbs_fbs_w1_14_actual": 6,
  "sdv_fbs_fbs_w1_14_actual_layer_a": 713,
  "sdv_fcs_any": 119
}

Deficit vs gate: lake `-12` (need 700, have 712).

Spread / total independently:

| | n |
| --- | ---: |
| joined spread available | 838 |
| joined total available | 838 |
| Train-0 lake spread | 712 |
| Train-0 lake total | 712 |
| Train-0 fill spread | 713 |
| Train-0 fill total | 713 |

## Provenance

Authoritative artifact (when mounted): `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet`
exported 2026-08-13 from `odds_snapshots` (`the-odds-api-historical-enterprise`).
Documented counts: 28,322 snaps / 838 close spreads / 717 lake-primary / 900 warehouse games.

Close selection: last snap with `captured_at` **strictly before kickoff**; DraftKings then FanDuel.
Open = first legal snap. Intermediate = legal snaps between open and close.
Same timestamp as kickoff is illegal. Post-kick snaps are dropped.
Identity: `cfb_warehouse.identity.resolve_team_code`. Join key `(game_date, home_name, away_name)`.
Conflicts (multi-game, dual ±1-day, flipped orientation) are reason-coded and excluded — no silent pick.
Raw source values are stored beside normalized engine codes / closes.

Sources tried:

- `hd_parquet` present=`True` /Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet
- `repo_parquet` present=`False` /Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet
- `monorepo_parquet` present=`False` /Users/ryankos/kosedge/.worktrees/cfb-2022-closes-mac/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet
- `postgres_export` present=`False` odds_snapshots WHERE leagues.code='cfb' (export_odds_lake SQL)
- `odds_api_live_historical` present=`False` do not burn The Odds API historical credits in this assignment

## Duplicates / conflicts

{
  "duplicate_game_ids": 0,
  "conflict_multi_game": 0,
  "conflict_date_skew": 0,
  "orientation_flip_candidates": 1,
  "sdv_lake_spread_disagree": 2
}

## Unmatched reason codes (games without a valid pregame lake close)

{
  "FCS_AWAY": 111,
  "POST_KICK_ONLY": 2,
  "SDV_FILL_ONLY": 121,
  "NO_LAKE_MATCH": 180,
  "LAYER_A_MISSING_AWAY": 5,
  "ORIENTATION_FLIP_CANDIDATE": 1,
  "FCS_BOTH": 4
}

Unmatched lake events (lake side, no warehouse game): `54`

## FBS / FCS exclusions

{
  "fcs_home": 0,
  "fcs_away": 115,
  "fcs_both": 4,
  "fcs_any": 119
}

## Leakage / contract tests

- rule: `strictly_before_kickoff`
- failures: `0`
- ok: `True`
- MATCHUP_RESPONSE still `1.4`
- qb contract still `cfb-qb-feature-v1`
- opened_2025: `False`

## Source / date coverage

{
  "lake_date_min": "2022-08-27",
  "lake_date_max": "2023-01-10",
  "n_distinct_lake_dates": 81,
  "books": {
    "draftkings": 14613,
    "fanduel": 13709
  },
  "sources": {
    "the-odds-api-historical-enterprise": 28322
  },
  "captured_at_min": "2022-08-26T17:45:09+00:00",
  "captured_at_max": "2023-01-09T16:53:02+00:00",
  "joined_close_sources": {
    "sportsdataverse_espn_cfb_betting": 121,
    "odds_api_lake": 717,
    "none": 62
  }
}

## Representative joined rows

| game_id | week | home_team_id | away_team_id | close_spread_home | close_total | close_source | train0_lake |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 401405059 | 1 | NW | NEB | 11.0 | 51.5 | odds_api_lake | True |
| 401415240 | 7 | HAW | NEV | 5.5 | 51.5 | sportsdataverse_espn_cfb_betting | False |
| 401426532 | 1 | WKU | espn:2046 | -30.5 | 70.5 | sportsdataverse_espn_cfb_betting | False |
| 401404146 | 1 | UTAHST | CONN | None | None | None | False |
| 401403890 | 3 | TAMU | MIA | -8.5 | 53.5 | odds_api_lake | True |
| 401404090 | 6 | OU | TEX | None | None | None | False |
| 401405058 | 1 | ILL | WYO | -14.0 | 43.0 | odds_api_lake | True |
| 401426530 | 1 | FAU | CHAR | -7.0 | 59.0 | odds_api_lake | True |
| 401409235 | 1 | NMSU | NEV | 7.5 | 48.0 | odds_api_lake | True |
| 401426531 | 1 | UTEP | UNT | 1.5 | 54.5 | odds_api_lake | True |

## Methodology if n<700

{
  "recommendation": "RETAIN_CLOSE_ACTUAL_GATE",
  "do_not_switch_to_actuals_only": true,
  "why": [
    "The owned Odds-API lake is documented at 28,322 2022 snaps / 838 closes / 717 lake-primary.",
    "The miss on this VM is mount/export, not a proof that 2022 closes never existed.",
    "Actuals-only 2022 FBS\u2013FBS W1\u201314 is already 780 \u2014 labels exist; the hole is the market tape.",
    "Switching the protocol to actuals-only would train 1.40 without the feature it is judged against."
  ],
  "formal_actuals_only_would_require": "an explicit protocol amendment; this recovery does not make that change"
}

## GO / STOP

**GO TO FROZEN 1.40 SCORING**

Do not score frozen 1.40 in this assignment. Do not recalibrate.
CFB remains dark.

