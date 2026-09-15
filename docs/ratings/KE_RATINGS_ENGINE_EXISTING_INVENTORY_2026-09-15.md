# KE Ratings Engine — Existing System Inventory

**Date:** 2026-09-15  
**Scope:** Inventory / audit only. No model fitting. No production, board, or code changes.  
**Sports:** NFL, CFB, NBA, CBB (NCAAM), WNBA, MLB.  
**Constraint honored:** 2025 CFB play-by-play was **not opened**. CFB PBP evidence is from code, packaging scripts, ops inventory metadata, and 2026-facing snapshots only.  
**No `KE Ratings Engine` module exists by that name.** This document inventories everything already implemented that maps onto the target concepts.

Target stack (architecture context — **not implemented as one spine**):

```text
RAW DATA → KE SPORT FEATURES → KE RATINGS ENGINE → KE POWER / PLAYER RATINGS
         → GAME PROJECTION → FAIR LINE / TOTAL / PROPS → MODEL vs MARKET → EDGE BOARD
```

Ratings are supposed to measure team quality. Projection asks what happens when profiles meet. Betting models must not invent what “good” means.

---

## Classification legend

Each concept is classified **exactly one** of:

| Class | Meaning |
| --- | --- |
| **REAL_AND_VALIDATED** | Owned (or contracted) measurement, wired to a consumer, with tests and/or graded ops evidence. |
| **REAL_UNVALIDATED** | Real computation exists and is used, but is not market-graded / not a ratings SoT. |
| **PARTIAL** | Real pieces exist; incomplete coverage, not fully wired, or split across stacks. |
| **PROXY** | Derived from a correlated signal (vendor z-score, OPS, YPG, unit-grade heuristic) rather than the named measurement. |
| **PLACEHOLDER** | UI copy, hook field, or empty desk; no computed rating. |
| **50_FILL/CONSTANT** | League-average 50 / 1.0 / hardcoded constant used as a stand-in for missing measurement. |
| **DEAD_CODE** | Computed or stored, but not consumed by the live ratings / compose / KEI path. |
| **MISSING** | No implementation found. |

**Vendor vs proprietary (honesty rule used in the % estimate):** KenPom AdjEM/AdjOE/AdjDE, ESPN/Connelly SP+, Basketball-Reference ORtg/DRtg/BPM, and D-Ratings / EvanMiya / BartTorvik feeds are **real third-party ratings**. They are **not** a proprietary KE Ratings Engine. The inventory records them. The % estimate does **not** treat them as KE Ratings already built.

---

## 1. Executive summary

### How much of the KE Ratings Engine is already present?

**About 28% of a proprietary KE Ratings Engine is already present.**

A looser “something exists for this concept, including vendor tables and synthetic proxies” reading is **about 41%**. That looser number is **not** the KE Ratings Engine. Treating KenPom, SP+, or Basketball-Reference season tables as KE would pad the answer.

| Slice | Estimated present | What that means |
| --- | ---: | --- |
| **Proprietary KE Ratings Engine (headline)** | **~28%** | Owned measurement → opponent-aware rating → persisted artifact → live model consumer |
| Concept checklist including vendor / proxy | ~41% | Same 13 concepts, counting vendor feeds and labeled proxies |
| NFL only (closest sport) | ~64% of NFL cells | Owned EPA backbone on the live Layer-1 path |
| CFB only | ~34% of CFB cells | Dual stack: vendor SP+ live; owned PBP EPA **research-only** |
| NBA / WNBA | ~25–30% each | Vendor ORtg/DRtg/pace carry + KEI; no power desk; no SOS |
| CBB | ~22% proprietary / ~40% vendor-product | KenPom Lab is validated **fair math**, not KE ratings |
| MLB | ~12% | Per-game OPS / pitcher-quality proxies; **no season ratings engine** |

### What is actually here

1. **NFL is the only sport with an owned play-level efficiency spine on the live path.** nflverse PBP → situational / rolling tables → `efficiency_backbone` v1.1 → `TeamStrengthState` → Power Ratings desk + True PR + season engine + Edge Board. That is the closest existing analogue to KE Ratings.
2. **CFB has two efficiency worlds that must not be collapsed.** Live compose/KEI uses **final-2025 SP+ carry** plus **synthetic success / explosiveness / pace**. An owned garbage-weighted PBP EPA opponent-adjust warehouse exists (2014–2025 metadata) but is **`used_in_spread: false`**. Measured PBP success, explosiveness, stuff, and red-zone EPA sit on team-game rows and are **not** promoted into weekly adjusted ratings or compose.
3. **Basketball ratings are vendor season tables plus a KEI/fair translation layer.** NBA/WNBA: Basketball-Reference ORtg/DRtg/net/pace, 0.85 carry shrink, BPM (NBA) or PER−15 (WNBA). CBB: KenPom AdjEM/AdjOE/AdjDE/AdjT as SoT; Lab B2/B2-PACE is leakage-tested fair math and is **quarantined from product KEI**.
4. **MLB has no ratings engine.** Daily PA/Poisson sim uses OPS-index offense and starter/bullpen quality. No season team book, no SOS, no power ratings JSON.
5. **There is no shared KE Ratings Engine.** Season-engine folders, KEI `model_*` vs `handicap_*`, and `/pro/power-ratings/[sport]` are reusable **plumbing**. The mathematics are sport-specific and incomplete.
6. **Downstream (projection → fair line → Edge Board) is more complete than ratings.** Do not confuse a working Edge Board with a finished ratings engine.

### What is not here

- No module named KE Ratings Engine.
- No unified opponent-adjusted success / explosiveness / havoc / finishing book across sports.
- No football havoc metric (NFL pressure is a proxy; CFB havoc is UI copy).
- No true CFB tempo (plays/game or seconds/play) on the live path.
- No proprietary CBB/NBA/WNBA opponent-adjusted estimator.
- No MLB wOBA / wRC+ / WAR / ERA− / season SOS.
- Player “strength” is production multipliers or vendor BPM/PER, not a KE player ratings layer.

---

## 2. Sport-by-sport KE Ratings Engine gap matrix

Rows = KE concepts. Columns = sports. One classification per cell (best existing artifact). N/A = concept does not apply (basketball special teams).

