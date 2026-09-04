# Kos Edge #5 — Market / Odds Infrastructure Architecture Audit (LOCKED v1)

| Field         | Value                                                                                                                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Status**    | **LOCKED v1** (CoS 2026-09-04 ~01:40 ET)                                                                               |
| **Audience**  | Alex / CoS                                                                                                             |
| **SoT**       | www.kosedge.com probe ~01:32 ET (matrix also in `docs/ODDS_DATA_INFRA.md` after PR 459)                                |
| **Companion** | #4 Edge Board overnight audit                                                                                          |
| **Locks**     | no invent prices / CLV / history · no PLAY flips · Odds API key rotate Ryan-only · no invent freshness / Best formulas |

**Source:** CoS LOCKED Alex overnight architecture audit (2026-09-04 ~01:40 ET). Draft path at lock: `/workspace/ke5-market-odds-architecture-audit-DRAFT-2026-09-04.md`.

---

## Philosophy locks (verbatim)

1. **fail toward uncertainty**
2. **append-only market ledger**
3. **OPEN / CLOSE / BEST / CONSENSUS / AS-OF written before calc changes**
4. **STALE never wins Best**
5. **line + price independent**
6. **identity aliases ≠ truth**
7. **missing history = N/A—DATA GAP**
8. **no invent; no PLAY flips; key rotate Ryan-only**

**HARD RULE:** NO invent freshness windows or Best math.

---

## CoS LOCK

### Locked

- Philosophy (above) + integrity gap matrix + remediation sequence (below).
- **Best / STALE stay UNKNOWN** — do not invent FRESH / AGING / STALE windows or Best formulas from this audit.
- **persist=0 = R1 RED** (Alex + CoS) — subscriber fair-lines path must not be treated as ledger write.
- **Lab / Edge Board** may stay **N/A—DATA GAP** / **LIMITED** where history / CLV / closes are missing — fail toward uncertainty.

### Nit A — Edge Board alias (R9)

PR **454** already ships **308** `/pro/{sport}/edge-board` → `/edge-board/{sport}`. Re-spot after promo. Mark **R9 alias cleared** when confirmed on www.

### Nit B — R2 honesty vehicle

**R2** = PR **459** honesty vehicle (non-NFL fair-lines HTML soft-404 → customer-honest empty JSON 200). Flip **R2** only after merge + promo shows empty JSON **200**. Do not invent lines while flipping.

### SoT note — two docs, one purpose each

| Doc                                                           | Purpose                                                                                                                        |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **This file** (`docs/MARKET_ODDS_INFRASTRUCTURE_AUDIT_v1.md`) | **FULL #5** architecture audit + integrity / coverage / contract skeleton + Market Risk Register + remediation — **LOCKED v1** |
| **`docs/ODDS_DATA_INFRA.md`** (PR **459**)                    | **NARROW** overnight honesty contract — live fair-lines matrix + Lab DATA GAP inventory + TO-BE-LOCKED defs stub               |

Do **not** merge purposes. Do **not** invent Best / freshness into either doc.

---

## 1. Current-state (Alex www probe ~01:32 ET)

### Fair-lines API (`GET /api/{sport}/fair-lines`)

| Sport     | Probe (~01:32 ET) | Notes                                                                                          |
| --------- | ----------------- | ---------------------------------------------------------------------------------------------- |
| **nfl**   | **200**           | `count=241` · **9 books** · `oddsFeed=ok` · `oddsPersisted` **events/snapshots/history all 0** |
| **cfb**   | HTML **404**      | pre-459 soft-404 (no JSON route)                                                               |
| **ncaaf** | HTML **404**      | pre-459; Odds-API alias of CFB                                                                 |
| **mlb**   | HTML **404**      | pre-459                                                                                        |
| **nba**   | HTML **404**      | pre-459                                                                                        |
| **nhl**   | HTML **404**      | pre-459                                                                                        |
| **wnba**  | HTML **404**      | pre-459                                                                                        |

**Default-branch code (at lock):** only `apps/web/app/api/nfl/fair-lines/route.ts` for fair-lines page-data · `persistOdds: false` (read-only subscriber path; beat/worker owns persist).

### Live NFL line fields (present vs absent)

