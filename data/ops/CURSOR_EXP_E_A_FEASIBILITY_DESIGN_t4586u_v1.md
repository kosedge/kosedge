# CURSOR EXP E → A FEASIBILITY DESIGN — t4586u v1

**PAPER / READ-ONLY FEASIBILITY · CERT=0 · NFL NO-GO · F2 PHI@WSH FROZEN · sealed=1**

Filed 2026-10-28. Cursor (cloud eng) seat. No experiment run. No merge. No deploy. No Odds. No locked-model change.

| bind | sha8 | role |
|---|---|---|
| DECISION_RYAN_t4586u NFL RCA experiment pre-registration | **29eb0f92** | Approve **preparation + pre-registration** of E → A only |
| COS_ORDER_CURSOR_t4586u_EXP_E_A_FEASIBILITY_DESIGN_v1 | cba279d1 | This paper |
| COS_CONSOLIDATED_RCA_t4577u_v1.md | **f2b6a67c** | Ranked experiments; H1–H3 residuals; stop rule |
| Cursor eng RCA (PR **#647 DRAFT**, do **not** merge) | **7020a8d9** | Code facts I-1…I-6; Exp E0 spec |
| IMV grade of eng RCA | **21eb1b57** | ACCEPT_WITH_DEFECTS; H3 kickoff-timestamp proof still OPEN |
| Alex predictive RCA v2 (claims) / numbers | 04869644 / 6dac8577 | SoT MAE; encompassing; Exp A statistical lane |
| PR #646 DRAFT emit (do **not** merge) | CSV **02f6b2e2** / manifest **3073dd96** | Week-ordinal PBP emit that produced n=2992 |
| Walk-forward games export (PR #638 tip `82ffb211`) | **4fe1cdd7** | Schedule+kickoff panel |
| OOS scores `historical_oos_games.csv` | **1ee90fac** | Actuals + nflverse close proxy + `roof` |

**Institutional memory:** `no prior grades` for this research-diagnostic product. Ledger folders under `data/knowledge/nfl/` have templates only. This paper does not invent grades.

**This VM (2026-10-28):** `DATABASE_URL` **UNSET**. `LAUNCH_RESEARCH_DATABASE_URL` UNSET. `127.0.0.1:5432` refused. `psycopg` not installed. Warehouse rematerialize was not invented. No Odds calls. F2 PHI@WSH path not touched.

---

## What this paper is / is not

**Is:** a sealed, reproducible implementation design so IMV can review protocol and Ryan can later authorize **execution** of Exp E (then, only if E passes and Ryan re-approves, Exp A). Cursor owns feasibility + join/as-of recipe. Alex owns the statistical specification. IMV owns leakage controls and pass/fail criteria.

**Is not:** an Exp E run, an Exp A run, a scoring-equation change, a #647/#646 merge, a warehouse remat, a market post-hoc fit, a CERT claim, or a production patch.

Ryan t4586u authorized **preparation and pre-registration only**. Execution of A, and any change to the locked model, return to Ryan first.

```text
❌ BAD: stretch eval preds by 1/0.304; fit β on 2023/2024; merge #647; flip HFA in main
✅ GOOD: prove kickoff-honest windows first; if clean, sketch adj-EPA → same LOCKED spine; β on prior folds only
```

---

## Standing locks (unchanged)

| lock | state |
|---|---|
| NFL fireability | **NO-GO · CERT=0 · Coming Soon ON · KEEP** |
| F2 PHI@WSH | **frozen** (T-90 Nov 1 path stands) |
| Protected holdout | **2024+ never touched** for fit, tune, or look |
| `LOCKED_SCORING` | **untouched** (45.3 / 1.05 / 16.0 / 10.5 / ±6.5 / ±5.0) |
| Market blend on n=2992 SoT | `apply_market_blend=false` 2992/2992 |
| Odds API | **off** |
| Stake / PLAY chrome | **off** (numbers only) |

SoT failure (bound, not re-litigated): EPA MAE gap **+0.725**, RECORD **+0.840**, n=2992, 2013–2023, 0/11 seasons beat market. Cause **not certified**. Exp A is CONDITIONAL on Exp E and is not authorized to run from this paper.

---

## 1) Experiment E FIRST — kickoff-honest as-of audit

### 1.1 Purpose (close H3)

**H3 (IMV 21eb1b57 / RCA f2b6a67c):** week-ordinal as-of is **CODE FACT** on the n=2992 emit; kickoff-timestamp as-of is **ABSENT**. Week-grain ≡ kickoff-honest remains **HYPOTHESIS** until proven.

Exp E does **not** change MAE and does **not** rebuild ratings. It proves or falsifies that every team-week that entered `_rolling_before` for game G finished **before** `kickoff(G)`.

If E fails (any inversion, or unresolvable kickoff on a contributor), **A–D stay blocked**. If E passes, week-ordinal may be treated as kickoff-equivalent **for this panel only**, with intra-week conservatism documented (not claimed as a defect).

### 1.2 Current as-of contract (what the emit actually did)

Preferred SoT path = PR #646 `scripts/nfl/emit_epa_wf_pbp_strict_asof_t4564u.py` (not on `deploy-vercel`; cite only).

| knob | value | code |
|---|---|---|
| Grain | `(season, week) < (target_season, target_week)` | `_rolling_before` |
| Window | last **5** team-weeks, unweighted mean | `WINDOW = 5` |
| Plays | `play_type ∈ {pass, run}`, finite `epa` | `_load_pbp_week_rows` |
| Seasons loaded | **2012–2023** (2012 exists so 2013 W1 is not empty) | emit docstring |
| Franchise | `canonicalize_team` (STL/SD/OAK aliases) | `_franchise` |
| Same-week | **refused** | filter is strict `<` |
| Kickoff compare | **ABSENT** | `_rolling_before` never reads `kickoff_utc` |
| Rest emit | **7.0 / 7.0** every row | `NflGameInputs(rest_days_*=7.0)` |
| Neutral | **ABSENT** on `NflGameInputs`; HFA +1.05 always | framework L450–455 / L782–797 |
| Warehouse | **not used** | `DATABASE_URL` unset; CURRENT ROW refused |

Production / warehouse contracts are **different** and must not be mixed into E’s pass/fail:

| path | as-of | use in E? |
|---|---|---|
| #646 PBP emit | week-ordinal `<` | **YES — audit this window** |
| Warehouse `nfl_dp_team_rolling_features_weekly` | `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` + join at **same** `(season, week)` | **NO** (leaky; `DATABASE_URL` unset anyway) |
| `historical_market_backtest.py` | warehouse join | **NO** |
| `run_nfl_walkforward_backtest` | `projection_created_at < outcome_completed_at` | **NO** (stamps, not features) |
| Live `_load_team_strength_priors` | `week <= as_of_week` on stored rows | **NO** |

### 1.3 Why week-grain is not automatically kickoff-honest

This seat **re-downloaded** the pinned `games.csv` (sha256 **MATCH** `4fe1cdd7…`). Inventory (read-only; not an E verdict):

| check | n |
|---|---:|
| Panel games 2013–2023 REG+POST | 2992 |
| `kickoff_utc` empty | **0** |
| `kickoff_utc` parse fail | **0** |
| Season-weeks in panel | 234 |
| Season-weeks with **>1 calendar kickoff day** | **211 / 234** |
| Season-weeks with kickoff **span > 2 days** | **179 / 234** |
| `nflverse_location == Neutral` | **55** (incl. 3 week-22 Super Bowls) |
| `rest_days_home` / `away` | **7.0 / 7.0 on 2992/2992** |
| `nflverse_join` | `ok` 2992/2992 |
| Join to OOS `(season, week, home, away)` | **2992 / 2992** |

So intra-week kickoff spread is **common**, not rare. Week-ordinal `<` is **conservative intra-week** (Sunday cannot see Thursday of the same week label) and **untested across week-label vs calendar inversions** (COVID / flex / international / POST). That is exactly H3.

**2012 gap:** 2013 W1 windows pull prior-season team-weeks. Those 2012 games are **not** in `games.csv` (panel starts 2013). Exp E **must** pin a 2012 kickoff source or it cannot close W1.

### 1.4 Dataset pins + join recipe (E inputs)

#### Pins already sealed (usable without DB)

| artifact | sha256 | how this seat treated it |
|---|---|---|
| `games.csv` @ git `82ffb211d389b20e4d6ec305e4a0466532a48a6d` | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` | **Re-downloaded; MATCH** |
| OOS `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv` | `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed` | **In-repo; MATCH** |
| EPA WF features CSV (PR #646 run `…20261027T213659Z`) | `02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2` | On #646 branch only; **not** in this tree; do not merge |
| Rolling weekly PBP-strict CSV (same run) | `1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479` | Same; needed if E reconstructs windows without re-agg PBP |
| Emit manifest | `3073dd96178c1dffb8370cc43a817a9ec005ef110ee07b2357e8b246e8f743a8` | Documents as-of policy + rest=7.0 |

URL for `games.csv` (read-only):

```text
https://raw.githubusercontent.com/kosedge/kosedge/82ffb211d389b20e4d6ec305e4a0466532a48a6d/data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv
```

#### PBP 2012–2023 — **H1 OPEN** (HEAD-only this seat; sha256 not computed)

Exp E needs nflverse PBP to enumerate **which games** sit in each contributor team-week (and 2012 kickoffs). This paper **did not download** those parquets (that would start E). HEAD-only liveness 2026-10-28:

| season | HTTP | bytes | Last-Modified (GMT) | ETag |
|---:|---|---:|---|---|
| 2012 | 200 | 19_322_039 | 2025-04-30 06:33:24 | `0x8DD87B0E8D28515` |
| 2013 | 200 | 19_521_610 | 2024-08-25 12:30:13 | `0x8DCC501AAF2EDE3` |
| 2014 | 200 | 19_360_792 | 2024-08-25 12:30:15 | `0x8DCC501AC8708B7` |
| 2015 | 200 | 19_545_842 | 2025-04-30 06:33:27 | `0x8DD87B0EA89DFCF` |
| 2016 | 200 | 19_344_382 | 2025-04-30 06:34:28 | `0x8DD87B10F253F15` |
| 2017 | 200 | 19_050_401 | 2025-04-30 06:41:25 | `0x8DD87B2078B19D7` |
| 2018 | 200 | 19_072_097 | 2025-04-30 06:39:20 | `0x8DD87B1BD0510CA` |
| 2019 | 200 | 19_119_729 | 2025-07-31 18:17:18 | `0x8DDD05E7C69836C` |
| 2020 | 200 | 19_286_459 | **2026-08-26** 07:33:10 | `0x8DF034447C8FB65` |
| 2021 | 200 | 20_249_925 | 2026-01-08 13:13:13 | `0x8DE4EB7ADE84D25` |
| 2022 | 200 | 20_426_548 | 2026-02-12 10:25:24 | `0x8DE6A2108A8E56F` |
| 2023 | 200 | 20_534_088 | 2026-02-12 10:24:52 | `0x8DE6A20F5B300DA` |

URL recipe (same as #646 emit):

```text
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet
```

**Vintage risk (blocking for a silent re-download):** several seasons were **rewritten after** a naive “2013–2023 is frozen” assumption — notably **2020 on 2026-08-26**. #646 emit (2026-10-27) used whatever GitHub served that day; those local bytes were **not** checked into git. **H1 is not closed** until an authorized E run writes `sha256(play_by_play_{season}.parquet)` for 2012–2023 **before** building windows.

Live nflverse **`schedules/games.csv`** HEAD 200 (2_186_994 bytes) but `Last-Modified: 2026-10-28 00:36:37 GMT` — **mutable same-day**. Do **not** treat the live schedule release as a pin. Prefer (a) `kickoff_utc` already on pinned `games.csv` for 2013–2023, and (b) a **content-addressed snapshot** of 2012 (+ any missing) schedule rows written by E into `research/nfl/t4586u_exp_e_inputs/`.

#### Weather columns — **H1 PARTIAL**

| source | weather fields | pin |
|---|---|---|
| OOS 2013–2023 (n=2992) | `roof` only: outdoors 2135 / dome 424 / closed 376 / open 57 / empty **0** | file sha256 `1ee90fac…` |
| `games.csv` emit | **no** temp / wind / precip | n/a |
| n=2992 EPA emit | weather overlays **False**; `NflGameInputs.weather_*` unused | CODE FACT |
| nflverse PBP (typical) | `temp`, `wind`, `roof`, `surface` at play/game grain | **sha256 OPEN** (not downloaded) |
| Live Open-Meteo path | `nfl_rest_weather_feed.py` — 2026 cards, not 2013–23 SoT | not an E input |

Exp E does **not** need weather to close H3. Exp C/D **do**. H1 weather = pin `roof` via OOS now; pin PBP `temp`/`wind`/`roof`/`surface` **on first authorized download**, same bytes as the E PBP snapshot.

### 1.5 Join recipe (concrete)

**Do not use warehouse joins.** E is offline nflverse + pinned CSVs.

```text
G  = games.csv row                     keys: (season, week, game_id)
     kickoff(G) := parse(G.kickoff_utc)   # 2992/2992 present
     loc(G)     := G.nflverse_location    # Home | Neutral
     rest_emit  := (7.0, 7.0)             # provenance: emit constant

H  = team-week EPA from PBP            keys: (season, week, franchise)
     filter play_type ∈ {pass,run}, epa finite
     franchise := canonicalize_team(posteam|defteam)
     identical to emit _load_pbp_week_rows + _franchise

W(G, side) = last 5 H rows for franchise(side) with
             (H.season, H.week) < (G.season, G.week)
             and off_epa, def_epa_allowed not null
             # same predicate as _rolling_before

Games(TW)  = distinct PBP game_id in team-week TW
kickoff(TW) := max{ kickoff of games in Games(TW) }
               source priority:
                 1) games.csv.kickoff_utc if game_id in panel
                 2) 2012 (or other off-panel) snapshot: nflverse
                    game_date + start_time / gametime → UTC
                    (write snapshot + sha256; never live-mutate)
