# #14 Phase A — CBB / NCAAB evidence inventory

**Status:** inventory only · **no** product UI · **no** new model code · **no** props work  
**Ticket:** Linear [KOS-28](https://linear.app/kosedge/issue/KOS-28/14-phase-a-cbb-inventory-keepverifyrebuildretiredata-gap) · Notion [#14 CBB Production Model (LOCKED)](https://app.notion.com/p/3d1568a6d5df81ddb87bf0e2b7a093b6)  
**Base:** `deploy-vercel` @ inventory branch `cursor/cbb-phase-a-inventory-ef25`  
**As of:** 2026-09-04 (UTC)  
**Philosophy:** CBB does not get special treatment. Classify with receipts. No sentimental KEEP.

**Naming SoT (product):** sport key `ncaam`, label `CBB` (`apps/web/lib/sports.ts`).  
**Odds API key:** `basketball_ncaab`.  
**Colloquial aliases:** `cbb` / `ncaab` appear in scripts, Prisma comments, and orphan routes — not in `SPORTS[]`.

**v1 markets (later):** fair spread · projected total · win prob/ML where defensible.  
**Props:** OUT for v1 (see Explicit OUT).

---

## 1. Executive summary

- CBB “engine” is almost entirely an **`apps/web` Python pipeline** (KenPom-weighted KEICMB) + **static processed JSON/parquet** — not a model-service season engine.
- Live product key is **`ncaam`**. Model-service contributes **Odds API edge-board only** (`GET /edge-board/ncaam/today` → `basketball_ncaab`).
- Documented backtest (2026-02-21): **406** graded games, **49.01%** ATS, **−1.97%** ROI; merged events **10,270**; live weights are **KenPom-only** (`adjem:1`, all others `0`). Receipt: `apps/web/data/processed/kei_backtest_results.json` + `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`.
- Historical odds **in repo**: 488 open + 488 close JSON under `apps/web/data/raw/odds/{open,close}/` dated **2022-11-01 → 2025-12-04** (dense 2022-11→2024-01, then 2025-11/12 pocket). API earliest possible: **2020-11-16** (docs). Pre-2022 and dense 2024–25 **DATA GAP**.
- Results coverage is thin vs odds: ESPN CSVs 2022–2025 (~4.2k rows) exist; Sports-Reference CSVs **absent**; `actual_margins.parquet` only grades **406** events (many via SportsData trial path per methodology).
- **Identity is P0 risk:** `" st" → " state"` mangles `Ohio State` → `ohio stateate` (and Penn/Michigan/Ball State). Miami FL vs OH relies on fragile short-name norms (`miami` vs `miami (oh)`); product directory uses `miami` / `miami-oh` — no shared canonical IDs.
- Shadow systems: dual ratings builders, dual join/backtest paths, sample KEI writer, broken `real_backtest.py`, empty Haslametrics stubs, Torvik snapshots dir with **0** files, odds path docs drift (`historical-odds/ncaab` vs `raw/odds`).
- Product surfaces for Edge Board / KEI lines / power ratings / overview exist; overnight infra declares **ncaam/cbb fair-lines OUT** of warehouse (`docs/ODDS_DATA_INFRA.md`). `/pro/ncaam/fair-lines` copy says “not connected.”
- Props are already gated off (`supportsPropsFantasy: false`; `/pro/ncaam/props` → tempo). SportsData `--props` script exists — **OUT / RETIRE for v1**.
- Phase B must VERIFY identity joins, actual-margin coverage, whether KEI JSON freshness is acceptable, and which shadow paths to RETIRE before any rebuild.

---

## 2. Inventory table

| Artifact | Location | Role | Classification | Receipt | Notes |
| --- | --- | --- | --- | --- | --- |
| Sport SoT `ncaam` / label CBB | `apps/web/lib/sports.ts` L18–24 | Product namespace; props false | **KEEP** | `key: "ncaam"`, `supportsPropsFantasy: false` | Canonical |
| Odds map `ncaam→basketball_ncaab` | `apps/web/lib/odds-api.ts` | Live odds sport key | **KEEP** | `SPORT_KEY_MAP.ncaam` | |
| Pipeline entrypoint | `apps/web/run_pipeline.py` | Ratings→odds→join→merge | **KEEP** | `pnpm pipeline` → `@kosedge/pipeline` | |
| Path SoT | `apps/web/pipeline_paths.py` | Raw/processed paths | **KEEP** | | |
| Ensemble ratings builder | `apps/web/src/build_ensemble_ratings.py` | Primary ratings table | **KEEP** | → `full_ensemble_ratings.parquet` | |
| Legacy ratings builder | `apps/web/src/build_ratings.py` | Parallel ratings path | **VERIFY** | Still in `run_pipeline` | Shadow of ensemble |
| KenPom ingest | `apps/web/src/ingest_kenpom.py` | API → CSV 2016–2026 | **KEEP** | needs `KENPOM_API_KEY` | Feed ≠ SoT (CoS rule) |
| KenPom weekly snapshots | `apps/web/src/precompute_kenpom_snapshots.py` + `data/processed/kenpom_snapshots/` | As-of ratings (no lookahead) | **KEEP** | **198** parquet files on disk | |
| Torvik snapshot precompute | `apps/web/src/precompute_torvik_snapshots.py` | Weekly Torvik via `cbbdata` | **REBUILD** | `torvik_snapshots/` **0 files** | Weight currently 0 |
| Merge + ensemble spread | `apps/web/src/merge_games_ensemble.py` | Join odds+ratings+margins; edge | **KEEP** | formula + clip; uses weights JSON | Identity REBUILD needed |
| Process odds | `apps/web/src/process_odds.py` | Raw JSON → odds parquet | **KEEP** | | |
| Join+backtest (legacy) | `apps/web/src/join_and_backtest.py` | Parallel join → `games_with_edges.parquet` | **VERIFY** | Still in default pipeline | Candidate RETIRE after VERIFY |
| Weight estimator | `apps/web/src/estimate_ensemble_weights.py` | OLS → `ensemble_weights.json` | **KEEP** | train ≤2022, n=200 | Live = KenPom-only |
| Actual margins builder | `apps/web/src/build_actual_margins.py` | Results → margins parquet | **REBUILD** | only 406 matched | Prefer ESPN, not trial SportsData |
| ESPN results scrape | `apps/web/scrape_cbb_results_espn.py` + `data/raw/games/espn_cbb_games_2022..2025.csv` | Primary results | **KEEP** | ~4,189 lines total | |
| Sports-Reference scrape | `apps/web/scrape_cbb_results.py` | Alt results | **DATA GAP** | no `sportsref_cbb_games_*.csv` in repo | Script KEEP; data absent |
| Historical odds fetch | `apps/web/scripts/fetch_historical_ncaab_odds.py` | Odds API historical open/close | **KEEP** | earliest API 2020-11-16 | Credits: 40/day |
| Live KEI projector | `apps/web/scripts/project_future_kei_lines.py` | Live odds + ratings → KEI | **KEEP** | | |
| KEI export | `apps/web/scripts/export_kei_lines.py` | → `kei_lines_ncaam.json` | **KEEP** | | |
| KEI backtest | `apps/web/scripts/backtest_kei_results.py` | Canonical ATS/ROI logger | **KEEP** | writes `kei_backtest_results.json` | |
| Power ratings export | `apps/web/scripts/export_power_ratings.py` | → `power_ratings_ncaam.json` | **KEEP** | 365 teams | Freshness VERIFY |
| Sample KEI writer | `apps/web/scripts/populate-kei-lines-sample.js` | Fake/sample lines | **RETIRE** | `populate:kei-lines-sample` | Shadow of real export |
| Broken real backtest | `apps/web/src/real_backtest.py` | Deduped edge backtest | **RETIRE** | imports `MERGED_GAMES_PATH`, reads `MERGED_PATH` | Broken |
| Flat betting backtest | `apps/web/src/flat_betting_backtest.py` + `flat_betting_picks.csv` | Experiment filters | **VERIFY** | | Shadow of KEI backtest |
| Margin XGB trainer | `apps/web/src/train_margin_model.py` | Train margin model | **RETIRE** / **DATA GAP** | `margin_model.json` absent | |
| Haslametrics ingest + CSVs | `apps/web/src/ingest_haslametrics.py` + `data/raw/ratings/haslametrics_*` | Rating component | **RETIRE** (stubs) / **REBUILD** if wanted | identical MD5 empty stubs | Weight 0 |
| Barttorvik/Torvik CSVs | `data/raw/ratings/barttorvik_*.csv` | Torvik season files | **KEEP** + **DATA GAP** | **2022 missing** | |
| EvanMiya CSVs | `data/raw/ratings/evanmiya_team_ratings_*.csv` | BPR component | **VERIFY** | weight 0 live | |
| DRatings scrape/CSVs | `src/ingest_dratings.py`, scripts, `dratings_ratings_*.csv` | External ratings | **VERIFY** | not in live ensemble formula | |
| SportsData CBB pull | `apps/web/scripts/pull_sportsdata_cbb.py` | Results/today/**props** | **VERIFY**; props **OUT** | `pnpm pull:cbb` | Trial/scrambled caveat |
| Model-service NCAAM today | `services/model-service/src/routes/edge_board.py` | Live odds board upstream | **KEEP** | `SPORT_KEY_NCAAB`; `@router.get("/ncaam/today")` | No season engine |
| Model-service sport map | `services/model-service/src/tasks.py` | `basketball_ncaab`→`ncaam` | **KEEP** | | |
| CBB season engine | — | Production spine | **DATA GAP** | does not exist | |
| Edge Board `/edge-board/ncaam` | `apps/web/app/edge-board/[sport]/page.tsx` | Public decision board | **KEEP** | assemble + KEI file | Default bare `/edge-board` → ncaam VERIFY |
| Assemble API | `apps/web/app/api/edge-board/[sport]/assemble/route.ts` | Page-data | **KEEP** | | |
| Today API (web) | `apps/web/app/api/edge-board/ncaam/today/route.ts` | Proxy MS / Odds | **KEEP** | | |
| KEI Lines UI | `/pro/kei-lines/ncaam` + `NcaamKeiLinesClient.tsx` | Model baselines table | **KEEP** / **DATA GAP** freshness | 38 games; dates 2026-02-20..22 | Stale vs “today” |
| Fair-lines desk | `/pro/ncaam/fair-lines` | Fair lines shell | **VERIFY** | copy: “out of this overnight slice” | Warehouse OUT |
| Power ratings UI | `/pro/power-ratings/ncaam` | Strength table | **KEEP** / **VERIFY** freshness | 365 teams JSON | |
| Overview / slate / edges / odds | `/pro/ncaam/*`, `/odds/ncaam` | Desk chrome | **KEEP** | props filtered | |
| Tempo desk | `/pro/ncaam/tempo` | College tempo | **REBUILD** / **DATA GAP** | no tempo model feed | |
| Team research | directories + shells | Directory + research shells | **KEEP** shells / **DATA GAP** stats | `miami` + `miami-oh` | |
| Standings / Efficiency nav | `/pro/ncaam/standings`, `/stats` | Nav links | **RETIRE** from nav or REBUILD | NFL-only `notFound()` | Dead nav |
| Props page | `/pro/ncaam/props` | Redirect → tempo | **OUT (v1)** / **RETIRE** as product | `supportsPropsFantasy: false` | |
| Orphan `/pro/cbb`, `/pro/ncaab` | dynamic `[sport]` | Alias pollution | **RETIRE** or redirect → `ncaam` | Sport Standard inventory notes 200s | |
| Prisma sport comment `cbb` | `apps/web/prisma/schema.prisma` | Schema comment | **VERIFY** | live key is `ncaam` | Naming drift |
| Methodology doc | `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md` | Reproduce + math SoT | **KEEP** | run 2026-02-21 | |
| Odds infra docs | `docs/ODDS_DATA_INFRA.md` | Declares ncaam/cbb **out** | **KEEP** | | |
| Processed odds parquet | `ncaab_historical_odds_open_close.parquet` | Training/backtest odds | **KEEP** | committed + regenerable | |
| Merged games parquet | `merged_games_with_odds_and_ratings.parquet` | Join output | **KEEP** | 10,270 events (backtest) | |
| Actual margins parquet | `actual_margins.parquet` | Graded results | **REBUILD** | 406 rows | Coverage gap |
| Ensemble weights JSON | `ensemble_weights.json` | Live weights | **VERIFY** | KenPom-only | Re-estimate after identity fix |
| `kei_lines_ncaam.json` | processed | Product KEI feed | **KEEP** / **DATA GAP** freshness | 38 games @ 2026-02 | |
| `power_ratings_ncaam.json` | processed | Product power | **KEEP** / **VERIFY** | 365 teams | |
| `edge_board_fallback_ncaam.json` | processed | Skeleton fallback | **KEEP** | honesty: no invented books | |
| KenPom/Torvik archives | `kenpom_archive.parquet` / `torvik_archive.parquet` | As-of archives | **DATA GAP** | absent on disk | |
| Notebooks | — | Experiments | **DATA GAP** | none found | |
| Archived MS edge_board | `_archive/.../edge_board.py` | Old backup | **RETIRE** | | |

---

## 3. Grouped sections

### 3.1 Code / models

**Canonical spine (KEEP):**

1. `run_pipeline.py` / `@kosedge/pipeline` scripts  
2. `build_ensemble_ratings.py` → `full_ensemble_ratings.parquet`  
3. KenPom ingest + **198** weekly snapshots  
4. `process_odds.py` ← historical Odds API JSON  
5. `merge_games_ensemble.py` → `merged_games_with_odds_and_ratings.parquet`  
6. `backtest_kei_results.py` / `export_kei_lines.py` / `project_future_kei_lines.py`  
7. Model-service `GET /edge-board/ncaam/today` (odds only)

**Live model math (receipt):**  
`ensemble_weights.json` = `{adjem:1, torvik:0, barthag:0, bpr:0, haslam:0, home_court:2.8696, train_end_year:2022, n_train:200}`  
→ `ensemble_spread ≈ adjem_diff + 2.8696`, clipped ±28. Documented in `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`.

**Shadow / parallel (VERIFY → likely RETIRE):**

| Shadow | vs canonical |
| --- | --- |
| `build_ratings.py` + `join_and_backtest.py` → `games_with_edges.parquet` | vs ensemble + merge |
| `flat_betting_backtest.py` / `yesterday_ats.py` / broken `real_backtest.py` | vs `backtest_kei_results.py` |
| `populate-kei-lines-sample.js` | vs export/project scripts |
| Offline KEI JSON vs live Odds board | no unified season engine |

**Missing production spine:** no `cbb_season_engine` / Railway materialize path analogous to NFL/CFB. **DATA GAP**.

### 3.2 Data / APIs

| Layer | What exists | Classification |
| --- | --- | --- |
| KenPom CSV 2016–2026 | `data/raw/ratings/kenpom_ratings_2016-2026.csv` | **KEEP** (feed) |
| Barttorvik yearly | 2016–2021, 2023–2025; **no 2022** | **KEEP** + **DATA GAP** |
| EvanMiya / DRatings | yearly CSVs present | **VERIFY** (unused in live weights) |
| Haslametrics | empty comma stubs, identical MD5 across years | **RETIRE** stubs |
| ESPN games | 2022–2025 CSVs (~4.2k lines) | **KEEP** |
| Sports-Reference | scraper only; **0** CSVs | **DATA GAP** |
| Odds raw JSON | 488×2, 2022-11-01…2025-12-04 | **KEEP**; pre-2022 + dense 2024–25 **DATA GAP** |
| Odds parquet | committed processed | **KEEP** |
| SportsData trial parquets | `all_sportsdata_results_2016-2025.parquet`, etc. | **VERIFY** (scrambled trial) |
| Torvik snapshots | dir expected, **0** files | **DATA GAP** / **REBUILD** |
| Archives | kenpom/torvik archive parquets absent | **DATA GAP** |

**External feeds:**

| Source | Usage | Note |
| --- | --- | --- |
| KenPom API | ingest + snapshots | Core feed; **not** SoT per CoS lock |
| Barttorvik / Torvik (`cbbdata`) | CSVs + snapshot script | Snapshots missing; weight 0 |
| The Odds API | historical + live board | `basketball_ncaab` |
| ESPN scoreboard | results scrape | Primary real results |
| Sports-Reference | scraper | Broken/absent for 2022+ in repo |
| SportsData.io | trial pull + replay | Results/props PoC; **props OUT** |
| DRatings / Haslametrics / EvanMiya | scrapes/CSVs | Peripheral; not live-weighted |

**APIs (product/infra):**

| Endpoint | Status |
| --- | --- |
| `GET /api/edge-board/ncaam/assemble` | Live generic |
| `GET /api/edge-board/ncaam/today` | Live |
| `GET /api/odds/ncaam/compare` | Live |
| Model-service `/edge-board/ncaam/today` | Live odds |
| `/api/ncaam/fair-lines` warehouse | **OUT** per `ODDS_DATA_INFRA.md` |

### 3.3 Product surfaces

| URL | Role | Class |
| --- | --- | --- |
| `/edge-board/ncaam` | Public board (default bare `/edge-board` redirects here) | **KEEP** (default bias **VERIFY**) |
| `/pro/ncaam/overview` | Hub (props sections filtered) | **KEEP** |
| `/pro/ncaam/slate/today` | Daily slate | **KEEP** |
| `/pro/kei-lines/ncaam` | KEI table (file-backed) | **KEEP** / freshness **DATA GAP** |
| `/pro/ncaam/fair-lines` | Desk shell; pending copy | **VERIFY** |
| `/pro/ncaam/edges` | Board-derived edges | **KEEP** |
| `/pro/ncaam/tempo` | Tempo desk shell | **REBUILD** / **DATA GAP** |
| `/pro/ncaam/execution` | Execution monitor | **KEEP** |
| `/pro/ncaam/tracking` | CLV stub | **DATA GAP** |
| `/pro/ncaam/teams` (+ `[slug]`) | Directory + research shells | **KEEP** / shells **DATA GAP** |
| `/pro/power-ratings/ncaam` | Power table | **KEEP** / **VERIFY** |
| `/odds/ncaam` | Multi-book compare | **KEEP** |
| `/pro/ncaam/standings`, `/stats` | Nav → 404 | **RETIRE** nav or REBUILD |
| `/pro/ncaam/props` | Redirect → tempo | **OUT (v1)** |
| `/pro/cbb`, `/pro/ncaab` | Orphan aliases | **RETIRE** / redirect |
| Insights note `cbb-market-vs-power` | Desk content | **KEEP** |
| `/methodology` | Mentions CBB stack | **KEEP** |

Nav receipt: `apps/web/lib/sport-pro-nav.ts` lists Standings/Efficiency for ncaam while pages 404 for non-NFL.

### 3.4 Experiments

| Artifact | Class | Receipt |
| --- | --- | --- |
| `kei_backtest_results.json` (canonical) | **KEEP** | 406 / −1.97% ROI / 2026-02-21 |
| `walk_forward_backtest_results.json` | **VERIFY** | experiment |
| `flat_betting_picks.csv` + flat backtest | **VERIFY** | |
| `yesterday_ats.py` | **VERIFY** | ops helper |
| `real_backtest.py` | **RETIRE** | NameError path bug |
| `train_margin_model.py` | **RETIRE** until revived | no artifact |
| SportsData replay capture (`ncaab` league) | **VERIFY** | `capture_sportsdata_replay.py` |
| One-off `write_dratings_from_fetch.py` | **RETIRE** | hardcoded fetch dump |
| Notebooks | **DATA GAP** | none |

### 3.5 Identity / joins

**P0 — string normalize bug (REBUILD):**

```text
normalize: .replace(" st", " state")
"Ohio State" → "ohio stateate"
"Penn State" → "penn stateate"
"Michigan State" → "michigan stateate"
"Ball State" → "ball stateate"
"Ohio St" → "ohio state"   # happens to work
```

Receipt: `apps/web/src/merge_games_ensemble.py` L33–41; same pattern in `join_and_backtest.py`, `build_ensemble_ratings.py`, `build_schedule_from_odds.py`, `precompute_kenpom_snapshots.py`, `build_results_with_totals.py`.

**Miami FL vs OH (DATA GAP / risk):**

| Layer | FL | OH |
| --- | --- | --- |
| Product directory | slug `miami` (ACC) | slug `miami-oh` (MAC) | `directories-college.ts` |
| Odds short-name path | `Miami Hurricanes` → first token `miami` | `Miami (OH) RedHawks` → `miami (oh)` | `odds_team_to_short` |
| Canonical IDs | **none** shared across pipeline ↔ product | | |

Alias map covers unc/lsu/usc/ole miss/unlv/vcu/smu/tcu/wku/utsa/unm — **no miami dual entry**.

**Naming drift:** Prisma comment `"cbb"` vs product `ncaam` vs Odds `basketball_ncaab` vs SportsData slug `cbb`/`ncaab`.

### 3.6 Gaps

| Gap | Severity | Notes |
| --- | --- | --- |
| Team identity (State* mangling + Miami) | **P0** | Blocks trustworthy joins / backtests |
| Graded results only 406 / 10k odds events | **P0** | Backtest sample too thin / skewed |
| Torvik snapshots missing | High | Ensemble cannot use Torvik as-of |
| Odds pre-2022-11 not in repo | High | API allows from 2020-11-16 |
| Dense 2024–25 odds pocket thin | High | Jump after 2024-01 to 2025-11 |
| barttorvik_2022.csv missing | Med | |
| sportsref CSVs absent | Med | |
| No model-service CBB season engine | High for production spine | |
| No `/api/ncaam/fair-lines` warehouse | Intentional OUT for now | |
| KEI/power JSON freshness (Feb 2026 slice) | Med | Product may show stale slate |
| Tempo / tracking / team research feeds | Med | shells only |
| Haslametrics empty | Low (weight 0) | RETIRE stubs |
| No CBB notebooks / enterprise gates file | Low | |

---

## 4. Explicit OUT list (v1)

Do **not** promote for CBB v1:

1. **Player props product** — `supportsPropsFantasy: false`; `/pro/ncaam/props` redirects to tempo; overview omits props walls.  
2. **SportsData `--props`** pulls (`pull_sportsdata_cbb.py --props`) — trial PoC only.  
3. **Props-center / fantasy college cards** — college excluded from launch cards.  
4. **Conf% / PLAY stake tags** — out until #3 + governance (Notion lock).  
5. **Shadow “sample” KEI** — `populate-kei-lines-sample.js`.  
6. **Broken / experimental backtests as truth** — `real_backtest.py`, flat/walk-forward as SoT.  
7. **Haslametrics stub CSVs** as real ratings.  
8. **SportsData trial scrambled results** as production actuals.  
9. **KenPom as SoT** — feed only; CoS lock: KenPom feeds ≠ SoT.  
10. **Copying NFL methodology wholesale** — out of scope per KOS-28.  
11. **Orphan routes `/pro/cbb` / `/pro/ncaab`** as supported surfaces.  
12. **Dead nav targets** standings/stats/injuries/rosters/depth for CBB until rebuilt with real feeds.

---

## 5. Recommended Phase B handoff (what VERIFY must answer)

Phase B is **verification / disposition**, not rebuild. VERIFY must produce yes/no (+ receipts) for:

1. **Identity contract**  
   - Confirm `ohio stateate` (and peers) join-miss rate on merged parquet.  
   - Confirm Miami FL vs OH collision/miss rate on odds↔ratings↔ESPN.  
   - Decide: one canonical ID table (REBUILD) before any weight re-estimate.

2. **Which join path is SoT**  
   - Keep `merge_games_ensemble` only? RETIRE `join_and_backtest` + `full_ratings` from default pipeline?

3. **Actual-margin rebuild scope**  
   - Can ESPN 2022–2025 CSVs alone raise graded n ≫ 406 after identity fix?  
   - Drop SportsData trial from production actuals?

4. **Odds completeness plan**  
   - Pull 2020-11-16→2022-10 and dense 2024–25? Credit budget vs `HISTORICAL_ODDS_CREDITS_ESTIMATE.md` / ncaab README.

5. **Ensemble honesty**  
   - With Torvik weight 0 and snapshots empty: is “ensemble” marketing honest, or rename to KenPom baseline until Torvik as-of exists?

6. **Product truth**  
   - Is `/pro/ncaam/fair-lines` “not connected” compatible with live `/pro/kei-lines/ncaam` + Edge Board KEI file? Pick one customer-facing fair-line SoT for v1 (spread/total/ML).  
   - Accept or refresh stale `kei_lines_ncaam.json` (38 games, 2026-02-20..22).

7. **RETIRE batch**  
   - Sample KEI JS, broken `real_backtest`, Haslametrics stubs, orphan cbb/ncaab routes, dead nav items — approve deletion/quarantine list.

8. **OUT confirmation**  
   - Props remain OUT; no SportsData props promotion; no PLAY/Conf%.

9. **Production spine decision (docs only in B)**  
   - Stay file-backed web pipeline, or plan model-service materialize like other sports? (Implementation = later phase.)

**Phase B exit:** disposition matrix signed (KEEP/VERIFY→KEEP|REBUILD|RETIRE) + identity P0 ticket unlocked for Phase C rebuild — still no props, no UI chrome expansion beyond honesty fixes if separately authorized.

---

## Receipts appendix (commands / probes)

```text
# Branch base
git rev-parse --abbrev-ref HEAD  # cursor/cbb-phase-a-inventory-ef25

# Odds coverage
ls apps/web/data/raw/odds/open | wc -l   # 488
# months: 2022-11 … 2024-01 continuous; 2025-11, 2025-12 pocket

# Snapshots
ls apps/web/data/processed/kenpom_snapshots | wc -l  # 198
ls apps/web/data/processed/torvik_snapshots | wc -l  # 0

# Backtest
python3 -c "import json;print(json.load(open('apps/web/data/processed/kei_backtest_results.json')))"
# 406 games, -1.97% ROI, run_date 2026-02-21

# Weights
cat apps/web/data/processed/ensemble_weights.json
# adjem 1.0; others 0

# Identity bug
python3 -c "print('Ohio State'.lower().replace(' st',' state'))"  # ohio stateate

# Props gate
# apps/web/lib/sports.ts supportsPropsFantasy: false
# apps/web/app/(pro)/pro/[sport]/props/page.tsx redirect ncaam→tempo
```

**Related ops/docs (context, not reclassified as CBB engine):**  
`data/ops/edge-board-population-status-2026-08-02.md` (NCAAM KEI fallback) · `data/ops/multi-sport-ui-overhaul-report.md` · `docs/SPORT_STANDARD_EVIDENCE_INVENTORY.md` · `docs/SPORTSDATA_REPLAY_CAPTURE.md` · `docs/HISTORICAL_ODDS_CREDITS_ESTIMATE.md` · `docs/MARKET_ODDS_INFRASTRUCTURE_AUDIT_v1.md`.

---

*End Phase A inventory. No product/UI/model code changed in this packet.*