| KE concept | NFL | CFB | NBA | CBB | WNBA | MLB |
| --- | --- | --- | --- | --- | --- | --- |
| Offensive efficiency | **REAL_AND_VALIDATED** | **PARTIAL** | **REAL_UNVALIDATED** | **PROXY** | **REAL_UNVALIDATED** | **PROXY** |
| Defensive efficiency | **REAL_AND_VALIDATED** | **PARTIAL** | **REAL_UNVALIDATED** | **PROXY** | **REAL_UNVALIDATED** | **PARTIAL** |
| Special teams | **REAL_UNVALIDATED** | **PROXY** | *N/A* | *N/A* | *N/A* | *N/A* |
| Pace / tempo | **PARTIAL** | **PROXY** | **REAL_UNVALIDATED** | **PROXY** | **REAL_UNVALIDATED** | **MISSING** |
| Explosiveness | **PARTIAL** | **PROXY** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| Finishing | **PARTIAL** | **DEAD_CODE** | **PROXY** | **MISSING** | **PROXY** | **MISSING** |
| Havoc / disruption | **PROXY** | **MISSING** | **MISSING** | **PLACEHOLDER** | **MISSING** | **MISSING** |
| EPA / PPA | **REAL_AND_VALIDATED** | **PARTIAL** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| Opponent adjustment | **PARTIAL** | **PARTIAL** | **PROXY** | **PROXY** | **PROXY** | **PROXY** |
| Strength of schedule | **REAL_UNVALIDATED** | **PARTIAL** | **MISSING** | **REAL_UNVALIDATED** | **MISSING** | **MISSING** |
| Power ratings | **REAL_AND_VALIDATED** | **REAL_UNVALIDATED** | **MISSING** | **PROXY** | **MISSING** | **MISSING** |
| Team strength | **REAL_AND_VALIDATED** | **REAL_UNVALIDATED** | **REAL_UNVALIDATED** | **PROXY** | **REAL_UNVALIDATED** | **MISSING** |
| Player strength | **PROXY** | **PARTIAL** | **PARTIAL** | **MISSING** | **PARTIAL** | **PARTIAL** |

### How to read the football cells

- **NFL offensive/defensive efficiency** are owned EPA/play mapped into Layer-1 indices, with unit tests and ops smell tests. That is why they are REAL_AND_VALIDATED.
- **CFB offensive/defensive efficiency** are **PARTIAL** because the live path is vendor SP+ carry (real opponent-adjusted source, not owned, stale to 2025) while the owned PBP EPA adjust is real but **not** the compose SoT.
- **CFB explosiveness / success / pace** are **PROXY** on the live path (SP+ z-heuristics and skill−F7). Warehouse PBP explosive/success/RZ/stuff are measured at team-game grain and then **dropped** at iterative adjust — see §5.
- **CFB finishing** is **DEAD_CODE**: `rz_epa_raw` is stored on team-game rows and never enters weekly adj or compose.
- **CFB havoc** is **MISSING**. `/pro/cfb/tempo` is a copy shell that uses board totals “while dedicated tempo feeds finish join.”
- **NFL havoc** is **PROXY**: pressure generated/allowed inside `epa_to_strength_indices`, not a havoc rate.
- **NFL explosiveness** is **PARTIAL**: pass explosive only (league anchor 0.085); rush explosive not split.

### How to read the basketball / baseball cells

- **NBA/WNBA ORtg/DRtg/pace** are REAL_UNVALIDATED **vendor carry**, not a KE estimator. Classified REAL_UNVALIDATED because the shrink/rebase/KEI path is real code with tests — not because it is proprietary KE.
- **CBB off/def/pace** are **PROXY** for KE: KenPom AdjOE/AdjDE/AdjT. Lab B2/B2-PACE is REAL_AND_VALIDATED **as a KenPom fair engine** and is called out in §6; it is still not KE Ratings.
- **CBB SOS** is KenPom `sos` in the parquet lake; live ensemble weight on non-KenPom components is **0**.
- **CBB power ratings** are latest-season AdjEM export — not point-in-time.
- **MLB offense** is OPS / 0.720. **MLB defense** is starter + bullpen quality, not a team defensive rating. **MLB player strength** is `starter_quality` (ERA/WHIP default; FIP/xFIP/stuff modes off).

---

## 3. Reusable shared infrastructure vs sport-specific mathematics

### Shared (reusable plumbing — not KE math)

| Piece | What it does | Sports | KE Ratings status |
| --- | --- | --- | --- |
| Season-engine folder pattern | Priors → compose / project-game → status API | NFL, CFB, NBA, WNBA | Pattern only. **MLB has no `mlb_season_engine/`.** |
| `TeamStrengthState`-style O/D indices ~1.0 | Layer-1 slot Edge Board already consumes | NFL (canonical); CFB compose indices | NFL math is sport-specific. CFB 0–100 → index is a parallel convention. |
| KEI contract (`model_*` vs `handicap_*`) | Research fair vs product line | NFL, CFB, NBA, WNBA, CBB, MLB | Downstream of ratings. Shared **product** layer. |
| `resolveKeiGames` / Edge Board merge | Fair-lines → KEI columns | All six | Consumer, not a rating. |
| `/pro/power-ratings/[sport]` | Generic table UI | All sports routed | **NFL desk + CBB JSON only.** Others empty. |
| `data-paths.ts` | `power_ratings_{sport}.json`, `kei_lines_{sport}.json` | Generic | File convention. |
| Carry shrink toward league mean | `value' = mean + s*(value − mean)` | NFL prior/current blend; CFB `EFF_CARRY_SHRINK=0.85`; NBA/WNBA `TEAM_CARRY_SHRINK=0.85` | Shared **idea**. Constants and scales differ. |
| Opponent-adjust iterators | `observed − opponent expected`, shrink thin samples | NFL KAV (12 iter); CFB warehouse EPA (4 iter) | Shared **idea**. Not one library. **Not on CFB live path.** |
| JSON packaged cold-start | Engine image can boot without warehouse | NFL backbone JSON; CFB SP+ snapshot + research prior; NBA/WNBA Ch1–4 packs | Persistence pattern. |
| Postgres feature marts | Situational / rolling / matchup / context | NFL `nfl_dp_*`; MLB `mlb_game_context` / `mlb_market_projections` | Sport schemas. No shared ratings schema. |

### Sport-specific mathematics (not reusable as-is)