```

**Invariants to test (every G, both sides):**

1. **Kickoff-honest:** `max(kickoff(TW) for TW in W(G, side)) < kickoff(G)`.
2. **No self-game:** no `play.game_id == G.game_id` in W (already implied by week `<`; still count).
3. **Week-1 prior-season:** for every 2013–2023 week-1 G, list `{first, last}` of W as `YYYYWww`. Expect Y−1 last completed team-weeks; `games_in_window` ≤ 5.
4. **COVID / flex flag (not auto-fail):** any pair where week ordinal order ≠ calendar kickoff order **across different week labels** (e.g. week 12 kickoff after week 13). Flag + count.
5. **Intra-week conservatism (not a fail):** same `(season, week)` has a game with `kickoff < kickoff(G)` that was **excluded** by week `<`. Count only. This is information **left on the table**, not leakage.
6. **Franchise alias:** STL↔LAR, SD↔LAC, OAK↔LV must not split a window. Count windows that cross a relocation code.

Optional contrast (only if `DATABASE_URL` is later authorized; **not** required to close H3): same G vs warehouse row at `(season, week, team)` — E3 in eng RCA. Out of scope until DB exists.

### 1.6 Rest and neutral provenance (catalog, not a fix)

E **records** these; it does **not** implement Exp D (real rest) or Exp B (neutral HFA=0).

**Rest**

| layer | what it is | E output |
|---|---|---|
| WF emit | hard-coded 7.0/7.0 (I-1) | `n_rest_placeholder = 2992` (already true on `games.csv`) |
| `rest_days_from_schedule` | DOW heuristic (Thu→4, Mon→6, else 7); **both teams same value** | do **not** treat as true rest |
| `rest_days_from_dates` / `compute_rest_fields` | calendar / kickoff-to-kickoff | E may **compute** true days-since-last-game from schedule kickoffs as a **sidecar catalog** (`n_true_rest_ne_7`, `n_short_rest_<6`) — **no re-sim** |
| `simulate_nfl_game` | **does** consume rest (`rest_delta * 0.18`, short-rest ±0.30) | path live; emit never feeds it |

**Neutral**

| layer | what it is | E output |
|---|---|---|
| `games.csv` `nflverse_location` | Home 2937 / Neutral **55** | `n_neutral=55`; list week-22 SBs |
| `NflGameInputs` | **no** `neutral_site` field | CODE FACT (no re-sim) |
| Decompose | always +1.05 HFA | CODE FACT |
| Web 2026 slate | display HFA 0 on listed neutrals | **not** in historical sim |

Pooled MAE impact of 55 × 1.05 is tiny (~0.019 pts) and is **not** a claim that HFA-on-neutral caused +0.725. E only proves the flag is unused.

### 1.7 Pass / fail count outputs (machine contract)

Authorized E script (when Ryan says go — **not this PR**) writes:

```text
research/nfl/t4586u_exp_e_kickoff_asof/
  manifest.json
  SHA256SUMS                 # inputs + outputs
  counts.json                # the table below
  inversions.csv             # one row per FAIL window (empty if pass)
  week1_windows.csv          # first/last contributing season-weeks
  covid_flex_flags.csv
  intraweek_conservative.csv
  rest_catalog.csv           # true rest vs 7.0; no sim
  neutral_catalog.csv        # 55 rows