| Family        | Evidence on live NFL rows                            | Status                                                            |
| ------------- | ---------------------------------------------------- | ----------------------------------------------------------------- |
| **OPEN**      | `openSpreadHome` / `openTotal`                       | present                                                           |
| **BEST**      | `bestSpread*` / `bestTotal*` (+ book / juice fields) | present as **shape** — **Best formula = UNKNOWN / DO NOT INVENT** |
| **AS-OF**     | `asOf` / `oddsAsOf` / `oddsCapturedAt`               | present                                                           |
| **CLOSE**     | —                                                    | **ABSENT**                                                        |
| **CONSENSUS** | —                                                    | **ABSENT**                                                        |
| **STALE**     | —                                                    | **ABSENT** (no owned freshness enum / window)                     |
| **aliases**   | —                                                    | **ABSENT** as market-truth fields (identity aliases ≠ truth)      |

### Pro shells / redirects / Edge Board

| Surface                                           | Probe                                                                                        |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Pro fair-lines shells (`/pro/{sport}/fair-lines`) | **200** (nfl/cfb/mlb/nba/nhl/wnba)                                                           |
| `/pro/{sport}/kei-lines`                          | **308** → fair-lines except **`/pro/ncaaf/kei-lines` = 404** (pre-459)                       |
| Edge Board pages (`/edge-board/{sport}`)          | **200**                                                                                      |
| Assemble `linesAsOf`                              | **NFL / CFB** have `linesAsOf`; **mlb / nba / nhl / wnba** top `linesAsOf` **null** at probe |
| Public odds / health JSON                         | **None** (e.g. `/api/odds/health` not a public SoT)                                          |

### Ledger / keys

- **`book_ledger` ≠ market ledger** — pick/lean/pass grading store (`infra/db/053_book_ledger.sql`) is not the append-only odds market history.
- Odds API keys: **env-only** (`apps/web/lib/odds-api-keys.ts`) — no embed; **rotate Ryan-only**.

---

## 2. Integrity gap matrix

Legend: 🟢 owned / aligned · 🟡 partial / process-only · 🔴 defect or missing owned path · ⚪ UNKNOWN / not evidenced

| #   | Philosophy lock                                     | Status                  | Evidence / note                                                                                                                       |
| --- | --------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | fail toward uncertainty                             | 🟡                      | Honesty path exists for empty / unavailable; non-NFL still soft-404 pre-459; Lab/Edge Board may stay N/A—DATA GAP / LIMITED           |
| 2   | append-only market ledger                           | 🔴 / ⚪                 | Live `oddsPersisted=0` on subscriber path; append-only market ledger not evidenced as live SoT · warehouse schema exists but gate CoS |
| 3   | OPEN / CLOSE / BEST / CONSENSUS / AS-OF before calc | 🟡                      | OPEN / BEST\* / AS-OF present as fields · **CLOSE / CONSENSUS ABSENT** · defs must stay written before calc changes                   |
| 4   | STALE never wins Best                               | ⚪                      | STALE enum / windows **UNKNOWN** — **DO NOT INVENT**; cannot prove rule in product math                                               |
| 5   | line + price independent                            | 🟢                      | Shape present (line + juice / price fields on Best / open / market)                                                                   |
| 6   | identity aliases ≠ truth                            | 🟡                      | Sport / desk aliases (e.g. ncaaf↔cfb) exist; aliases must not become market truth                                                     |
| 7   | missing history = N/A—DATA GAP                      | 🔴                      | History / CLV series not landing on subscriber persist=0 path · Lab marks N/A—DATA GAP                                                |
| 8   | no invent; no PLAY flips; key rotate Ryan-only      | 🟢 process / 🟡 product | Process locks held overnight · product still carries gaps (404s, missing CLOSE, UNKNOWN Best/STALE)                                   |

---

## 3. Coverage matrix (sport × surface)

SoT: Alex www probe ~**01:32 ET** (pre-459 fair-lines API column). Post-459 honesty target documented in `docs/ODDS_DATA_INFRA.md` — flip R2 only per Nit B.

| Sport     | `/api/.../fair-lines`                              | `/pro/.../fair-lines` | `/pro/.../kei-lines` | `/edge-board/{sport}` | Assemble top `linesAsOf` | Public odds/health JSON |
| --------- | -------------------------------------------------- | --------------------- | -------------------- | --------------------- | ------------------------ | ----------------------- |
| **nfl**   | **200** LIVE · count=241 · 9 books · persist all 0 | **200**               | **308**              | **200**               | present                  | none                    |
| **cfb**   | HTML **404** (pre-459)                             | **200**               | **308**              | **200**               | present                  | none                    |
| **ncaaf** | HTML **404** (pre-459)                             | — / alias             | **404** (pre-459)    | — (use cfb)           | —                        | none                    |
| **mlb**   | HTML **404** (pre-459)                             | **200**               | **308**              | **200**               | **null**                 | none                    |
| **nba**   | HTML **404** (pre-459)                             | **200**               | **308**              | **200**               | **null**                 | none                    |
| **nhl**   | HTML **404** (pre-459)                             | **200**               | **308**              | **200**               | **null**                 | none                    |
| **wnba**  | HTML **404** (pre-459)                             | **200**               | **308**              | **200**               | **null**                 | none                    |

