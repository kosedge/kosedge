# CBB / NCAAM Phase A Inventory (evidence only)

**Date:** 2026-09-04  
**Issue:** Linear [KOS-28](https://linear.app/kosedge/issue/KOS-28/14-phase-a-cbb-inventory-keepverifyrebuildretiredata-gap) · Notion [#14 CBB Production Model (LOCKED)](https://app.notion.com/p/3d1568a6d5df81ddb87bf0e2b7a093b6)  
**Branch base:** `deploy-vercel` @ `6e2fcdf9`  
**Scope:** Evidence-only inventory. **No** UI work, **no** new model code, **no** rebuild. Labels below are **suggested** for CoS; final KEEP/VERIFY/REBUILD/RETIRE/DATA GAP is CoS.  
**Locks honored:** Props out of v1 · KenPom = feed candidate, not SoT · CBB enters mature KosEdge (no parallel architecture invented here) · Identity mismatches called out.

---

## Executive summary

KosEdge already has a **legacy CBB (NCAAM) research pipeline** under `apps/web` (Python scrape/ingest → ensemble ratings → odds join → KEI lines/backtest) plus **product shells** that treat `ncaam` as a first-class sport key (Edge Board default, Pro hub, power ratings, KEI lines). There is **no** Railway model-service CBB season/possession engine comparable to NFL/CFB/NBA — model-service CBB surface is **odds-only** (`GET /edge-board/ncaam/today`).

**Suggested posture (for CoS review):**

| Bucket | Headline |
|--------|----------|
| **KEEP** | Sport key + Odds API plumbing (`basketball_ncaab` ↔ `ncaam`); product route shells; book-ledger sport membership; methodology doc as historical receipt |
| **VERIFY** | Ensemble/KEI pipeline math & weights; KenPom/Torvik/Evan raw feeds; historical odds parquet vs raw JSON; live Edge Board/KEI JSON freshness |
| **REBUILD** | Team identity / alias layer (Miami FL vs OH proven broken); production spine that inherits house validation contracts (not a second website) |
| **RETIRE** | Haslametrics year-CSVs that are byte-identical placeholders; one-off `write_dratings_from_fetch.py`; archived duplicate edge_board; sample KEI populator if superseded |
| **DATA GAP** | Transfer/roster discontinuity feeds; pre-2020-11 Odds history; Sports-Reference game CSVs; Torvik snapshots; SportsData raw pull dir; enterprise training mainlines (`ncaam` = 0); margin model artifact; CBB enterprise gates |

**Backtest receipt (stale):** `kei_backtest_results.json` run_date **2026-02-21** — 406 graded games, **49.01%** ATS flat bet, **−1.97%** ROI. Live weights file is **KenPom-only** (`adjem=1`, others `0`). That is evidence of a **feed-weighted prototype**, not a house SoT engine.

---

## Inventory table

| Artifact | Location | Type | Last evidence | Suggested label | Why | Risks |
|----------|----------|------|---------------|-----------------|-----|-------|
| NCAAB Python pipeline entry | `apps/web/run_pipeline.py` | Code | git `2026-02` (pipeline scripts); still wired via `@kosedge/pipeline` | VERIFY | Single entry for ratings→odds→merge; env checks `ODDS_API_KEY` / `KENPOM_API_KEY` | Stale vs house engines; may encourage shadow rebuild |
| Pipeline path constants | `apps/web/pipeline_paths.py` | Code | present on `deploy-vercel` | KEEP | Canonical paths for raw/processed CBB data | Drift if new spine ignores it |
| KenPom ingest | `apps/web/src/ingest_kenpom.py` | Code / feed | git `54320fc2` 2026-02-19 | VERIFY | Fetches `kenpom.com/api.php` with `KENPOM_API_KEY` → CSV | **Feed ≠ SoT**; key/env ops |
| KenPom weekly snapshots | `apps/web/src/precompute_kenpom_snapshots.py` + `data/processed/kenpom_snapshots/` (198 files) | Code / data | snapshots on disk; script 2026-02-19 | VERIFY | As-of ratings for no-lookahead join | Coverage/freshness unknown for 2025–26 |
| KenPom archive fetch | `apps/web/src/fetch_ratings_archive.py` | Code | 2026-02-19; **`kenpom_archive.parquet` MISSING** | DATA GAP / VERIFY | Script exists; artifact absent | Lookahead risk if seasonal CSV used instead |
| Torvik snapshot precompute | `apps/web/src/precompute_torvik_snapshots.py` | Code | 2026-02-19; **`torvik_snapshots/` MISSING** | DATA GAP | Code present; no snapshot dir | Merge falls back; weights already zero Torvik |
| Ensemble ratings builder | `apps/web/src/build_ensemble_ratings.py` | Model code | git `26e3ea48` 2026-02-22 | VERIFY | Builds `full_ensemble_ratings.parquet` from KenPom+Torvik+Evan(+Haslam) | Identity normalize shared with merge |
| Ratings builder (simpler) | `apps/web/src/build_ratings.py` | Model code | 2026-02-19 | VERIFY / RETIRE? | Older `full_ratings.parquet` path; overlaps ensemble | Dual rating artifacts |
| Merge + edge | `apps/web/src/merge_games_ensemble.py` | Model code | 2026-02-22 | VERIFY → REBUILD (identity) | Core join odds↔ratings; spread formula | **Miami identity broken** (see §Identity) |
| Join/backtest (legacy) | `apps/web/src/join_and_backtest.py` | Model code | 2026-02-19 | VERIFY / RETIRE? | Parallel to merge path | Duplication |
| Weight estimation | `apps/web/src/estimate_ensemble_weights.py` + `ensemble_weights.json` | Model | weights train_end_year **2022**, n_train **200** | VERIFY | Live model is KenPom-only + HCA 2.8696 | Overfits narrative of “ensemble” |
| Margin model train | `apps/web/src/train_margin_model.py` | Model code | 2026-02-19; **`margin_model.json` MISSING** | DATA GAP / RETIRE | Script without artifact | Dead training path |
| Flat / real backtests | `flat_betting_backtest.py`, `real_backtest.py`, `yesterday_ats.py` | Experiments | 2026-02-19 | VERIFY | Lab scripts | Not house scorecard |
| Actual margins | `build_actual_margins.py` + `actual_margins.parquet` | Data pipeline | 2026-02-22 | VERIFY | Grades need results↔odds match | Sparse vs odds (406 / 10k events) |
| ESPN results scrape | `scrape_cbb_results_espn.py` + `espn_cbb_games_2022..2025.csv` | Data | CSVs on disk (1104/1173/930/978 rows) | KEEP / VERIFY | Present results feed | Incomplete seasons; no 2021/2026 file |
| Sports-Reference scrape | `scrape_cbb_results.py` | Code | script present; **no `sportsref_cbb_games_*.csv`** | DATA GAP | Documented target missing | Alternate results SoT unused |
| D-Ratings ingest | `ingest_dratings.py`, `scrape_dratings.py`, `ingest_dratings_historical.py`, CSVs 2020–2026 | Feed | CSVs present; 2026 file tiny (1327 B) | VERIFY | External rating feed | Scrape fragility; partial 2026 |
| One-off D-Ratings writer | `scripts/write_dratings_from_fetch.py` | Dead code | hardcoded HTML table | RETIRE | Stdlib fallback dump | Stale snapshot |
| Haslametrics ingest + CSVs | `ingest_haslametrics.py` + 44 CSVs | Feed | **defense_2016..2026 all MD5-identical** | RETIRE (files) / DATA GAP (real feed) | Placeholder duplication | Pollutes ensemble if weights non-zero |
| EvanMiya ratings CSVs | `evanmiya_team_ratings_2016..2026.csv` | Feed | on disk | VERIFY | BPR component | License/refresh unknown |
| BartTorvik CSVs | `barttorvik_2016..2021,2023..2025.csv` | Feed | **2022 missing**; no 2026 | DATA GAP / VERIFY | Gap year + current season | Incomplete Torvik history |
| KenPom multi-year CSV | `kenpom_ratings_2016-2026.csv` (3928 rows, seasons 2016–2026) | Feed | git 2026-02-19 | VERIFY | Primary adjem source today | Names `Miami FL`/`Miami OH` vs odds shorts |
| SportsData.io CBB pull | `scripts/pull_sportsdata_cbb.py` (`SPORTSDATA_CBB_SLUG`, default `cbb`) | API client | 2026-02-22; **`data/raw/sportsdata_cbb/` empty** | VERIFY / DATA GAP | Client + docs; raw dir absent | Props endpoints exist — **out of v1** |
| SportsData processed | `all_sportsdata_results_2016-2025.parquet`, `sportsdata_games_2025.parquet` | Data | on disk (same size) | VERIFY | Possibly collapsed/dupe artifacts | Integrity check needed |
| Historical odds fetch | `scripts/fetch_historical_ncaab_odds.py` | API | README: Odds API from **2020-11-16** only | KEEP (capability) | Documented credit cost | Pre-2020 **DATA GAP** |
| Raw odds JSON | `apps/web/data/raw/odds/{open,close}/` **488+488** files, **2022-11-01 → 2025-12-04** | Market history | on disk | KEEP / VERIFY | Substantial open/close lake | Path differs from README `historical-odds/ncaab/` |
| Historical-odds README dir | `apps/web/data/historical-odds/ncaab/README.md` only | Docs | no open/close JSON there | VERIFY | Docs/path drift | Confusion on SoT path |
| Processed odds parquet | `ncaab_historical_odds_open_close.parquet` | Market history | git 2026-02-22 | VERIFY | Merge input | Refresh vs raw JSON |
| Merged training table | `merged_games_with_odds_and_ratings.parquet` | Data | cited in backtest (10,270 events) | VERIFY | Core research table | Identity join quality |
| KEI projection script | `scripts/project_future_kei_lines.py` | Model → product | 2026-02-22 | VERIFY | Odds upcoming + ratings → `kei_lines_ncaam.json` | Same Miami alias bug |
| KEI lines export / sample | `export_kei_lines.py`, `populate-kei-lines-sample.js` | Product data | sample JS exists | VERIFY / RETIRE (sample) | Sample can invent structure | Honesty risk if used live |
| Power ratings export | `export_power_ratings.py` → `power_ratings_ncaam.json` (**365** teams) | Product data | multi-sport report 2026-07-31 | KEEP / VERIFY | Live Pro power surface | Feed-derived ranks |
| KEI lines JSON | `kei_lines_ncaam.json` (**38** games) | Product data | git content `ba3eeb19` 2026-02-21 | VERIFY | Pro KEI Lines + Edge Board KEI | Stale offseason slate likely |
| Edge Board fallback | `edge_board_fallback_ncaam.json` | Product data | cited 2026-08-02 ops | KEEP | Honest skeleton; no invented books | Must stay non-inventive |
| Backtest results JSON | `kei_backtest_results.json` | Experiment receipt | run_date **2026-02-21** | KEEP (receipt) | Documents −1.97% ROI / 406 games | Not a launch gate |
| Methodology doc | `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md` | Docs | git 2026-02-22 | KEEP | Repro notes; admits KenPom-only weights | Do not treat as Contract v1 |
| Web API Edge Board | `apps/web/app/api/edge-board/ncaam/today/route.ts` | API | git `5ed39619` 2026-07-24 | KEEP | Proxies model-service then Odds API | Cache/TTL ops |
| Model-service Edge Board | `services/model-service/src/routes/edge_board.py` `GET /ncaam/today` | API | touched 2026-09-03 (file); NCAAM = odds reshape | KEEP | Markets-only; no KEI engine | Not a production model |
| Odds sport map | `apps/web/lib/odds-api.ts` `ncaam → basketball_ncaab` | Config | present | KEEP | Shared house odds client | Breaks if key renamed carelessly |
| Model-service sport map | `tasks.py` `basketball_ncaab → ncaam` | Config | present | KEEP | Persistence mapping | — |
| Enterprise odds pull plan | `scripts/odds/enterprise_training_pull.py` ncaam plan | Market infra | checkpoint lists ncaam completed; **inventory mainline_games: 0** | DATA GAP / VERIFY | Sport planned; no rows stored | False “complete” |
| Persist mainlines | `scripts/odds/persist_mainline_odds.py` includes ncaab | Market infra | present | KEEP | Shared ledger writer | Needs non-zero pulls |
| Book snapshot stub | `scripts/ncaam/book_snapshot.py` | Ops stub | git `b792f784` 2026-08-29; exits 2 | VERIFY | Schema-ready; join not implemented | Don’t confuse with live Book |
| Book ledger sports set | `book_ledger/schema.py` includes `ncaam` | Schema | present | KEEP | Multi-sport ledger membership | — |
| Prisma Sport key comment | `apps/web/prisma/schema.prisma` key `"cbb"` | Schema drift | comment vs product `ncaam` | VERIFY / REBUILD | **Namespace mismatch** (`cbb` vs `ncaam`) | Identity / DB pollution |
| Infra SQL sports | `infra/db/001_init.sql` code `'ncaam'` | Schema | present | KEEP | Aligns with product key | Prisma comment stale |
| Pro sport IA / desk / nav | `lib/sports.ts`, `sport-pro-nav.ts`, `pro-sport-ia.ts`, `pro-sport-desk.ts`, `sport-overview.ts` | Product | active | KEEP | Mature shell; props disabled | Don’t invent parallel hub |
| Team research directory | `directories-college.ts` `NCAAM_TEAM_DIRECTORY` | Product | Miami ACC only; **no miami-oh in NCAAM list** (CFB has miami-oh) | REBUILD (identity) | Incomplete D1 + FL/OH gap | Wrong team pages |
| KEI Lines page | `pro/kei-lines/[sport]/` + `NcaamKeiLinesClient.tsx` | Product | 2026-09-03 touch (NFL redirect); NCAAM special-cased | KEEP / VERIFY | Working surface on JSON | Stale lines |
| Fair Lines honesty | `pro/[sport]/fair-lines/page.tsx` — CBB “not connected” overnight slice | Product | present | KEEP | Honest empty | Don’t invent prices |
| Props route | `pro/[sport]/props` — ncaam redirects (college no props desk) | Product | `supportsPropsFantasy: false` | KEEP (out of v1) | Matches #14 props-out | Do not ungate |
| Edge Board default | `/edge-board` → `/edge-board/ncaam` | Product | documented in CFB audits | KEEP | Product default sport | CFB deep-link discipline |
| Tempo page | `pro/[sport]/tempo` for college | Product shell | present | KEEP | Shell only | No CBB tempo model found |
| Insights desk note | `insights/content/desk-notes.ts` `cbb-market-vs-power` | Content | present | VERIFY | Editorial surface | Claims audit (#10) |
| Pipeline package scripts | `services/pipeline/package.json` `pull:cbb`, `backtest:kei`, … | Tooling | present | KEEP | Monorepo entrypoints | — |
| Root pnpm aliases | `package.json` `pull:cbb`, `backtest:kei`, `export:kei-lines` | Tooling | present | KEEP | Operator convenience | — |
| Pipeline tests | `apps/web/tests_pipeline/` + kenpom fixture | Tests | present | KEEP / VERIFY | Minimal coverage | Not enterprise gates |
| Python allowlist | `policies/web-python-allowlist.txt` lists CBB scripts | Policy | present | KEEP | CI allowlist for web Python | — |
| Archived edge_board | `_archive/apps_api_backup/.../edge_board.py` | Dead | archive | RETIRE | Duplicate of live route | Confusion |
| CBB enterprise gates doc | `docs/CBB_ENTERPRISE_GATES.md` | Docs | **NOT FOUND** (noted in CFB Week0 audit) | DATA GAP | No house gate file | Gate debt for Phase B+ |
| Transfer / roster discontinuity | searched `transfer`/`roster` under CBB paths | Data | **only CFB portal artifacts** | DATA GAP | Required by #14 v1 philosophy | Early-season risk |
| Optimizer / possession CBB engine | model-service | Model | **none** (NBA/WNBA/NFL only) | DATA GAP | No production spine | Don’t copy NBA possession blindly |
| Notebooks | `notebooks/**/*cbb*` | Experiments | **none** | DATA GAP | No notebooks tree for CBB | — |
| `models/` package | repo root | — | **absent** | — | N/A | — |

---

## 1. Code

### 1.1 Primary research pipeline (`apps/web`)

Documented run order in `apps/web/data/README.md` and `run_pipeline.py`:

1. Ratings: `build_ratings.py` / `build_ensemble_ratings.py` (+ KenPom/Torvik/Evan/Haslam/D-Ratings ingests)
2. Odds: `fetch_historical_ncaab_odds.py` → `process_odds.py`
3. Join: `join_and_backtest.py`, `merge_games_ensemble.py`
4. Results: ESPN / Sports-Ref scrapes → `build_actual_margins.py`
5. Optional: `train_margin_model.py`, backtest scripts, `project_future_kei_lines.py`, exports

**Evidence:** scripts + `policies/web-python-allowlist.txt` entries; `@kosedge/pipeline` npm scripts wrap the same Python.

### 1.2 Model-service

- **Present:** odds Edge Board for NCAAM; sport maps; book ledger sport token; Celery odds persistence map.
- **Absent:** `ncaam_*` / `cbb_*` season engine, possession simulator, fair-lines API, props projection (correct for props-out; still a **spine DATA GAP** for production modeling).

### 1.3 Shared web libs (product wiring)

`odds-api.ts`, `build-edge-board-rows.ts`, `resolve-kei-lines.ts`, `edge-board-kei-availability.ts`, `power-ratings.ts`, sport IA modules — NCAAM is wired like other sports, with college props suppressed.

---

## 2. Models

| Piece | Evidence | Suggested |
|-------|----------|-----------|
| “Ensemble” spread | Formula in `merge_games_ensemble.py` / `project_future_kei_lines.py`; defaults adjem 0.40… **overridden** by `ensemble_weights.json` to adjem=1 | VERIFY — currently KenPom + HCA |
| Home court | `home_court: 2.8696` in weights (train ≤2022) | VERIFY |
| Backtest | `kei_backtest_results.json` + methodology doc | KEEP as receipt; not launch-ready |
| Margin ML | `train_margin_model.py` without output JSON | DATA GAP / RETIRE path |
| Production house spine | No model-service CBB engine | DATA GAP → future REBUILD under mature contracts |

**KenPom role (locked):** ingest + snapshots are **feed candidates**. Current live weights make KenPom *de facto* the only active rating term — that is a Phase A finding, not an endorsement of KenPom-as-SoT.

---

## 3. Data / seasons

| Dataset | Seasons / span | Notes |
|---------|----------------|-------|
| KenPom CSV | 2016–2026 | 3928 rows; teams include `Miami FL` / `Miami OH` |
| KenPom snapshots | 198 parquet files under `processed/kenpom_snapshots/` | As-of archive for merge |
| BartTorvik | 2016–2021, 2023–2025 | **2022 gap**; no 2026 file |
| EvanMiya | 2016–2026 | Present |
| D-Ratings | 2020–2026 | 2026 file very small |
| Haslametrics | 2016–2026 files | **Byte-identical defense CSVs across years** → treat as bad data |
| ESPN games | 2022–2025 | Row counts ~930–1173 / season |
| Sports-Ref games | — | Script only |
| SportsData results parquet | labeled 2016–2025 | Raw pull dir empty; verify provenance |
| Rest/travel | `rest_travel.parquet` | Built from odds-derived schedule |

---

## 4. Market history

| Source | Span | Evidence |
|--------|------|----------|
| The Odds API historical NCAAB | API floor **2020-11-16** (README) | Pre-2020 = **DATA GAP** |
| Raw open/close JSON in repo | **2022-11-01 → 2025-12-04** (488 days × open/close) | Under `data/raw/odds/`, not `historical-odds/ncaab/` |
| Processed open/close parquet | Used by merge; backtest odds range **2022-04-05 → 2025-12-06** | VERIFY alignment with raw |
| Enterprise training pull | Sport marked completed; **`mainline_games: 0`** | DATA GAP disguised as complete |
| Book snapshot | Stub only for ncaam | VERIFY later |

---

## 5. APIs & env

| Env / API | Role | Evidence |
|-----------|------|----------|
| `KENPOM_API_KEY` | KenPom fetch / snapshots | `run_pipeline.py --check-env`, `ingest_kenpom.py`, `fetch_ratings_archive.py`; optional `KENPOM_BASE_URL` |
| `ODDS_API_KEY` (+ backup) | Historical + live NCAAB | `env.ts`, fetch scripts, edge-board routes |
| `SPORTSDATA_CBB_SLUG` | Default `cbb`, fallback `ncaab` | `pull_sportsdata_cbb.py`, `docs/SPORTSDATA_REPLAY_CAPTURE.md` |
| `MODEL_SERVICE_URL` + `INTERNAL_API_SECRET` | Proxy `/edge-board/ncaam/today` | Web API route |
| Odds API sport key | `basketball_ncaab` | Shared maps |

No committed KenPom secrets found in scanned source (env-driven).

---

## 6. Experiments

- `kei_backtest_results.json` / methodology doc (2026-02-21) — flat bet all games with margins.
- `flat_betting_picks.csv`, `walk_forward_backtest_results.json`, `games_with_edges.parquet`.
- Pipeline unit tests: `tests_pipeline/test_build_ratings.py` (KenPom mini fixture), `test_schema.py`.
- No CBB notebooks found.
- Lab NFL scorecards explicitly **exclude CBB** (`docs/lab/NFL_SPREAD_*`).

---

## 7. Product surfaces

| Surface | Path / behavior | Suggested |
|---------|-----------------|-----------|
| Edge Board (default) | `/edge-board` → `/edge-board/ncaam` | KEEP |
| Edge Board sport | `/edge-board/ncaam` + assemble/fallback | KEEP / VERIFY KEI freshness |
| API | `/api/edge-board/ncaam/today` | KEEP |
| Pro overview / slate / matchups / tempo / teams | `/pro/ncaam/...` via `[sport]` | KEEP shells |
| Fair Lines | Honest “not connected” for overnight CBB slice | KEEP |
| KEI Lines | `/pro/kei-lines/ncaam` + client | VERIFY data |
| Power Ratings | `/pro/power-ratings/ncaam` ← JSON | VERIFY |
| Props | Redirect / pending; `supportsPropsFantasy: false` | KEEP out of v1 |
| Odds | `/odds/ncaam` desk link | KEEP |
| Adjacent aliases | `/pro/cbb`, `/pro/ncaab` cited as 200 in sport-standard inventory | VERIFY alias routing |
| Brand | KEI code `KEICMB` | KEEP |

---

## 8. Dead / duplicated / drift

1. **Haslametrics year files identical** — RETIRE as data; re-pull if needed.  
2. **`write_dratings_from_fetch.py`** — one-off RETIRE candidate.  
3. **`_archive/.../edge_board.py`** — RETIRE/ignore.  
4. **Dual odds paths** — README points at `historical-odds/ncaab/`; lake lives in `raw/odds/`.  
5. **`build_ratings` vs `build_ensemble_ratings`** — overlapping outputs.  
6. **Prisma comment `cbb` vs product/infra `ncaam`** — namespace drift.  
7. **`populate-kei-lines-sample.js`** — sample generator; risk if mistaken for production.  
8. **SportsData processed files same byte size** — possible duplicate/collapse; VERIFY.  
9. **Enterprise pull “ncaam completed” with 0 mainlines** — process debt.

---

## Identity (P0 callout) — Miami FL vs OH

**Receipts:**

- KenPom raw names: `Miami FL`, `Miami OH` → after pipeline normalize → `miami fl`, `miami oh` (see `power_ratings_ncaam.json` ranks 37 / 84 for 2026).
- Odds event names (sample close JSON 2024-01): `Miami Hurricanes`, `Miami (OH) RedHawks`.
- `odds_team_to_short` / `ODDS_TO_RATINGS_ALIASES` (**no miami entries**):
  - `Miami Hurricanes` → `miami` (**≠** `miami fl`)
  - `Miami (OH) RedHawks` → `miami (oh)` (**≠** `miami oh`)
  - `Miami RedHawks` → `miami` (collides with FL short form)
- Product directory: NCAAM list has `miami` (ACC) only; `miami-oh` exists on **CFB** list, not NCAAM.

**Suggested label:** REBUILD identity/alias layer before trusting any join, board, or backtest that matches on `team_norm`. This matches #14 CoS rule “Identity P0.”

Other fuzzy alias surface: small map (`unc`, `lsu`, `usc`, …) — VERIFY completeness for D1.

---

## What was NOT found (DATA GAP candidates)

1. Production CBB model-service engine (season / tempo-possession / fair-lines API).  
2. `docs/CBB_ENTERPRISE_GATES.md` / CBB scorecard v1.  
3. Transfer portal / roster discontinuity datasets for CBB.  
4. Sports-Reference game CSVs (script only).  
5. Torvik snapshot directory; KenPom archive parquet.  
6. `margin_model.json`.  
7. BartTorvik 2022 (+ current-season Torvik file).  
8. Odds history before 2020-11-16 (vendor limit).  
9. `data/raw/sportsdata_cbb/` populated raw pulls.  
10. Enterprise warehouse mainline rows for ncaam (`mainline_games: 0`).  
11. CBB-specific notebooks / `models/` package.  
12. Live Book join for ncaam (stub only).  
13. Workspace file `ke14-cbb-LOCKED-2026-09-04.md` (cited by Linear/Notion; **not present in this checkout** — mandate recovered from Notion page text).

---

## Suggested KEEP vs RETIRE vs DATA GAP (rollup for PR body)

**KEEP (infrastructure & shells):** `ncaam` sport key + Odds maps; Edge Board API/proxy; Pro shells with props gated off; power/KEI JSON *as product contracts to re-feed*; book ledger membership; methodology + backtest JSONs as historical receipts; pipeline path module.

**RETIRE (or quarantine):** identical Haslametrics year dumps; D-Ratings one-off writer; archived edge_board copy; sample KEI populator if not needed; treat “ensemble” marketing as misleading while weights are KenPom-only.

**DATA GAP (block honest production claims):** identity-safe team SoT; roster/transfer feeds; model-service spine; enterprise mainline history; Torvik snapshots / archive parquet; Sports-Ref results; CBB enterprise gates; pre-2020 markets (accept vendor floor).

**VERIFY next (not rebuild yet):** freshness of `kei_lines_ncaam.json` / snapshots; SportsData parquet integrity; raw odds ↔ parquet continuity; whether seasonal KenPom CSV joins leak future info when snapshots incomplete.

---

## Method (how this inventory was built)

- Repo-wide `rg` for `cbb|ncaam|kenpom|torvik|basketball_ncaab|college basketball` across `apps/`, `services/`, `scripts/`, `docs/`, `data/`.  
- Glob of path names `*cbb*|*ncaam*|*kenpom*`.  
- File presence/size/row counts; MD5 on Haslametrics; JSON parses of KEI/power/backtest/enterprise summary.  
- Git `log -1` stamps on key paths.  
- Simulated `odds_team_to_short` vs KenPom norms for Miami.  
- Linear KOS-28 + Notion #14 LOCKED page (2026-09-04).  

**Non-goals honored:** no code changes beyond this document; no UI; no model rebuild; props left out of v1 recommendations.