```

`counts.json` **required keys** (integers; no implied pass from silence):

| key | meaning | pass rule |
|---|---|---|
| `n_games` | panel size | must = 2992 |
| `n_windows` | 2 × games with a non-empty W | report |
| `n_windows_empty` | W empty (should be ~0 given 2012 load) | **FAIL if > 0** unless pre-declared bye/relocation exception list |
| `n_contributors` | sum of team-weeks in all W | report |
| `n_kickoff_ok` | windows with `max(kickoff(TW)) < kickoff(G)` | |
| `n_kickoff_fail` | inversions | **FAIL if > 0** |
| `n_kickoff_unknown` | missing/unparsed kickoff on a contributor | **FAIL if > 0** (no silent skip) |
| `n_self_game_leak` | `G.game_id` in W | **FAIL if > 0** |
| `n_week1` | week=1 games | report (expect 11 × ~16 REG + POST W1 if any) |
| `n_covid_flex_flags` | week-label vs calendar disagreement | **flag; does not auto-fail** unless an inversion is also in `n_kickoff_fail` |
| `n_intraweek_conservative` | same-week earlier kickoffs excluded | informational |
| `n_franchise_cross` | window crosses relocation alias | report; fail only if alias split **drops** a game that should have been in W |
| `n_rest_placeholder` | emit rest == 7.0 both sides | expect 2992 |
| `n_neutral` | `nflverse_location==Neutral` | expect 55 |
| `pbp_sha256` | map season → sha256 | **required**; H1 close |
| `games_csv_sha256` | must = `4fe1cdd7…` | **FAIL if mismatch** |
| `verdict` | `PASS` \| `FAIL` \| `BLOCKED` | |

**Stop rule (pre-registered):**

- `verdict=FAIL` → **block A–D**. Rebuild windows on kickoff clock; do not “explain away” inversions in the same breath as an A run.
- `verdict=BLOCKED` → input hash / 2012 snapshot / download failure. Not a pass.
- `verdict=PASS` → H3 **closed for this panel**. Week-ordinal may be used as kickoff-equivalent **with intra-week conservatism noted**. Still not a redesign GO.

Expected MAE change on PASS: **none**. Integrity only.

### 1.8 Implementation sketch (research-only; not written this PR)

When (and only when) execution is authorized:

1. New script `research/nfl/t4586u_exp_e_kickoff_asof_audit.py` (mirror #646 imports; **do not** copy emit into `services/model-service/src` production).
2. Reuse `_rolling_before` / `_franchise` / play filter by **importing from a copied research module** or by inlining the same 15-line predicate — bit-identical to #646. Do not “improve” the window while auditing it.
3. Download PBP 2012–2023 to a gitignored cache; write sha256 **before** parquet read.
4. Snapshot 2012 schedule kickoffs once; pin sha256.
5. Emit `counts.json` + inversion CSVs. Exit code 0 only on `PASS`.
6. No `simulate_nfl_game`. No `LOCKED_SCORING` edit. No Odds. No `DATABASE_URL` required.

**Reuse (cite, do not merge):**

- `#646` emit for window definition.
- `#647` `research/nfl/t4577u_engineering_rca_diagnostics.py` for n=2992 join convention (`m = home−away`, `mm = −market_spread_home`).
- `nfl_rest_weather_feed.compute_rest_fields` / `adjusted_sos.rest_days_from_dates` as **catalog** helpers only.
- CFB warehouse rule (`available_at` strictly before kickoff) as the **honesty standard**, not as imported code.