| Sport | Rating scale | Core identity of “good” | Can other sports copy the math? |
| --- | --- | --- | --- |
| NFL | Index ~0.82–1.24; Model PR in points vs avg | EPA/play + pressure + soft success/explosive/RZ/ST | Closest KE template. Football-only play definitions. |
| CFB live | 0–100 SP+ z-map, shrink to 50 | Vendor SP+ O/D + roster/QB/units | No — vendor + 50-scale identity stack. |
| CFB warehouse | EPA/play, league-centered 0 | Garbage-weighted PBP EPA | Football PBP only; unused by KEI. |
| NBA | ORtg / DRtg / net / pace | BR advanced + BPM rebase | Basketball possession math; vendor SoT. |
| CBB | KenPom AdjEM / AdjOE / AdjDE / AdjT | Vendor efficiency + tempo | Do not treat as KE. Lab is KenPom-asof fair. |
| WNBA | Same as NBA, 40-min / harmonic pace / PER−15 | BR WNBA advanced | Parallel to NBA, thinner talent feed. |
| MLB | OPS index 0.78–1.25; SP quality 0.82–1.18 | Counting-stat quality, not season ratings | No ratings book to port. |

**Implication:** Shared infrastructure can host a KE Ratings Engine. It does not currently *be* one. Sport mathematics cannot be swapped. NFL’s backbone is the only live owned ratings-like spine.

---

## 4. Per-sport inventory (trace, formulas, consumers)

Traces use: **raw → feature → calculation → persisted artifact → model consumer → UI consumer.**

### 4.1 NFL

**North star:** `data/ops/nfl-model-vision.md`. Layer 1 team strength feeds season sim, Edge Board, Power Ratings desk, True PR. Player production is a separate spine (fantasy/props), not KE player ratings.

#### Canonical live trace

```text
nflverse PBP
  → nfl_dp_play_by_play
  → nfl_dp_team_situational_weekly     (EPA, success, explosive pass, RZ, pressure, pace)
  → nfl_dp_team_rolling_features_weekly (3g/5g trailing)
  → nfl_dp_matchup_features_weekly     (home/away/diff 5g + KAV + ST KAV)
  → efficiency_backbone.TeamEfficiencyPackage
  → package_to_strength_indices / TeamStrengthState
  → season engine expected_team_points
       ├─ power_ratings_desk (Method B Model PR)
       ├─ true_pr_product
       ├─ nfl_simulator + handicapping framework
       └─ Edge Board / /pro/power-ratings/nfl / /pro/nfl/model
```

Cold start when rolling empty: `scripts/nfl/build_packaged_efficiency_backbone.py` → `nfl_team_efficiency_backbone_2026.json` (legacy mirror `nfl_team_epa_priors_2026.json`).

#### Concept cards

**Offensive / defensive efficiency — REAL_AND_VALIDATED**

- **Formulas** (`efficiency_backbone.py`):
  - `opponent_adjust_epa(raw, league) = raw − league_mean` (league centering, not full SOS).
  - `offense_index = clamp(1.0 + off_epa*0.75 + (pressure_gen − pressure_allowed)*0.18, 0.82, 1.22)`
  - `defense_index = clamp(1.0 + (−def_epa_allowed)*0.90 + pressure_delta*0.14, 0.82, 1.24)`
  - Soft additives (shrunk when variance high): success vs 0.44 (`_W_SUCCESS=0.12`), explosive pass vs 0.085 (`_W_EXPLOSIVE=0.08`), RZ TD vs 0.55 (`_W_RZ=0.06`), pass/run/early-down EPA (v1.1), ST bleed `_W_ST=0.065`.
  - Prior/current blend: `w_current = clamp(games/8, 0, 1)`. Games 0–2 labeled prior-heavy.
- **Source:** nflverse via `nfl_dp_team_situational_weekly`.
- **Coverage:** Packaged 2026 priors = 2025 REG. Rolling materialized 2023–2026 per `nfl-efficiency-backbone-v1.1-20260808.md` (2286 rolling rows cited).
- **PIT:** Current season week-capped; completed games gated by schedule scores. Matchup/KAV join week W−1 for pre-game.
- **Cadence:** Weekly situational ingest; rematerialize rolling; rebuild packaged at least once per offseason.
- **Validation:** `tests/test_nfl_efficiency_backbone.py`, `test_nfl_true_pr_foundation.py`, `test_nfl_tasks.py`; ops v1 / v1.1; hierarchy smell tests (SEA above ARI; NE not crushed).
- **Persistence:** Postgres situational / rolling / matchup; packaged JSON.
- **Consumers:** `_load_team_strength_priors`, season engine, simulator, Power Ratings desk, True PR, Edge Board.

**EPA — REAL_AND_VALIDATED.** PBP `AVG(epa)` / `AVG(success)` in data-platform ingest. No NFL PPA.

**Special teams — REAL_UNVALIDATED.** `st_index = clamp(1.0 + st_epa*0.55, 0.85, 1.15)` from `nfl_dp_team_st_kav_weekly` (`build_st_kav_weekly.py`; coverage cited 2013–2025 in builder). Missing ST → `st_index=1.0` labeled `neutral_hook` (constant, not a 50-fill). Desk labels ST **approximate**.

**Pace — PARTIAL.** Measured `pace = (off_plays/games) / 62.0`, clamp 0.88–1.12. Plus `game_script.py` coaching overlays and a **static** UI pack `apps/web/lib/nfl-structural-pace-2026.ts` (PROXY for Edge Board bullets).

**Explosiveness — PARTIAL.** Pass explosive ≥20 yards in situational ingest; additive vs 0.085. Rush explosive not split (ops v1). KAV uses yards ≥12 (separate product). Missing → league 0.085, not 50.

**Finishing — PARTIAL.** `red_zone_td_rate` additive + matchup `diff_red_zone_td_rate_5g` (simulator weight). Season-engine `red_zone.py` is role shares for player TDs (PROXY relative to team finishing).

**Havoc — PROXY / named metric MISSING.** Pressure rates in the index formula; sack rate in tendency profiles; OL `protection_index` is an injury heuristic.

**Opponent adjustment — PARTIAL.** Three stacks that must not be double-counted:

| Stack | Class | Formula / note |
| --- | --- | --- |
| League-mean center | PROXY | `raw − league` in backbone |
| Past SOS | REAL_UNVALIDATED (tests: `test_nfl_adjusted_sos_past.py`) | `adj_off = raw_off + 0.70*(league_def − mean_opp_def)`; prior side only; W−1 opp book |
| KAV iterative | REAL_UNVALIDATED | 12-iter EPA/success/explosive; **not** Layer-1 PR (`power_ratings_desk.py` forbids double-count) |
| Projected 2026 SOS | REAL_UNVALIDATED | Outlook only; does not rewrite intrinsic PR |
| External DVOA hook | PLACEHOLDER | Only if caller passes values |