**CBB / NCAAM:** out of #5 overnight scope unless a broken link needs honest empty.

---

## 4. Canonical contract skeleton (fields only)

Formulas: **TBD** / **N/A—DATA GAP** / **DO NOT INVENT Best**. No invent freshness windows.

| Field             | Role (skeleton)                                                            | Formula / lock                                                                                                           |
| ----------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **OPEN**          | First-captured book open (**line + price**); immutable once set            | Field present on NFL (`openSpreadHome` / `openTotal`) · open=current invent **forbidden** · calc TBD from evidence       |
| **CLOSE**         | Closing line at kickoff / final                                            | **ABSENT** on live fair-lines · **N/A—DATA GAP** until owned history series                                              |
| **BEST**          | Shop-side best across carried books (**line + price**)                     | Shape present (`bestSpread*` / `bestTotal*`) · **Formula = DO NOT INVENT Best** · stays **UNKNOWN** until owned evidence |
| **CONSENSUS**     | Market average / consensus rule — never a KEI stand-in                     | **ABSENT** · **N/A—DATA GAP** / TBD                                                                                      |
| **AS-OF**         | Book vintage only (`last_update` / `odds_captured_at` / joined `oddsAsOf`) | Present · **never** request clock / `Date.now()`                                                                         |
| **line**          | Market number (spread / total / ML point)                                  | Independent of price                                                                                                     |
| **price**         | American juice / ML price paired to line                                   | Independent of line (−3 −105 ≠ −3 −120)                                                                                  |
| **stale**         | Freshness class (FRESH / AGING / STALE / UNAVAILABLE)                      | **UNKNOWN** · windows **N/A—DATA GAP** · **DO NOT INVENT** · STALE never wins Best (philosophy) once defined             |
| **aliases**       | Provider / desk identity aliases                                           | Aliases ≠ truth                                                                                                          |
| **history / CLV** | Append-only open→close series for Lab / grading                            | **N/A—DATA GAP** on live persist=0 path · do not invent CLV / prices                                                     |

---

## 5. Market Risk Register (R1–R11)

| ID      | Risk                                                                                                                  | Severity    | Owner / note                                                                                                                              |
| ------- | --------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **R1**  | `persist=0` / `oddsPersisted` all **0** on live NFL fair-lines — no append-only market ledger write on subscriber GET | 🔴          | **Alex + CoS** — next after honesty                                                                                                       |
| **R2**  | Non-NFL fair-lines HTML **404** (pre-459)                                                                             | 🔴          | Honesty vehicle = **PR 459** · flip after merge + promo empty JSON **200** (Nit B)                                                        |
| **R3**  | **CLOSE** absent on live fair-lines contract                                                                          | 🔴          | Blocks Lab CLV / close grading as product SoT                                                                                             |
| **R4**  | **STALE / Best** math                                                                                                 | ⚪          | **UNKNOWN** — do not invent windows or Best formula                                                                                       |
| **R5**  | Odds API key rotate                                                                                                   | 🟢          | Process owned · **Ryan-only** · env-only keys                                                                                             |
| **R6**  | Lab CLV / Market Edge Evidence                                                                                        | **LIMITED** | Scorecard / protocol may stay LIMITED · missing series = **N/A—DATA GAP**                                                                 |
| **R7**  | CFB / NCAAF fair-lines connectivity                                                                                   | 🔴 / alias  | Model has no `/cfb/fair-lines` · ncaaf alias · honesty empty ≠ connected board                                                            |
| **R8**  | No public odds / health JSON                                                                                          | 🟡          | No subscriber health SoT for odds pipeline                                                                                                |
| **R9**  | Edge Board trust / alias chrome                                                                                       | 🟡          | Companion #4 · PR 454 308 `/pro/.../edge-board` → `/edge-board/{sport}` · re-spot after promo (Nit A) · mark alias cleared when confirmed |
| **R10** | Odds warehouse gate                                                                                                   | 🟡          | `infra/db/052_nfl_odds_warehouse.sql` exists · **CoS-gated** — warehouse only if defect (Step 4)                                          |
| **R11** | `book_ledger` ≠ market ledger                                                                                         | 🟡          | Book pick ledger must not be mistaken for append-only odds market history                                                                 |