### 1.9 What E must not do

- Re-sim the 2992 panel.
- Replace 7.0 rest or zero HFA on Neutral (those are E1 / E2 / B / D, separately gated).
- Treat warehouse CURRENT ROW as the as-of SoT.
- Download live `schedules/games.csv` and call it pinned (it moved **today**).
- Touch 2024+.
- Claim “no leakage” from week `<` alone.

---

## 2) Experiment A CONDITIONAL — opponent-adjusted ratings + fold-fit β

**Status:** design sketch only. **Do not run.** Gated on Exp E `PASS` **and** a new Ryan GO. Alex owns the statistical spec; this section is the Cursor plug-in so A cannot silently become a scoring change or a market fit.

### 2.1 What A is / is not

| A is | A is not |
|---|---|
| Opponent-adjusted **off/def EPA** at team-week, estimated **pregame** | A `k = 1/0.304` stretch of eval preds |
| β (pts per rating **or** EPA scale) fit on **prior folds only** | β set to ~20.9 or to market SD |
| Same `simulate_nfl_game` / `epa_to_strength_indices` / `LOCKED_SCORING` | Edit of 16.0 / 0.75 / ±6.5 / 1.05 in `main` |
| Research generator under `research/nfl/` | Production remat, packaged-EPA flip, overlay ON |
| One look at 2023 after freeze | Fit or peek at 2024+ |