**Power ratings / team strength — REAL_AND_VALIDATED.** Method B: `expected_team_points` vs synthetic average opponent, then `zero_center`. Tuesday shrink `PR_pub = (1−α)*PR_prior + α*PR_data` (`ALPHA_BY_WEEK` 0.12→0.80). Ryan Adj defaults 0; never overwrites Model PR. Script: `scripts/nfl/tuesday_power_ratings_update.py` → `data/ops/nfl-power-ratings-desk/latest.json`. UI: `apps/web/lib/power-ratings.ts`, `/pro/power-ratings/nfl`.

**True PR — REAL_AND_VALIDATED (display).** `intrinsic_pr = 0.5*(full_strength_off + full_strength_def)`. API `GET /nfl/season-engine/true-pr`. UI `/pro/nfl/model`.

**Player strength — PROXY.** `qb_talent_factor_from_prior_ypg` / skill YPG multipliers in `nfl_player_projection_engine.py`. QB premium (`qb_premium.py`, scale 0.058, cap 0.070) is REAL_UNVALIDATED team-level, not a player rating book. Continuity score is REAL_UNVALIDATED (curated 2026 staff flags).

**50-fill / constants:** `placeholder_league_avg` O/D = 1.0 when no artifact. Packaged EPA-only fill uses success 0.44 / pressure 0.16 / RZ 0.55. **NFL does not use a 0–100 / 50-fill pattern for team ratings** (contrast CFB).

**KAV (owned DVOA-like) — REAL_UNVALIDATED; game-level, not Layer-1.** `kav-v1`: `kav_pct = (adj_epa − league_mean) / 0.15`. Net KAV = off − def. Consumers: handicapping framework, simulator, matchup features. Not a second power rating.

---

### 4.2 CFB

**Engine stamp:** `cfb-season-engine-v0.15-power-sot`.  
**Honesty docs:** `data/ops/cfb-efficiency-backbone-20260804.md`, `docs/CFB_CH2_EFF_PACK_AUDIT.md`, `docs/CFB_CH2_EFF_CARRY_SCORECARD.md`, `data/ops/cfb-efficiency-preseason-prior-v1-20260812.md`, `docs/CFB_TOTALS_HOT_AUDIT.md`.

#### Live compose / KEI trace (published spreads/totals)

```text
Final-2025 SP+ (ESPN story / cfbupdate / optional CFBD /ratings/sp)
  → scripts/cfb/package_efficiency_2025_carry.py
  → cfb_efficiency_snapshot_2025_carry_2026.json
       as_of=2026-08-31 · 147 teams · 141 mapped SP+ · 6 league_average_fill
  → efficiency.build_efficiency_profile
       + optional in_season_update (margin residuals; often no-op)
  → roster_construction + qb_situation + position_groups + HFA + coaching
  → compose_team_projection → expected_team_points → project_game
  → apply_cfb_kei (spread bias guard; kei_total = model_total identity)
  → KEI pack / Edge Board / /pro/cfb/project-game
```

#### Parallel warehouse trace (research only — does not change KEI)

```text
HD PBP 2014–2025 (NOT opened this audit)
  → aggregate_team_games (garbage weights; EPA, success, explosive, stuff, RZ)
  → iterative_adjust (EPA only, 4 iters, shrink n/(n+80))
  → week_snapshots (week W uses week < W) + season finals
  → preseason_prior.program_component
  → cfb_preseason_prior_2026.json (147 teams, as_of=2026-08-12)
  → project-game research_prior block only
  used_in_spread: false
```

Ops inventory metadata (`data/ops/cfb-efficiency-preseason-prior-v1-20260812-inventory.json`): 20,588–20,591 team-games, 25,741 week rows, 1,568 season finals, 0 claimed week-leakage rows. **This audit did not open the parquet.**

#### Live efficiency formulas (vendor → 0–100)

From `scripts/cfb/package_efficiency_2025_carry.py` and `efficiency.py`:

```text
z_off = (sp_offense − μ_off) / σ_off
z_def = (μ_def − sp_defense) / σ_def          # inverted so higher = better
off_eff_raw = clamp(50 + 18*z_off, 5, 95)
def_eff_raw = clamp(50 + 18*z_def, 5, 95)
success_*_raw = clamp(50 + 16*(0.85*z_*), 5, 95)
expl_raw = clamp(50 + 17*max(-1.5, z_off − 0.35*max(0, −z_off)), 5, 95)
eff' = 50 + 0.85*(eff_raw − 50)               # EFF_CARRY_SHRINK
```

`success_*` and `explosiveness` are documented **SP+-correlated proxies, not PBP**. `pbp: not_used` in the snapshot source block.

#### Compose / scoring (not a second rating)

Weights in `priors.py` (current, post-v0.8): `WEIGHT_OFF_EFF=0.34`, roster 0.22, QB 0.24, skill 0.10, OL 0.10; defense eff 0.36. Post-compose: `QB_INDEX_BLEND=0.26`, `EFF_OFF_INDEX_BLEND=0.12`, `EFF_DEF_INDEX_BLEND=0.12`.

```text
pace = clamp(1.0 + (skill − front_seven)/200, 0.85, 1.20)
pace += (explosiveness − 50)/400              # tiny; totals audit mean expl ~49.8
base = LEAGUE_TEAM_PPG * (off_idx/opp_def_idx)^response * unit_boosts * pace
st_nudge = 0.015 * ((st_home + st_away)/2 − 50)   # SPECIAL_TEAMS_TOTAL_SCALE; split to both scores
power_index = 0.5*(offense_index + defense_index)
```

`success_off` / `success_def` are **driver metadata only** — not in the scoring formula. Packaged `sp_special_teams` is **unused** in compose.

#### Warehouse EPA formulas (owned, not live)

- Explosive play flag: `EPA ≥ 1.0` OR `yards ≥ 15` (`efficiency_adj.py`).
- Garbage-time weights: competitive margin 16, deep 24, late taper, min weight 0.10 (`garbage.py`).
- `adjusted = observed − opponent expected`; 4 iterations; center mean 0; `off_epa_adj = (n/(n+80))*adj`.
- Team-game stores `off_success_raw`, `off_explosive_rate`, `stuff_rate`, `rz_epa_raw`. **`iterative_adjust` outputs EPA only.**
- Program prior: `program_net_epa` weighted across prior seasons; `program_points = net * 28`.

#### Classification summary (CFB)

