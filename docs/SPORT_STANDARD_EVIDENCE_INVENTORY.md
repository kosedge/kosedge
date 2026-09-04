# KosEdge Sport Standard — Evidence Inventory

**Status:** inventory only (spec-first). No product grammar. No redesign.  
**As of:** 2026-09-04  
**Base:** `deploy-vercel` + public `www.kosedge.com` (read-only)  
**Machine-readable twin:** [`data/ops/sport-standard-evidence-inventory.json`](../data/ops/sport-standard-evidence-inventory.json)

CoS use: turn this into a gap matrix. Field values are `present` | `partial` | `absent`.

Allowed tag standard for inventory marking: **PLAY / LEAN / PASS** + **Best Value** where already exists. Do **not** introduce Best Bet / Stay Away (flag only if already in code).

---

## Shared contracts (evidence)

| Symbol | File |
|--------|------|
| `Tag = PLAY \| LEAN \| PASS` | `apps/web/lib/flat-rows-to-legacy.ts` |
| `ActionLabel` (NFL) = PASS/LEAN/PLAY/**BEST VALUE**/ALERT/**STAY AWAY** | `apps/web/lib/nfl-decision-engine.ts` |
| Edge Board UI | `apps/web/components/EdgeBoard.tsx` |
| Assemble API | `GET /api/edge-board/[sport]/assemble` |
| Odds compare | `GET /api/odds/[sport]/compare` · `OddsCompareBoard.tsx` |
| Nav SoT | `apps/web/lib/sport-pro-nav.ts` |
| Sport registry | `apps/web/lib/sports.ts` (`nfl\|cfb\|mlb\|nba\|nhl\|wnba` + ncaam) |

**www spot-check (2026-09-04):** `/edge-board/{sport}` and `/odds/{sport}` → **200** for all six sports.

**`run_id`:** absent on all major betting boards (edge / fair-lines / props / edges / odds). Present elsewhere (power-ratings / season-engine) — out of board scope.

**ODDS_API_KEY:** not shown in customer board UI (env/lib only). Ops-ish copy that **is** still visible: `Model service is not configured for this environment.` (`model-service-status.ts`); KEI table pipeline/`data/processed/kei_lines_*.json` empty copy.

---

## Summary table — Edge Board field coverage

Primary Sport Standard surface. Code capability (not live-row sparsity).

| Sport | Model/KEI | Market | Best | Edge | Confidence | Status/Tag | as-of | run_id |
|-------|-----------|--------|------|------|------------|------------|-------|--------|
| NFL | present | present | present | present | **partial** (Action cell) | present (Tag + ActionLabel) | present | absent |
| CFB | present | present | present | present | absent | present (PLAY sat→PASS) | present | absent |
| MLB | present | present | present | present | absent | present | present | absent |
| NBA | present | present | present | present | absent | present | present | absent |
| NHL | present | present | present | present | absent | present | present | absent |
| WNBA | present | present | present | present | absent | present | present | absent |

---

## Summary table — Fair / KEI Lines field coverage

| Sport | Model/KEI | Market | Best | Edge | Confidence | Status/Tag | as-of | run_id |
|-------|-----------|--------|------|------|------------|------------|-------|--------|
| NFL | present | partial | partial | partial | partial | partial | present | absent |
| CFB | present | absent | absent | absent | absent | absent | partial | absent |
| MLB | present | absent | absent | absent | absent | absent | partial | absent |
| NBA | present | absent | absent | absent | absent | absent | partial | absent |
| NHL | present | absent | absent | absent | absent | absent | partial | absent |
| WNBA | present | absent | absent | absent | absent | absent | partial | absent |

---

## Summary table — Props / Edges desk / Odds (compressed)

| Sport | Props board | Props tags | Edges desk tags | Odds Model/KEI |
|-------|-------------|------------|-----------------|----------------|
| NFL | live means/edge/conf; tag UI **absent** (null) | no PLAY/LEAN stake tags; WATCH in types only | no PLAY/LEAN/PASS col | absent |
| CFB | **no board** (→ tempo) | — | absent (on Edge Board) | absent |
| MLB | soft-launch shell | policy WATCH/PLAY/PASS stake off | absent | absent |
| NBA | Ch6 dark | forced **PASS** | absent | absent |
| NHL | Ch6 dark | forced **PASS** | absent | absent |
| WNBA | Ch6 dark | forced **PASS** | absent | absent |

Full per-board matrices: JSON `coverage_matrix.*`.

---

## Tags currently in use

| Tag | Sports / surfaces | Notes |
|-----|-------------------|-------|
| PLAY | Edge Board all six (policy-gated) | CFB PLAY sat→PASS; NFL spread lock `spread_play_v2_cap7` |
| LEAN | Edge Board all six | |
| PASS | Default everywhere | Props dark boards forced PASS |
| BEST VALUE / Best Value | **NFL only** (ActionLabel) | Remapped to PLAY when dead-tier (`nfl-dead-tiers.ts`) |
| **WATCH** (flag) | Prop policies NFL/NBA/MLB/WNBA | Web NFL props forces `tag: null` |
| **ALERT** (flag) | NFL ActionLabel | Non-standard |
| **STAY AWAY** (flag) | NFL ActionLabel | Already in code — inventory only; do not introduce as grammar |
| **isBestBet** (flag) | NFL boolean | Not a subscriber tag string / not “Best Bet” chrome |

Not found as board tags: `FIRE`, `PASS_HARD`, `BEST_BET` / `STAY_AWAY` (underscore forms).

---

## 1) Routes by sport

### NFL

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/nfl` | NFL Edge Board (public) | `app/edge-board/[sport]/page.tsx` |
| `/odds/nfl` | Compare Odds | `app/odds/[sport]/page.tsx` |
| `/pro/nfl/overview` | Desk hub | `pro/nfl/overview/page.tsx` |
| `/pro/nfl/slate/today` | Weekly Slate | `pro/nfl/slate/[date]/page.tsx` |
| `/pro/nfl/fair-lines` | KEI Lines | `pro/nfl/fair-lines/page.tsx` |
| `/pro/nfl/edges` | Model vs Market Edges | `pro/nfl/edges/page.tsx` |
| `/pro/nfl/props` | Props board | `pro/nfl/props/page.tsx` |
| `/pro/nfl/model` | Season Model | `pro/nfl/model/page.tsx` |
| `/pro/nfl/edge-board` | → `/edge-board/nfl` | `pro/nfl/edge-board/page.tsx` |
| `/pro/nfl/teams` (+ `[team]/[view]`) | Team Intel | `pro/nfl/teams/*` |
| `/pro/power-ratings/nfl` | Power Ratings | `pro/power-ratings/[sport]/page.tsx` |
| `/pro/nfl/fantasy` (+ builder/mock/…) | Fantasy desks | `pro/nfl/fantasy/*` |
| `/pro/nfl/survivor` | Survivor | `pro/nfl/survivor/page.tsx` |
| `/pro/nfl/game-boxes` | Game Boxes | `pro/nfl/game-boxes/page.tsx` |
| `/pro/nfl/camp` | Camp Desk | `pro/nfl/camp/page.tsx` |
| `/pro/nfl/execution` | Execution Monitor | `pro/[sport]/execution/page.tsx` |
| `/pro/nfl/injuries` | Injuries & News | `pro/nfl/injuries/page.tsx` |
| `/pro/nfl/launch-notes` | How to read desk (public) | `pro/nfl/launch-notes/page.tsx` |
| Also: projections, awards, previews, dfs, weekly-fantasy, news, standings, depth-charts | Desks / tools | various under `pro/nfl/` |

**APIs:** `/api/edge-board/nfl/assemble`, `/api/odds/nfl/compare`, `/api/nfl/fair-lines`, `/api/nfl/edges-desk`

### CFB

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/cfb` | CFB Edge Board (`?week=0\|1`) | `edge-board/[sport]/page.tsx` |
| `/odds/cfb` | Compare Odds | `odds/[sport]/page.tsx` |
| `/pro/cfb/overview` | Overview | `pro/cfb/overview/page.tsx` |
| `/pro/cfb/slate` | Official slate | `pro/cfb/slate/page.tsx` |
| `/pro/kei-lines/cfb` | KEI Lines (primary) | `pro/kei-lines/[sport]/page.tsx` |
| `/pro/cfb/fair-lines` | Fair Lines shell | `pro/[sport]/fair-lines/page.tsx` |
| `/pro/cfb/edges` | Edges | `pro/[sport]/edges/page.tsx` |
| `/pro/cfb/model` | Season Model | `pro/cfb/model/page.tsx` |
| `/pro/cfb/project-game` | Project Game | `pro/cfb/project-game/page.tsx` |
| `/pro/cfb/projections` | Projections | `pro/cfb/projections/page.tsx` |
| `/pro/cfb/futures` | Futures | `pro/cfb/futures/page.tsx` |
| `/pro/cfb/teams` | Power + Teams | `pro/cfb/teams/page.tsx` |
| `/pro/cfb/tempo` | Tempo & Havoc (props redirect) | `pro/[sport]/tempo/page.tsx` |
| Also: previews, conferences | Editorial | `pro/cfb/previews/*`, `conferences/*` |

**No CFB props board.** `/pro/cfb/props` → tempo.

### MLB

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/mlb` | MLB Edge Board | `edge-board/[sport]/page.tsx` |
| `/odds/mlb` | Compare Odds | `odds/[sport]/page.tsx` |
| `/pro/mlb/overview` | Overview | `pro/[sport]/overview/page.tsx` |
| `/pro/mlb/slate/today` | Daily Slate | `pro/[sport]/slate/[date]/page.tsx` |
| `/pro/mlb/fair-lines` | KEI Lines (ML/total/run line) | `pro/mlb/fair-lines/page.tsx` |
| `/pro/mlb/edges` | MLB Edges | `pro/mlb/edges/page.tsx` |
| `/pro/mlb/props` | Props soft-launch | `pro/[sport]/props/page.tsx` |
| `/pro/mlb/teams` | Team Research | `pro/[sport]/teams/page.tsx` |
| `/pro/power-ratings/mlb` | Power Ratings | `pro/power-ratings/[sport]/page.tsx` |
| Also: injuries, execution, tracking, matchups | Shared `[sport]` desks | |

### NBA

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/nba` | NBA Edge Board | `edge-board/[sport]/page.tsx` |
| `/odds/nba` | Compare Odds | `odds/[sport]/page.tsx` |
| `/pro/nba/overview` | Overview | `pro/[sport]/overview/page.tsx` |
| `/pro/nba/slate/today` | Daily Slate | `pro/[sport]/slate/[date]/page.tsx` |
| `/pro/nba/fair-lines` | KEI Lines | `pro/nba/fair-lines/page.tsx` |
| `/pro/nba/edges` | Edges | `pro/[sport]/edges/page.tsx` |
| `/pro/nba/props` | Props (Ch6 dark) | `pro/[sport]/props/page.tsx` |
| `/pro/nba/fantasy` | Fantasy | `pro/nba/fantasy/page.tsx` |
| `/pro/nba/teams` | Team Research | `pro/[sport]/teams/page.tsx` |
| `/pro/power-ratings/nba` | Power Ratings | `pro/power-ratings/[sport]/page.tsx` |

### NHL

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/nhl` | NHL Edge Board | `edge-board/[sport]/page.tsx` |
| `/odds/nhl` | Compare Odds | `odds/[sport]/page.tsx` |
| `/pro/nhl/overview` | Overview | `pro/[sport]/overview/page.tsx` |
| `/pro/nhl/slate/today` | Daily Slate | `pro/[sport]/slate/[date]/page.tsx` |
| `/pro/nhl/fair-lines` | Fair Lines (dynamic shell) | `pro/[sport]/fair-lines/page.tsx` |
| `/pro/kei-lines/nhl` | KEI Lines (primary href) | `pro/kei-lines/[sport]/page.tsx` |
| `/pro/nhl/edges` | Edges | `pro/[sport]/edges/page.tsx` |
| `/pro/nhl/props` | Props (Ch6 dark) | `pro/[sport]/props/page.tsx` |
| `/pro/nhl/goalies` | Goalie Desk | `pro/[sport]/goalies/page.tsx` |
| `/pro/nhl/fantasy` | Fantasy | `pro/nhl/fantasy/page.tsx` |
| `/pro/nhl/teams` | Team Research | `pro/[sport]/teams/page.tsx` |
| `/pro/power-ratings/nhl` | Power Ratings | `pro/power-ratings/[sport]/page.tsx` |

### WNBA

| Path | Title / purpose | File |
|------|-----------------|------|
| `/edge-board/wnba` | WNBA Edge Board | `edge-board/[sport]/page.tsx` |
| `/odds/wnba` | Compare Odds | `odds/[sport]/page.tsx` |
| `/pro/wnba/overview` | Overview | `pro/[sport]/overview/page.tsx` |
| `/pro/wnba/slate/today` | Daily Slate | `pro/[sport]/slate/[date]/page.tsx` |
| `/pro/wnba/fair-lines` | KEI Lines | `pro/wnba/fair-lines/page.tsx` |
| `/pro/wnba/edges` | Edges | `pro/[sport]/edges/page.tsx` |
| `/pro/wnba/props` | Props (Ch6 dark) | `pro/[sport]/props/page.tsx` |
| `/pro/wnba/fantasy` | Fantasy | `pro/wnba/fantasy/page.tsx` |
| `/pro/wnba/teams` | Team Research | `pro/[sport]/teams/page.tsx` |
| `/pro/power-ratings/wnba` | Power Ratings | `pro/power-ratings/[sport]/page.tsx` |

**Nav 404 traps (tools list):** `/pro/{mlb|nba|nhl|wnba}/standings` and several `/stats` links → `notFound()` (NFL-only pages). Inventory only — not a fix PR.

---

## 2) Board field evidence (major surfaces)

### Edge Board (all sports)

- **UI cols:** Open O/U, Open Line, Current Line, Current O/U, KEI Line, KEI O/U, Edge, Tag/Action — `EdgeBoard.tsx`
- **NFL assemble live fields seen:** `kei`, `modelKei`, `best`, `open`, `market`, `edgeMagnitude`, `publishTag`, `actionLabel`, `modelConfidenceScore|Band`, `linesAsOf`, `isBestBet` — **no `run_id`**
- **Confidence:** NFL Action cell only → **partial**; other sports **absent**
- **CFB:** trust labels (`cfbMarketTrusted`); Open/Best empty until Odds NCAAF (honest empty copy)

### Fair / KEI Lines

- NFL: richest payload (`NflFairLinesClient` + `/api/nfl/fair-lines`); UI Model/KEI/market subset; tags/confidence/best mostly payload
- MLB/NBA/WNBA static fair-lines: Model/KEI (or fair=KEI); no market/best/edge/tag table
- CFB/NHL: `/pro/kei-lines/{sport}` `KeiLinesTable` = Away/Home/Proj line/O/U only

### Props

- NFL: means, line, edge, confidence; **tags suppressed**
- NBA/NHL/WNBA: Best + Edge + proj; tag forced PASS; dark copy
- MLB: soft-launch / gated
- CFB: absent

### Edges desk

- NFL: kosedgeLine / marketLine / edge / marketAsOf; confidence **filter-only**
- MLB: edges + qualityScore (≠ confidence band)
- Others: derived from Edge Board tonight; **no tag column**

### Odds compare

- Market per-book + best-book highlights + asOf; **no** Model/KEI/Edge/Tag/Confidence/run_id

---

## 4) Empty-state / error copy (customer-visible)

| Board | Representative copy | Ops language? |
|-------|---------------------|---------------|
| Edge Board | `Board temporarily unavailable. Refresh to try again.` · `No Slate Yet` · CFB Odds/NCAAF empty pack note | No |
| Odds | `Odds temporarily unavailable…` · `No odds data yet…` (desktop-only) | No |
| Fair/KEI | NFL honest empty / Kosedge-only market · NBA/WNBA/MLB “no projections… daily sim” · NHL/CFB “Model board pending” | Partial |
| KEI table | `Run the pipeline export to generate data/processed/kei_lines_*.json` | **Yes** |
| Props | NFL no PLAY/LEAN stake tags · NBA/NHL/WNBA Ch6 dark · MLB soft-launch gate | Partial |
| Model errors | `Model service is not configured for this environment.` | **Yes** |
| ODDS_API_KEY / Vercel deploy ops | **Not found** in board UI | — |

Full quote list with files: JSON `sports.*.empty_states`.

---

## 5) Mobile filter presence

| Board | NFL | CFB | MLB | NBA | NHL | WNBA |
|-------|-----|-----|-----|-----|-----|------|
| Edge Board | yes (week/sport chips) | yes (week chips) | yes (sport) | yes (sport) | yes (sport) | yes (sport) |
| Odds | yes (sport) | yes | yes | yes | yes | yes |
| Fair/KEI | yes (slate window) | no | yes (run-line focus) | yes (date) | no | yes (date) |
| Props | yes (market chips) | n/a | no | no | no | no |
| Edges desk | yes (market/edge/conf) | no | yes (market/edge/quality) | no | no | no |

No dedicated `MobileFilter` drawer/Sheet on these boards. Filter chips use `flex-wrap` (shared mobile+desktop). Edge/Odds mobile **cards** ≠ filters.

---

## CoS handoff notes

1. Use JSON `coverage_matrix` as the gap-matrix seed (sport × board × field).
2. NFL is the only sport with dual Tag + ActionLabel + confidence on Edge Board.
3. Fair/KEI Lines outside NFL are Model/KEI-only tables — largest structural gap vs Edge Board grammar.
4. Non-standard tags already in code (WATCH, ALERT, STAY AWAY, isBestBet) are flagged — inventory, not product language.
5. Ops copy still customer-visible: model-service env string + KEI pipeline path — preferred to remove in a later copy PR (out of scope here).