RCA stop (IMV-accepted; **void if changed post-run**): FAIL unless 2023 encompassing **c CI excludes 0** **OR** paired 10k-bootstrap MAE-gap improvement CI excludes 0 **and** point improvement ≥ **0.10 pts**. Residual SD / β from prior folds only.

### 2.2 Why the locked equation stays frozen

Eng RCA 1.4 (CODE FACT): there is **no** literal 12.5 constant. Emergent slope ≈ `0.75 × 16.0 = 12` plus ±0.25 / ±6.5 clamps (elite ceiling ≈ 7.55). Alex’s 12.46 vs ~20.9 empirical pts/EPA is **the locked core doing what it is coded to do**. Pasting `×1.68` on eval rows is the forbidden curve-fit (RCA E4).

A’s allowed move: **change the EPA that enters** `epa_to_strength_indices`, and/or estimate a **fold-local** β **inside the generator** on training folds — then **freeze** it before the eval fold. The decompose weights in `nfl_handicapping_framework.py` stay at `LOCKED_SCORING`.

```68:86:services/model-service/src/services/nfl_season_engine/efficiency_backbone.py
def epa_to_strength_indices(
    *,
    off_epa: float,
    def_epa_allowed: float,
    pressure_generated: float = 0.0,
    pressure_allowed: float = 0.0,
) -> Dict[str, float]:
    """Canonical EPA→index conversion (mirrors ``tasks._epa_to_strength_indices``)."""
    pressure_delta = float(pressure_generated) - float(pressure_allowed)
    offense_index = _clamp(
        1.0 + (float(off_epa) * 0.75) + (pressure_delta * 0.18), *_OFF_CLAMP
    )
    ...
```

```100:109:services/model-service/src/services/nfl_regression_diagnose.py
LOCKED_SCORING = {
    "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
    "base_total_points": 45.3,
    "home_field_points": 1.05,
    "base_efficiency_max_total_points": 5.0,
    "base_efficiency_max_margin_points": 6.5,
    "base_efficiency_total_weight": 10.5,
    "base_efficiency_margin_weight": 16.0,
}
```

Tests: `test_scoring_equation_not_silently_retuned`. A research script that imports `simulate_nfl_game` and **does not** pass `config_overrides` for those keys keeps the lock.

### 2.3 Opponent-adjusted ratings (research estimator)

**Do not promote production KAV or KE Football opp-adj.**