| Concept | Live compose | Warehouse | Notes |
| --- | --- | --- | --- |
| Off / def efficiency | PARTIAL | REAL_UNVALIDATED | SP+ carry vs owned EPA adj |
| Success | PROXY | DEAD_CODE (raw only) | Not in adj or scoring |
| Explosiveness | PROXY | PARTIAL / unused | Pace nudge only on live |
| Pace | PROXY | MISSING | skill−F7 + expl/400 |
| Havoc | MISSING | MISSING | UI copy |
| Finishing | MISSING | DEAD_CODE | `rz_epa_raw` unwired |
| ST | PROXY | MISSING | Unit grade 50-default + 0.015 nudge; SP+ ST unused |
| EPA / PPA | MISSING | REAL_UNVALIDATED | No live PPA feed |
| Opponent adj | PROXY (vendor SP+) | REAL_UNVALIDATED | Dual stack |
| SOS | PARTIAL | PARTIAL | Implicit in SP+ / season-sim opponents |
| Power / team | REAL_UNVALIDATED | research prior unused | `cfb_power_sot_2026.json` |
| Player / QB / roster | PARTIAL | roster/QB class in prior | Formulas real; numerics approximate |

**PIT:** Preseason frozen 2025 SP+ → 2026. In-season `in_season_update` moves eff from **margin residuals** (`RESIDUAL_TO_EFF=0.35`) and nudges success/expl 0.6×Δeff — still proxy-linked, not PBP re-rate. Warehouse week snapshots are leakage-tested (`test_cfb_warehouse_leakage.py`).

**Cadence:** Manual rematerialize of SP+ snapshot; warehouse via `scripts/cfb/build_efficiency_preseason_prior.py` to HD parquets.

**Validation:** `test_cfb_season_engine.py`; CH2 pack/carry scorecards; warehouse leakage tests; totals hot audit (Over-drunk from matchup^response, **not** pace/expl). Historical calibration is a **PROXY** universe (roster/QB/units all 50).

**UI:** `/pro/cfb/project-game` Off/Def chips; `/pro/cfb/model`; `/pro/cfb/projections`; `/pro/cfb/tempo` **PLACEHOLDER**; team-research stats labels Tempo/Havoc/Explosiveness/Success with sections `status: "pending"`.

---

### 4.3 NBA

#### Trace

```text
Basketball-Reference 2025–26 team ratings + advanced pace
  → scripts/nba/build_team_prior_ch1.py
       team' = league_mean + 0.85*(team − league_mean)   # ORtg, DRtg, net, pace
  → nba_team_prior_2025_26_carry_2026_27.json
  → scripts/nba/build_roster_minutes_ch2.py
       player_net = Σ(BPM × min) / 240
       residual = clip(ch1_net − player_net, ±3)
       team_net = player_net + residual
       implied_ppg = pace × ORtg / 100
  → Ch3 situation (home/B2B/travel/altitude, clip ±3 pts)
  → Ch4 nba_kei.py
       margin_home = (net_h − net_a)*(pace/100) + situation_Δ
       kei_spread_home = −margin_home
       kei_total = ppg_h + ppg_a
  → /nba/fair-lines → apps/web nba-fair-lines / Edge Board
```

Parallel: `nba_possession_simulator.py` — pace = arithmetic mean; `PPP ≈ 0.5*(ORtg + (200 − opp_DRtg))/100`. `/nba/fair-lines?source=auto` falls back to Ch4 KEI when the sim slate is empty.

| Concept | Class | Evidence |
| --- | --- | --- |
| Off / def / pace / net | REAL_UNVALIDATED | BR tables + Ch1 shrink; tests `test_nba_team_prior_ch1.py` |
| Opponent adj | PROXY | Season-level BR, not rolling adj |
| SOS | MISSING | — |
| Power ratings product | MISSING | No `power_ratings_nba.json`; `/pro/power-ratings/nba` empty |
| Player strength | PARTIAL | Decayed BPM; RAPTOR/EPM/LEBRON/DARKO **MISSING** as SoT |
| Explosiveness / havoc / EPA | MISSING | STL/BLK exist as Ch5 count stats only |
| Finishing | PROXY | Sim 2P/FT scaling to target PPP |
| Four factors | PROXY | Sim 3P/TOV/ORB rates, not published team four factors |
| Thin defaults | 50_FILL/CONSTANT | `pace=100`, `ortg/drtg=114` when thin (`nba_data.py`) |

**PIT:** Frozen preseason packs (`as_of` ~2026-09-01 on Ch4). Not game-day PIT.  
**Cadence:** Manual `scripts/nba/build_*`.  
**Validation:** Chapter scorecards + unit tests; grade harness exists; not a market-graded ratings engine.

---

### 4.4 CBB (NCAAM)

#### Product / legacy KEI trace

```text
KenPom + BartTorvik + EvanMiya + Haslam + D-Ratings CSVs
  (apps/web/data/raw/ratings/, seasons ~2016–2026)
  → ingest_kenpom.py / build_ratings.py / build_ensemble_ratings.py
  → full_ensemble_ratings.parquet
  → merge_games_ensemble.py
  → kei_lines_ncaam.json + power_ratings_ncaam.json
  → /pro/power-ratings/ncaam, KEI Lines, Edge Board
```

**Live ensemble weights** (`ensemble_weights.json`): `adjem: 1.0`, torvik/barthag/bpr/haslam/dratings **0**, `home_court: 2.8696`. Code defaults in `merge_games_ensemble.py` still list a multi-source mix; **the file on disk is KenPom-only.**

**Power export:** rank by latest-year AdjEM (`scripts/export_power_ratings.py`) — **PROXY**, not game-day PIT.

**Legacy backtest** (`docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`, 2026-02-21): 406 games, 49.01% ATS, **−1.97% ROI**.

#### Lab fair trace (quarantined from product KEI)

```text
Weekly kenpom_YYYY-MM-DD.parquet
  → kenpom_asof.py (backward asof; assert_no_kenpom_leakage)
  → fair_b2.py / fair_b2_pace_v1.py
  → data/ops/lab/ncaam/ only
```

```text
fair_spread = clip(adjem_h − adjem_a + HCA, ±28)
fair_total = (pace/100) * (adjoe_h + adjde_a + adjoe_a + adjde_h) / 2
pace = (adjt_h + adjt_a) / 2
B2-PACE margin = clip(adjem_diff * (adjt_h+adjt_a)/200 + 2.8696, ±28)
```

Lab scorecard v1.2 cites Test-A n=2205, leakage 0. **This is a validated KenPom fair engine, not KE Ratings.** Protocol forbids writing `kei_lines_ncaam.json` / product power paths.

