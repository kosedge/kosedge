# 2022 Odds-API / warehouse closing-line recovery

**Generated:** `2026-09-11T23:38:47Z`  
**Contract:** `cfb-qb-feature-v1` (untouched)  
**MATCHUP_RESPONSE:** `1.4` frozen; not scored  
**Scope:** market-data recovery + join audit only. CFB stays dark. No PLAY.

## Decision

**STOP** — Train-0 lake close+actual n=`0` (lake-or-SDV-fill n=`1`) vs gate `700`.

Lake mounted this run: `False`. Chosen source: `None`.

Frozen 1.40 was **not** scored. Recalibration is **not** authorized.
2025 remains sealed. 2026 remains outside the loss.

## Funnel (2022)

raw events → valid pregame closes → identity-matched → FBS/FBS → actual available → close+actual eval

| Step | n |
| --- | ---: |
| raw lake events (date, home, away) | 0 |
| raw lake snaps | 0 |
| valid pregame lake closes | 0 |
| identity-matched | 0 |
| FBS/FBS | 0 |
| actual available | 0 |
| close+actual eval (all weeks, Layer A both) | 0 |
| **Train-0 W1–14 close+actual (lake)** | **0** |
| Train-0 W1–14 close+actual (lake or SDV fill) | 1 |

SDV fill (not the Odds-API lake) — shown so the hole is exact, not vibes:

{
  "sdv_rows_with_spread": 125,
  "sdv_fbs_fbs": 6,
  "sdv_fbs_fbs_w1_14_actual": 6,
  "sdv_fbs_fbs_w1_14_actual_layer_a": 1,
  "sdv_fcs_any": 119
}

Deficit vs gate: lake `700` (need 700, have 0).

Spread / total independently:

| | n |
| --- | ---: |
| joined spread available | 125 |
| joined total available | 125 |
| Train-0 lake spread | 0 |
| Train-0 lake total | 0 |
| Train-0 fill spread | 1 |
| Train-0 fill total | 1 |

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

- `hd_parquet` present=`False` /Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet
- `repo_parquet` present=`False` /workspace/services/model-service/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet
- `monorepo_parquet` present=`False` /workspace/data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet
- `postgres_export` present=`False` odds_snapshots WHERE leagues.code='cfb' (export_odds_lake SQL)
- `odds_api_live_historical` present=`False` do not burn The Odds API historical credits in this assignment

## Duplicates / conflicts

{
  "duplicate_game_ids": 0,
  "conflict_multi_game": 0,
  "conflict_date_skew": 0,
  "orientation_flip_candidates": 0,
  "sdv_lake_spread_disagree": 0
}

## Unmatched reason codes (games without a valid pregame lake close)

{
  "FCS_AWAY": 115,
  "NO_LAKE_MATCH": 900,
  "SDV_FILL_ONLY": 125,
  "LAYER_A_MISSING_AWAY": 5,
  "WEEK_OUT_OF_TRAIN0": 1,
  "FCS_BOTH": 4
}

Unmatched lake events (lake side, no warehouse game): `0`

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
  "lake_date_min": null,
  "lake_date_max": null,
  "n_distinct_lake_dates": 0,
  "books": {},
  "sources": {},
  "captured_at_min": null,
  "captured_at_max": null,
  "joined_close_sources": {
    "sportsdataverse_espn_cfb_betting": 125,
    "none": 775
  }
}

## Representative joined rows

| game_id | week | home_team_id | away_team_id | close_spread_home | close_total | close_source | train0_lake |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 401415240 | 7 | HAW | NEV | 5.5 | 51.5 | sportsdataverse_espn_cfb_betting | False |
| 401426532 | 1 | WKU | espn:2046 | -30.5 | 70.5 | sportsdataverse_espn_cfb_betting | False |
| 401405059 | 1 | NW | NEB | None | None | None | False |
| 401404146 | 1 | UTAHST | CONN | None | None | None | False |
| 401405058 | 1 | ILL | WYO | None | None | None | False |
| 401426530 | 1 | FAU | CHAR | None | None | None | False |
| 401409235 | 1 | NMSU | NEV | None | None | None | False |
| 401426531 | 1 | UTEP | UNT | None | None | None | False |
| 401403853 | 1 | HAW | VAN | None | None | None | False |
| 401416569 | 1 | OKST | CMU | None | None | None | False |

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

## Where the 2026-08-13 export was created

See `data/ops/cfb-2022-odds-lake-provenance-20260911.md`.

The parquet is **not** in git (PR #215: bulk warehouse not committed). It was written on the **developer Mac**:

1. `scripts/odds/enterprise_training_pull.py` → local `postgresql://ryankos:postgres@127.0.0.1:5432/kosedge` (CFB mainlines completed 2026-07-28).
2. `export_odds_lake()` via `scripts/cfb/ingest_historical_warehouse.py` → `/Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet` on **2026-08-13**.
3. Ops already says the Mac owns `/Volumes/KosEdgeData/raw/odds/**`.

No sha256 exists in the committed inventory — counts only (28,322 / 838 / 717). Railway production Postgres is a different DSN and was not the export source. This VM still cannot mount the HD or open that local Postgres.

Recovery action: copy `snapshots-2022.parquet` from the Mac HD (or re-export from that same local DB). Do not live-densify The Odds API.

## GO / STOP

**STOP**

Do not score frozen 1.40 in this assignment. Do not recalibrate.
CFB remains dark.