---

## 6. #3 Lab / #4 Edge Board dependencies

| Consumer                         | Dependency on #5                                                                        | Honest stance                                                                                                                                                         |
| -------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **#3 Model Validation Lab**      | Open→close / CLV series for Market Edge Evidence                                        | **CLV / closes blocked** where history missing → **N/A—DATA GAP** · Subscriber Influence may stay **LIMITED** · **fail toward uncertainty**                           |
| **#4 Edge Board Product Center** | Trusted market vintage (`linesAsOf`) · Best / Current display honesty · no invent as-of | Companion overnight Done (PRs 454–455) · still inherits #5 gaps (persist=0, CLOSE absent, Best/STALE UNKNOWN) · fail-closed stamps · **no PLAY flips** from odds gaps |

Garbage / missing quotes never create a stronger PLAY.

---

## 7. Remediation sequence

| Step       | Action                                        | Status / gate                                                              |
| ---------- | --------------------------------------------- | -------------------------------------------------------------------------- |
| **Step 0** | CoS lock philosophy + integrity + this audit  | **Done** (2026-09-04 ~01:40 ET)                                            |
| **Step 1** | Honesty — non-NFL fair-lines → empty JSON 200 | **PR 459** / agent `bc-b1200b8a` · flip **R2** after merge + promo (Nit B) |
| **Step 2** | Persist / append-only market ledger           | Address **R1** · beat/worker owns writes · not subscriber GET              |
| **Step 3** | Coverage                                      | Multi-sport fair-lines / as-of / alias parity after honesty                |
| **Step 4** | Warehouse                                     | **Only if defect** · CoS gate (**R10**) — not default overnight invent     |

### Non-remediations (hard)

- **No invent Best** math or FRESH / AGING / STALE windows
- **No PLAY flips** from this audit
- **No Odds API key rotate** except **Ryan**

---

## Evidence index

| Evidence                                        | Path                                                                             |
| ----------------------------------------------- | -------------------------------------------------------------------------------- |
| NFL fair-lines page-data (`persistOdds: false`) | `apps/web/app/api/nfl/fair-lines/route.ts`                                       |
| Persist contract test                           | `apps/web/__tests__/lib/nfl-fair-lines-persist.test.ts`                          |
| Odds API keys (env-only)                        | `apps/web/lib/odds-api-keys.ts`                                                  |
| Odds warehouse schema                           | `infra/db/052_nfl_odds_warehouse.sql`                                            |
| Book ledger schema (≠ market ledger)            | `infra/db/053_book_ledger.sql`                                                   |
| Market as-of / stale stamps ops                 | `data/ops/nfl-market-asof-stamps-20260903.md`                                    |
| Open/close grading ops                          | `data/ops/nfl-odds-open-close-grading.md`                                        |
| Narrow honesty matrix (companion doc)           | `docs/ODDS_DATA_INFRA.md` (PR 459)                                               |
| Edge Board product center (#4)                  | `docs/EDGE_BOARD_PRODUCT_CENTER.md`                                              |
| Live SoT probe                                  | www.kosedge.com ~01:32 ET (Alex) · NFL `count=241` / 9 books / `oddsPersisted=0` |

---

## CoS lock checklist

- [x] Philosophy locks quoted; HARD RULE — no invent freshness / Best math
- [x] Integrity gap matrix with 🟢🟡🔴⚪ per lock
- [x] Coverage matrix sport × surface (nfl/cfb/ncaaf/mlb/nba/nhl/wnba)
- [x] Canonical contract skeleton — formulas TBD / N/A—DATA GAP / DO NOT INVENT Best
- [x] Market Risk Register R1–R11
- [x] #3 Lab / #4 Edge Board deps — CLV/closes blocked; fail toward uncertainty
- [x] Remediation Steps 0–4 + non-remediations
- [x] Evidence index cited
- [x] Nit A (PR 454 Edge Board 308) + Nit B (PR 459 / R2 flip rule)
- [x] SoT separation from `docs/ODDS_DATA_INFRA.md`
- [x] Best / STALE remain UNKNOWN; persist=0 = R1 RED; Lab/Edge Board may stay N/A—DATA GAP / LIMITED
      )