| Concept | Class | Notes |
| --- | --- | --- |
| AdjOE / AdjDE / AdjEM | PROXY (KE) / vendor REAL | Product SoT = KenPom |
| Pace AdjT | PROXY (KE); Lab totals REAL_AND_VALIDATED as KenPom math | Product merge totals optional |
| SOS | REAL_UNVALIDATED | KenPom `sos` in parquet; weight 0 in live spread |
| Power ratings | PROXY | Season AdjEM JSON |
| Player strength | MISSING | EvanMiya BPR team-level, weight 0 |
| Havoc / tempo UI | PLACEHOLDER | `/pro/ncaam/tempo` copy; board totals until feed join |
| Explosiveness / finishing / EPA | MISSING | — |
| Haslam four-factor fingerprint | DEAD_CODE relative to fair | CSVs ingested; not in B2 |

---

### 4.5 WNBA

Mirror of NBA with WNBA constants.

| Difference vs NBA | Detail |
| --- | --- |
| Talent | `PER − 15` (BPM not on BR WNBA) |
| Pace in sim | **Harmonic** mean; clamp 68–95; league ~81 |
| KEI default pace | ~80 |
| Ch1 pack | `wnba_team_prior_2026.json` (YTD 2026 shrink 0.85) |
| Power JSON | MISSING |
| SOS / EPA / explosiveness / havoc | MISSING |
| Props PLAY cap | 4 (NBA 8) |

Trace: `scripts/wnba/build_*` → Ch4 `wnba_kei.py` (same net×pace/100 + situation) → `/wnba/fair-lines` → Edge Board. Classification pattern matches NBA: REAL_UNVALIDATED vendor carry, not KE Ratings.

---

### 4.6 MLB

**No `mlb_season_engine`.** Daily `mlb-v1-pa-sim` + Postgres. Enterprise report: overall **D / no-go** on CLV/Brier bar (`data/ops/mlb-model-enterprise-grade-report.md`). KEI plumbing works; ratings engine does not exist.

#### Trace

```text
MLB Stats API / Savant / Open-Meteo / Odds API
  → mlb_data (OPS offense, SP/BP, park, weather, lineups)
  → optional stuff / pitch_matchup (flags default OFF except batter–pitcher mul)
  → mlb_simulator (Poisson innings)
  → mlb_model_handicap (model_* vs handicap_*)
  → mlb_market_projections + mlb_game_context
  → /mlb/fair-lines → KEIMLB / Edge Board
```

| Concept | Class | Formula / note |
| --- | --- | --- |
| Offensive efficiency | PROXY | `ops_index = clamp(OPS / 0.720, 0.78, 1.25)`; composite 0.46 season + 0.24 split + 0.18 recent + 0.12 lineup |
| wOBA / wRC+ / WAR | MISSING | Team-research copy only |
| Defensive efficiency | PARTIAL | No `defense_index`; run prevention via starter + bullpen |
| FIP | REAL_UNVALIDATED, **default off** | `(13HR+3(BB+HBP)−2K)/IP + 3.20`; prod S0 is **era_whip** |
| Pace | MISSING | Fixed inning Poisson λ |
| Explosiveness / havoc / finishing / EPA | MISSING | Barrel/EV only on optional pitch path |
| Opponent adj / SOS | PROXY / MISSING | Platoon vl/vr shrink; no season SOS |
| Power / team book | MISSING | No `power_ratings_mlb.json` |
| Player (SP) | PARTIAL | `starter_quality`; named-star constants + name-hash fallback = **50_FILL/CONSTANT** |
| Park | PROXY | Static table ~0.93–1.12 |
| Bullpen fatigue | REAL_AND_VALIDATED (helpers) | Last 3 games, games before `as_of` |
| Run differential | DEAD_CODE | Ingested from standings; not a sim driver |

---

## 5. Special section — football: measured vs proxy vs 50-fill

This section exists because CFB attribution / totals work already showed that **named football signals on the live path are often not measured.** Do not relabel them as KE features.

### 5.1 Side-by-side

| Signal | NFL live path | CFB live compose / KEI | CFB warehouse (research) |
| --- | --- | --- | --- |
| EPA / play | **Measured** (nflverse) | **Not used** | **Measured** (owned PBP `EPA`) |
| Success rate | **Measured** (nflverse `success`) | **PROXY** from 0.85×SP+ z | **Measured** on team-game (`EPA_success`); **not adjusted / not composed** |
| Explosiveness | **Measured (pass only)** vs 0.085 | **PROXY** from SP+ z heuristic | **Measured** `EPA≥1` or `yards≥15`; **not adjusted / not composed** |
| Pace | **Measured** plays/game ÷ 62 | **PROXY** `(skill−F7)/200 + (expl−50)/400` | **Not modeled** |
| Finishing / RZ | **Measured** RZ TD rate (soft additive) | **MISSING** | **Measured** `rz_epa_raw`; **unwired** |
| Stuff / disruption | Pressure / sack **proxies** | **MISSING** (havoc UI only) | **Measured** `stuff_rate`; **unwired** |
| Special teams | **Measured** ST KAV / ST EPA when table present; else 1.0 | Unit grade + 0.015 total nudge; **SP+ ST column unused** | — |
| Opponent adjust | League center + Past SOS + KAV (split) | **Vendor SP+ methodology** | **Owned 4-iter EPA adj** |
| 50-fill | Rare (index 1.0 placeholder / league rate anchors) | **Common on 0–100 scale** — see §5.3 | Cold-start adj **0** (league-centered EPA) |

### 5.2 CFB attribution finding (already documented — restated)

`docs/CFB_TOTALS_HOT_AUDIT.md`: mean pace **0.996**, mean explosiveness proxy **~49.8**. The +8 vs market totals gap is **matchup-response score inflation**, not pace/explosiveness and not power-SoT fill. `success_*` do not enter `expected_team_points`. Football factor attribution (`summarize_nfl_factor_attribution_from_points`) has **no CFB analogue**; CFB drivers explicitly disclaim calibrated attribution (`team_projection.py`).

`docs/CFB_CH2_EFF_PACK_AUDIT.md`: warehouse PBP adj is **research_prior only**. Live outline is SP+ → z → 0–100 → compose.

`data/ops/cfb-efficiency-backbone-20260804.md`: success/explosiveness are **proxies, not true PBP**.

### 5.3 Explicit CFB 50-fill / constant inventory