| existing object | why it is not A |
|---|---|
| `data_platform_nfl.kav.iterative_opponent_adjust` | Production-adjacent; week `W−1` lag; needs warehouse; `overlays_off` can null KAV on live remat |
| `ke_football/opp_adj.py` | `OPP_ADJ_PROMOTED is False` / `NO_ADJUSTMENT_WINNER` — closed |
| `efficiency_backbone.opponent_adjust_epa` | League-mean center, not joint SOS |
| Emit `_rolling_before` | Raw team-week EPA — **ABSENT** opponent adjustment (eng RCA §B.8) |

**Pattern to fork (research-only):** CFB `services/model-service/src/services/cfb_warehouse/research_opp_adj.py`

```text
y_{g,i} = μ + h · home_{g,i} + off_i + def_j + ε
```

- `y` = garbage-weighted (or NFL: pass/run unweighted, to match emit) EPA/play.
- Ridge + prior `n0` + prior decay; league off/def centered.
- `fit_joint` / `games_before_cutoff` / `predict_game` already exist for CFB.
- Flags: `RESEARCH_ONLY = True`, `NOT_KE_RATINGS = True`.

NFL port (proposed module name, **not created this PR**):

```text
research/nfl/t4586u_exp_a_research_opp_adj.py          # estimator
research/nfl/t4586u_exp_a_fold_validate.py             # folds + β
```

NFL-specific rules (pre-register; Alex may tighten):

| rule | proposal |
|---|---|
| Eligible plays | `play_type ∈ {pass, run}`, finite `epa` — **same as emit** (do not silently add sack/penalty/ST) |
| OT | exclude `qtr >= 5` (CFB analogue) |
| Neutral `h` | `home=0` when `nflverse_location==Neutral` **inside the rating model only** — this is **not** Exp B (sim HFA still +1.05 unless B is separately authorized) |
| As-of cutoff | **kickoff** if E passed; else do not run A |
| Relocation | `canonicalize_team` so STL/LAR share a franchise rating with a documented split date |
| Cold start | week 1 = prior-season posterior (time-honest); no offseason shrink unless in the **frozen** param grid |

**KAV is a cousin, not a substitute:** iterative `adj = raw + (league − opp)` is a different estimator than joint ridge. A must name `ESTIMATOR_ID` (e.g. `nfl-research-opp-adj-epa-v0-ridge-joint`) so results cannot be laundered as “KAV worked.”

### 2.4 Chronological folds + β (prior folds only)

**H2 residual (RCA):** pre-register the CV grid / fold manifest; β fitted, not set to ~20.9. Alex owns the grid; Cursor locks the **information boundary**.

Proposed fold manifest (Cursor recommendation for IMV; Alex may replace **before** any run):

| fold | train / fit ratings | fit β | evaluate | status |
|---|---|---|---|---|
| F1…F10 | seasons `< S` for S = 2014…2022 (expanding) | OLS / ridge on **those** train games’ **pregame** adj-index vs actual margin | season S (≤2022) | **primary evidence** |
| F-2023 | freeze params from ≤2022 selection | **no refit** | 2023 n=285 one look | **supportive only** (already multiply inspected) |
| 2024+ | — | — | — | **forbidden** |

Inner week grain (CFB `pregame_fit` analogue): for game G in season S, ratings use **only** games with `kickoff < kickoff(G)` (E-honest). β for fold S is fit on **completed prior seasons**, not on S’s residuals.

**β definition (pick one before run; do not shop):**

1. **Preferred (information-preserving):** leave `epa_to_strength_indices` + decompose **unscaled**. β is **not** a post-sim multiplier. Opponent adjustment is the only new information.
2. **Allowed alternative (RCA text):** a scalar `β_epa` such that `off_epa_in = β_epa * adj_off` (and a `β_def` or shared β) chosen on prior folds by MAE or likelihood — **then frozen**. This is a **generator** parameter, not `pred_eval * k`.
3. **Forbidden:** `pred_2023 *= (sd_market / sd_pred)` or `a + b * pred` fit on the eval fold; any fit that uses `market_spread_home` as a target.

Market lines stay **labels for scoring MAE/encompassing**, never design-matrix columns for β.

Param grid lives in Alex’s spec. Cursor constraint: `select_params` may see **≤2022 folds only**. 2023 is `evaluate_seasons` once.

### 2.5 Plug-in to simulate / framework **without** changing production

```text
PBP (H1-pinned) → research_opp_adj.pregame_fit(kickoff cutoff)
                → adj off/def EPA per franchise
                → [optional frozen β_epa]
                → epa_to_strength_indices          # UNCHANGED
                → NflGameInputs.offense/defense_*  # UNCHANGED fields
                → simulate_nfl_game(
                     market_spread_home=None,      # blend OFF
                     market_total=None,
                     config_overrides=None,        # LOCKED defaults
                     rest_days_*=7.0               # until D/E1 authorized
                   )
                → compare to emit 02f6b2e2 and to market (OOS 1ee90fac)
```