| Location | When | Value | Class |
| --- | --- | --- | --- |
| Efficiency snapshot | 6 of 147 teams `league_average_fill` | all eff fields **50.0** | 50_FILL/CONSTANT |
| `build_efficiency_profile` | Non-FBS / missing code | 50.0 all eff | 50_FILL/CONSTANT |
| Official FBS missing SP+ | Packager / loader | **Hard-fail** — must not 50-fill | Guard (good) |
| `compose_team_projection` | `efficiency is None` | `off_eff=def_eff=50` | 50_FILL/CONSTANT |
| `types.py` defaults | Missing grades | Most unit/QB fields **50.0** | PLACEHOLDER defaults |
| `position_groups` | All units ≈50 | `fidelity=placeholder` | 50_FILL/CONSTANT |
| `historical_calibration.build_historical_proxy_state` | 2022–25 hist-cal universe | roster/QB/units **all 50**; expl = `50 + 0.15*(off−def)` | 50_FILL/CONSTANT + PROXY |
| Hist-cal success | Reuses off/def eff | `success_off=off_eff` | PROXY |
| Warehouse cold-start week | No games yet | `off_epa_adj=def_epa_adj=0` | CONSTANT (EPA scale) |
| `power_sot_v0.15_fill` | Slate code lacks compose | Placeholder indices from pack | PLACEHOLDER |
| `thin_sample_labeled` | Referenced, no producer | — | DEAD_CODE |

### 5.4 NFL fills (do not conflate with CFB 50s)

| Location | Value | Class |
| --- | --- | --- |
| Missing ST | `st_index=1.0` `neutral_hook` | CONSTANT |
| Missing explosive / success / RZ | League 0.085 / 0.44 / 0.55 | CONSTANT anchors |
| No strength artifact | `placeholder_league_avg` O/D 1.0 | 50_FILL/CONSTANT (index scale) |
| Packaged EPA-only rebuild | success 0.44, pressure 0.16, RZ 0.55 | PROXY constants |
| Demo strength bumps | Explicitly demo-only | DEAD_CODE for real mode |

### 5.5 What would count as *measured* football KE features (inventory only — not a build plan)

Already measured somewhere, **not** a KE Ratings Engine yet:

- NFL: EPA, success, pass-explosive, RZ TD, pressure, plays/game, ST EPA/KAV, KAV iterative adj.
- CFB warehouse: EPA, success, explosive, stuff, RZ EPA — **team-game grain only**.
- CFB live: **none** of success/explosiveness/pace/havoc/finishing are measured.

UI that implies they exist (`sport-config.ts` CFB statsLabels `Tempo / Havoc / Explosiveness / Success`; `/pro/cfb/tempo` havoc card) is **PLACEHOLDER**.

---

## 6. Dependency graph — who consumes what

### 6.1 Cross-sport consumer matrix

| Consumer | NFL | CFB | NBA | CBB | WNBA | MLB |
| --- | --- | --- | --- | --- | --- | --- |
| Edge Board assemble | Strength indices + PR enrich + structural pace | KEI pack + trusted market | Fair-lines KEI | Odds + KEI file | Fair-lines KEI | Fair-lines KEIMLB |
| `/pro/power-ratings/[sport]` | Method B desk JSON | Empty unless JSON added | Empty | AdjEM season JSON | Empty | Empty |
| True PR / model desk | `/pro/nfl/model` | `/pro/cfb/model`, project-game | Fair-lines | KEI Lines | Fair-lines | `/pro/mlb/fair-lines` |
| Season engine strength | EPA backbone **live** | SP+ compose **live**; warehouse research | Ch1–4 packs | No season engine (apps/web Lab) | Ch1–4 packs | **None** |
| Simulator / MC | `nfl_simulator` + matchup pack | Compose `project_game` | Possession sim (optional) | Lab B2 (quarantined) | Harmonic possession sim | Poisson PA sim |
| Props / fantasy | Player production spine (not KE ratings) | Player hooks from EP × pace | Ch5–7 | — | Ch5–7 | — |
| Tempo / havoc UI | Edge Board pace bullets | **Placeholder desk** | — | **Placeholder desk** | — | — |

### 6.2 NFL dependency (condensed)

```text
PBP EPA/success/explosive/RZ/pressure/ST
        │
        ├─ efficiency_backbone ──► TeamStrengthState ──┬─ expected_team_points ─ season sim
        │                                              ├─ power_ratings_desk ─ /pro/power-ratings/nfl
        │                                              ├─ true_pr_product ─ /pro/nfl/model
        │                                              └─ Edge Board O/D indices
        │
        ├─ KAV ──► matchup features / handicapping / sim   (NOT Layer-1 PR)
        └─ matchup 5g diffs ──► nfl_simulator spread_signal
```

### 6.3 CFB dependency (condensed)

```text
SP+ 2025 ──► 0–100 pack ──► compose ──► project_game ──► KEI ──► Edge Board
Roster/QB/units ─────────────┘              │
                                            └─ power_sot JSON ──► projections desk

PBP EPA warehouse ──► research_prior JSON ──► project-game research block only
PBP success/expl/stuff/RZ ──► team-game rows ──► (no live consumer)
```

### 6.4 Basketball / baseball (condensed)

```text
NBA/WNBA: BR ratings ──► Ch1 shrink ──► Ch2 talent rebase ──► Ch3 sit ──► Ch4 KEI ──► fair-lines ──► Edge Board
          (no power JSON)

CBB:      KenPom lake ──┬─ product merge (adjem weight 1) ──► kei_lines + power_ratings_ncaam.json
                        └─ Lab B2/B2-PACE (ops/lab only)

MLB:      Stats API OPS/SP ──► context ──► Poisson sim ──► handicap KEI ──► Edge Board
          (no ratings book, no power JSON)
```

### 6.5 What does **not** consume ratings (but looks like it might)

- CFB `/pro/cfb/tempo` and CBB `/pro/ncaam/tempo` — board totals / copy, not a tempo feed.
- Team-research section shells — almost all `status: "pending"`.
- CBB Torvik / EvanMiya / Haslam / D-Ratings — ingested, **weight 0** on live ensemble.
- CFB warehouse success/explosiveness/stuff/RZ — stored, not composed.
- MLB standings `run_diff` — ingested, not simulated.
- NFL external DVOA hook — optional, unused in training.
- NFL record-based `team_strength_from_record` — legacy fallback; live path prefers EPA priors.

---

## 7. Validation evidence index (existing — not new fits)

| Area | Evidence | What it validates |
| --- | --- | --- |
| NFL backbone | `test_nfl_efficiency_backbone.py`, ops v1 / v1.1 | Hierarchy smell; ST/splits labels; no demo in real mode |
| NFL Past SOS | `test_nfl_adjusted_sos_past.py` | Prior-only schedule adjust, lag book |
| NFL Power desk | `test_nfl_power_ratings_desk.py`, `docs/runbooks/nfl-tuesday-power-ratings.md` | Method B, zero-center, Tuesday α |
| NFL KAV | data-platform KAV module + matchup tests | Iterative adj + W−1 lag (not Layer-1 PR) |
| CFB compose | `test_cfb_season_engine.py`, CH2 scorecards | Eff moves projections; hard-fail official FBS |
| CFB warehouse | `test_cfb_warehouse_leakage.py`, `test_cfb_efficiency_preseason_prior.py` | PIT week `< W`; prior `season < 2026` |
| CFB totals | `docs/CFB_TOTALS_HOT_AUDIT.md` | Pace/expl **not** the Over; matchup^response is |
| NBA/WNBA chapters | `test_nba_*`, `test_wnba_*`, Ch1–4 scorecards | Pack math, not market CLV |
| CBB Lab | `tests_pipeline/test_ncaam_*`, scorecard v1.2 | KenPom asof leakage 0; **not** product KEI |
| CBB product KEI | methodology doc −1.97% ROI / 406 games | Legacy ensemble, KenPom-only weights |
| MLB | 30+ `test_mlb_*.py`; enterprise report D/no-go | Leakage hygiene real; **ratings bar not met** |

---

## 8. Coverage, PIT, cadence (quick reference)

| Sport | Historical coverage of rating-like inputs | Point-in-time safety | Update cadence |
| --- | --- | --- | --- |
| NFL backbone | Situational/rolling 2023–2026; ST builder 2013–2025; packaged prior = 2025 | Week-capped current; KAV/matchup W−1 | Weekly ingest + rematerialize |
| NFL KAV | Game + weekly as-of W | `week <= W` compute; pre-game W−1 | With PBP ingest |
| CFB SP+ live | Final 2025 only → 2026 carry | **Not** in-season PIT | Manual packager |
| CFB warehouse | PBP seasons 2014–2025 **in code/ops metadata** (files not opened) | Week W uses `< W`; leakage tests | HD build script |
| NBA/WNBA | One prior season carry (+ WNBA YTD 2026) | Frozen packs | Manual chapter builds |
| CBB KenPom lake | CSVs ~2016–2026 | Product power JSON **not** PIT; Lab asof **is** | Snapshot / Lab materialize |
| MLB | Current-season API YTD + 30d recent | Context `as_of`; Statcast `game_date−1` when enabled | Daily Celery cycle |

---

## 9. STOP

This document is an **inventory**. It is not a design, a migration plan, a rematerialize order, or a permission to retune compose weights, unwire SP+, promote warehouse EPA onto KEI, join tempo/havoc feeds, or open 2025 CFB PBP.

**Do not:**

- Build a KE Ratings Engine from this note.
- Refit, rename, replace, or “clean up” existing proxies.
- Treat KenPom / SP+ / BR / OPS as KE Ratings.
- Treat Edge Board or KEI as proof that ratings exist.
- Collapse CFB’s two efficiency worlds into one sentence.
- Call CFB explosiveness / pace / havoc / success “measured.”
- Ungate PLAY tags or change boards.

**For Ryan / CoS review only.** Next action, if any, is a separate assignment after this inventory is accepted.

---

## Appendix A — Key file index

| Path | Role |
| --- | --- |
| `services/model-service/src/services/nfl_season_engine/efficiency_backbone.py` | NFL owned ratings-like spine |
| `services/model-service/src/services/nfl_season_engine/adjusted_sos.py` | NFL past SOS |
| `services/model-service/src/services/nfl_season_engine/power_ratings_desk.py` | Method B Model PR |
| `services/model-service/src/services/nfl_season_engine/true_pr_product.py` | True PR display |
| `services/data-platform-nfl/src/data_platform_nfl/kav.py` | Owned KAV (not Layer-1) |
| `scripts/nfl/build_packaged_efficiency_backbone.py` | NFL packaged artifact |
| `scripts/nfl/tuesday_power_ratings_update.py` | PR desk publish |
| `services/model-service/src/services/cfb_season_engine/efficiency.py` | CFB SP+ profile loader |
| `scripts/cfb/package_efficiency_2025_carry.py` | SP+ z-map + proxies + 50-fill |
| `services/model-service/src/services/cfb_season_engine/team_projection.py` | Compose + pace proxy + ST nudge |
| `services/model-service/src/services/cfb_warehouse/efficiency_adj.py` | Owned PBP EPA adj (research) |
| `services/model-service/src/services/nba_season_engine/` | NBA Ch1–4 |
| `services/model-service/src/services/wnba_season_engine/` | WNBA Ch1–4 |
| `apps/web/src/build_ratings.py` / `build_ensemble_ratings.py` | CBB vendor merge |
| `apps/web/src/ncaam_lab/fair_b2.py` / `fair_b2_pace_v1.py` | CBB Lab fair (quarantined) |
| `apps/web/lib/power-ratings.ts` | Power ratings UI loader |
| `apps/web/app/(pro)/pro/[sport]/tempo/page.tsx` | CFB/CBB tempo **placeholder** |
| `services/model-service/src/services/mlb_data.py` | MLB OPS / SP quality |
| `services/model-service/src/services/mlb_simulator.py` | MLB game sim (not ratings) |

## Appendix B — Prior ops / audit docs this inventory relied on

- `data/ops/nfl-efficiency-backbone-v1-20260807.md`
- `data/ops/nfl-efficiency-backbone-v1.1-20260808.md`
- `data/ops/nfl-power-ratings-desk-20260811.md`
- `data/ops/cfb-efficiency-backbone-20260804.md`
- `data/ops/cfb-efficiency-preseason-prior-v1-20260812.md`
- `data/ops/cfb-full-model-foundation-report.md`
- `docs/CFB_CH2_EFF_PACK_AUDIT.md`
- `docs/CFB_CH2_EFF_CARRY_SCORECARD.md`
- `docs/CFB_TOTALS_HOT_AUDIT.md`
- `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`
- `data/ops/mlb-model-enterprise-grade-report.md`

## Appendix C — Audit constraints checklist

| Constraint | Status |
| --- | --- |
| No modify / delete / rename / refit / replace of models or boards | Honored (docs-only) |
| No model fitting | Honored |
| 2025 CFB PBP not opened | Honored |
| Classifications evidence-backed | File paths + formulas + existing tests/ops cited |
| STOP — no build plan | §9 |

---

*End of inventory. 2026-09-15.*