| surface | A may | A must not |
|---|---|---|
| `NflGameInputs` indices | yes (research script) | write `nfl_game_context` / packaged priors |
| `simulate_nfl_game` | import and call | change its source |
| `config_overrides` | omit | pass new `margin_weight` / HFA / caps |
| `tasks.run_nfl_market_simulations` | ignore | remat live slate |
| `prefer_packaged_epa` / `overlays_must_stay_off` | bypass by not calling remat | flip production flags |
| KAV fields on inputs | leave None | silently enable KAV as a stand-in for A |
| `apps/web` / F2 | ignore | any path under PHI@WSH |

Baseline for the paired comparison = **pinned EPA emit** (`02f6b2e2`, unblended, 4000 sims, rest 7/7, same seed namespace if re-sim). A’s research emit uses a **new** seed namespace (`t4586u-exp-a-research`) so rows cannot collide with the SoT CSV.

Production `deploy-vercel` tip (`bfc89f57` at this cut) **cannot** regenerate `games.csv` (export + `apply_market_blend` live on #638). A re-score / research sim should **import** `simulate_nfl_game` from this tip (locked equation) and **read** features from research outputs — not require merging #646/#647/#638.

### 2.6 Metrics (Cursor wiring; Alex numbers)

Same sign convention as eng diagnostics / Alex 88b3b7ce:

```text
m      = home_score − away_score          # from OOS
mm     = − market_spread_home             # nflverse close proxy; not Odds
pm_epa = − epa_trailing_spread_home       # emit / A research
pm_A   = − a_research_spread_home
```

Report: MAE(pm, m), MAE-gap vs market, bias, slope act~mdl, SD ratio, encompassing `c` (pm_A | mm), 10k paired bootstrap on MAE-gap. **Primary evidence = ≤2022 folds.** 2023 supportive. No 2024+.

If A loses on ≤2022 folds, **stop**. Do not hunt 2023.

### 2.7 Forbidden (E4 + Ryan t4586u)

- Unrestricted model redesign.
- Executing A from this paper.
- Tuning on 2024+.
- Cosmetic scale-factor fit / eval-pred stretch.
- Waiving gates / claiming predictive certification.
- Merge / deploy / publish / Odds.
- Changing F2 PHI@WSH capture path.
- Implementing B/D/C “while we are here.”

---

## 3) Dataset hash pins for H1 — status table

RCA H1: hash-pin Exp C/D inputs (PBP 2013–2023; schedules provenance; weather cols). E needs the same bytes plus **2012**.

| input | needed by | sha256 | status this seat |
|---|---|---|---|
| Walk-forward `games.csv` (schedule + kickoff + location) | E, A | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` | **PINNED + re-verified** |
| OOS actuals + `roof` + market proxy | E join, A score, C roof | `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed` | **PINNED + in-repo** |
| EPA WF features (SoT baseline) | A baseline | `02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2` | **PINNED on #646**; not in this tree |
| Rolling weekly strict-as-of | E reconstruct | `1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479` | **PINNED on #646** |
| Emit manifest | provenance | `3073dd96178c1dffb8370cc43a817a9ec005ef110ee07b2357e8b246e8f743a8` | **PINNED on #646** |
| nflverse PBP 2012 | E W1 windows | — | **OPEN** — HEAD live; sha256 not computed (no download) |
| nflverse PBP 2013–2023 | E, A, C/D | — | **OPEN** — HEAD live; **vintage drift** (2020 rewritten 2026-08-26) |
| Live nflverse `schedules/games.csv` | 2012 kickoffs only | — | **UNPINNABLE live** (Last-Modified 2026-10-28). Snapshot-on-E-run required |
| PBP weather `temp`/`wind`/`roof`/`surface` | C/D | — | **OPEN** — columns exist on typical nflverse PBP; not hashed here |
| Warehouse `nfl_dp_*` 2013–22 | E3 contrast only | — | **BLOCKED** — `DATABASE_URL` unset (Alex blocker **db42ad49**; still true) |

**H1 verdict for this paper:** schedules (2013–2023 panel) **closed**. PBP + weather-from-PBP + 2012 kickoff snapshot **open by design** until an authorized E download writes `SHA256SUMS`. That is a **blocker for running C/D/A**, not a blocker for **designing** them. It **is** a blocker for claiming H1 closed.

**Close recipe (authorized E, still no Odds / no prod write):**

```text
for y in 2012..2023:
  curl -L -o play_by_play_$y.parquet $PBP_URL
  sha256sum play_by_play_$y.parquet >> SHA256SUMS
# snapshot 2012 schedule rows actually used
# refuse to proceed if any sha256 missing
```

Do not use Railway `nfl_dp_raw_objects.checksum` as a substitute while `DATABASE_URL` is unset.

---

## 4) Feasibility, risks, effort

Effort is **technical** (files / tests / deps), not calendar. RCA ranks E as **S** and A as **M**.

### 4.1 Exp E — feasible offline

| item | note |
|---|---|
| Feasible now? | **Yes**, without DB, without Odds, without merging #646/#647 |
| Work | one research script + 2012–2023 PBP download (~230 MB) + 2012 kickoff snapshot + `counts.json` |
| Deps | pandas/pyarrow (emit already assumes them); pinned `games.csv`; copy of `_rolling_before` predicate |
| IMV surface | every FAIL row is a `(game_id, side, contrib_game_id, kickoff_contrib, kickoff_G)` tuple |

**Risks**

| risk | severity | mitigation |
|---|---|---|
| PBP vintage ≠ #646 emit bytes | **High** for “same windows” | Hash-on-download; if 2020/2022/2023 drift vs emit-era cache, **declare BLOCKED** and do not pretend identity |
| 2012 kickoff source | **High** for W1 | Snapshot + sha256; `n_kickoff_unknown>0` fails |
| Live schedule release mutates | **High** if used as pin | Do not; use `games.csv` + frozen 2012 slice |
| Franchise split (STL/SD/OAK) | Med | `canonicalize_team`; report `n_franchise_cross` |
| COVID 2020 week labels | Med | flag file; fail only on true kickoff inversion |
| Intra-week conservatism misread as leakage | Med | separate count; not in FAIL |
| Downloading PBP construed as “running A” | Process | E script **must not** call simulate / fit β |
| #646 not on default branch | Low | cite + `git show`; do not merge |

### 4.2 Exp A — feasible only after E PASS + Ryan GO

| item | note |
|---|---|
| Feasible as a **research script**? | **Yes**, patterned on CFB `research_opp_adj*` + emit’s `simulate_nfl_game` call |
| Feasible as a **production patch**? | **No** under current authority |
| Work | NFL ridge port; fold manifest; research emit; metrics vs `02f6b2e2` + OOS |
| Deps | E `PASS`; H1 PBP hashes; Alex grid; IMV protocol review |
| Production collision | none if A never writes `nfl_market_projections` / packaged priors / web |

**Risks**

| risk | severity | mitigation |
|---|---|---|
| A becomes a scale-fit | **High** | β not fit to market; no eval stretch; IMV stop 0.10 pts + c CI |
| A silently edits LOCKED knobs | **High** | no `config_overrides`; test lock stays |
| Using KAV / warehouse CURRENT ROW as “adj” | **High** | separate `ESTIMATOR_ID`; no DB |
| Fitting β on 2023 because n is small | **High** | fold table above; 2023 look once |
| Neutral `h=0` in ratings confused with Exp B | Med | document; sim HFA stays 1.05 |
| Rest still 7/7 so A vs emit is not a rest ablation | Med | intended; D is separate |
| `deploy-vercel` cannot rebuild SoT CSV | Low | read pinned CSV; don’t remake it |
| Compute (joint ridge × 2992 pregame fits) | Med | CFB-style week-cutoff batching; still research-only |

### 4.3 Shared / process

| risk | mitigation |
|---|---|
| `DATABASE_URL` still unset | E/A designed to **not need** it. E3 warehouse contrast remains blocked (db42ad49). |
| Merging #647 “for convenience” | **Forbidden.** Cite 7020a8d9 / 21eb1b57 only. |
| Odds “just for closes” | **Forbidden.** Market proxy remains nflverse `spread_line` on OOS (`1ee90fac`). |
| F2 / Nov 1 path drift | This PR is docs-only under `data/ops/` + sidecar. No web/sim production files. |
| Claiming CERT from a design paper | Verdict remains **CERT=0**. |

---

## 5) Authorization boundary (execution)

This paper **does not authorize** the E script to run. When Ryan authorizes E:

1. Branch off `deploy-vercel` (or an approved research branch). Do not merge #646/#647.
2. Implement **only** `research/nfl/t4586u_exp_e_kickoff_asof_audit.py` + outputs.
3. No A code in that same PR unless a later order says so.
4. Stop after `counts.json`. Ping sha8 + inversion count.
5. A remains **CONDITIONAL** on `verdict=PASS` **and** a **new** Ryan decision.

---

## 6) Explicit non-claims

- No GREEN, no edge, nothing fireable, **CERT=0**.
- H3 is **not** closed by this paper; the **proof procedure** is.
- H1 is **not** fully closed (PBP/weather sha256 OPEN).
- I-1 rest placeholder and I-3 neutral absence remain **CODE FACTS**; they are catalogued, not fixed.
- Warehouse CURRENT ROW leakage remains a **contract** fact; magnitude still **UNMEASURED**.
- Opponent-adjusted ratings are **ABSENT** on the emit; that does not prove A will move encompassing `c`.
- F2 PHI@WSH unchanged. Coming Soon ON. sealed_count increment is CoS’s, not this seat’s to invent.

---

## 7) Deliverable seal

| file | role |
|---|---|
| `data/ops/CURSOR_EXP_E_A_FEASIBILITY_DESIGN_t4586u_v1.md` | this paper |
| `data/ops/CURSOR_EXP_E_A_FEASIBILITY_DESIGN_t4586u_v1.sha256` | sidecar of this file’s sha256 |

**Owners:** Cursor (this design) · Alex (A statistical spec) · IMV (protocol review) · Ryan (execution GO).

NFL NO-GO · CERT=0 · F2 frozen · no Exp A run · no #647 merge
