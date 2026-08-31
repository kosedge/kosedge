# CFB Edge Board Audit — Week 1

**Phase:** 0 (READ ONLY)  
**Branch:** `cursor/cfb-edgeboard-week1-slate-odds-3ca1`  
**Base:** `deploy-vercel` @ `41480c90` (#338)  
**Engine stamp (research SoT):** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31` · seed `20260831`  
**Utah blocker:** still present — `docs/CFB_ENGINE_BLOCKER.md` (out of scope)  
**Greps run:** official-slate / Odds / KEI / Edge tags (see § Grep evidence)

This pass is desk plumbing only. Power, WP curve, year-shock, Utah natty, and `apply_cfb_kei` formula are **not** in scope.

---

## Slate artifact

| Item | Finding |
|---|---|
| **UI desk SoT path** | `apps/web/lib/data/cfb-official-slate-2026.json` |
| **as_of** | **`2026-08-17`** (stale vs engine `2026-08-31`) |
| **slate_version** | `cfb-official-slate-v2-dual-20260817` |
| **weeks** | `[0, 1]` — `n_w0=8`, `n_w1=89`, `n_games=97` |
| **week field** | integer `week` on each game (`0` or `1`) |
| **home_score / away_score** | **absent** on all UI slate rows |
| **status** | all `"accepted"` (not final) |
| **Who reads it** | `apps/web/lib/cfb-official-slate.ts` → `packagedOfficialWeekBoard()`; pages `/pro/cfb/slate`, `/pro/cfb/project-game`, `/pro/cfb/model`; panel `CfbOfficialSlatePanel` |
| **Default week (slate UI)** | `parseOfficialSlateWeek(raw)` → `Number(raw ?? 0)` → **Week 0** when `?week=` missing |
| **Publisher** | `scripts/cfb/publish_official_slate_2026.py` (still stamps Aug 17 dual slate / ops `data/ops/cfb-official-slate-20260817.md`) |
| **Type gap** | `CfbWeekBoardGame` / `asGame()` **strip** any scores — Phase 1 must extend schema + UI to show finals |

### Engine schedule (already closed — do not re-sim)

| Item | Finding |
|---|---|
| **Path** | `services/model-service/src/services/cfb_season_engine/data/cfb_official_schedule_2026.json` |
| **as_of** | `2026-08-31` |
| **W0 finals locked** | UNC@TCU 15–10 · SJSU@USC 26–42 · NCSU@UVA 8–34 · HAW@STAN 27–37 · NMSU@FSU 17–34 · MEM@UNLV 27–21 (`status=final`) |
| **W0 still open (FCS/non-desk)** | JVST @ fcs:NDSU · fcs:SAC @ EMU (scores null) |
| **Closer** | `scripts/cfb/close_week0.py` writes scores into **engine schedule** only — **does not** update the UI official-slate JSON |

**Named cause of slate bug:** UI artifact never received Week 0 close; still Aug 17 “accepted” pack. Engine and research surfaces moved; slate desk did not.

---

## KEI pack

| Item | Finding |
|---|---|
| **Model-service SoT** | `services/model-service/src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json` |
| **Web mirror (Edge Board load)** | `apps/web/lib/data/cfb-kei-w0-w1-2026.json` (bundled import) |
| **as_of / engine** | `2026-08-31` · `cfb-season-engine-v0.15-power-sot` |
| **kei_version** | `cfb-kei-v1.0-2026w0` |
| **Coverage** | weeks `[0, 1]` · `n_games=97` · `n_fbs_with_kei=49` · `n_w0_fbs_with_kei=6` |
| **used_in_spread** | pack `true`; per-row KEI `used_in_spread=true` for FBS openers |
| **market_spread_home** | **all `null`** on pack — Edge/Tag cannot fire from artifact alone |
| **tag** | `"PASS"` on sampled W1 rows (no market) |
| **Builder** | `scripts/cfb/build_cfb_kei_futures_2026.py` → `apply_cfb_kei` (`cfb_kei.py`) |
| **Edge Board loader** | `getKeiLines("cfb")` → `cfbKeiLinesFromBundledPack()` in `apps/web/lib/kei-lines.ts` (filters `kei_spread_home != null`) |
| **Stale file (unused on Vercel NFT path)** | `apps/web/data/processed/kei_lines_cfb.json` still shows W0 UNC@TCU KEI −20.39 — **do not treat as SoT**; bundled pack wins |

### Family A / live-check presence (W1 in bundled KEI)

| Matchup | Present | `kei_spread_home` | Notes |
|---|---|---|---|
| Ball State @ Ohio State | yes `BALL@OSU` | −42.2 | FBS · used_in_spread |
| Texas State @ Texas | yes | −25.15 | |
| Tennessee State @ Georgia | yes `FCS:TNST@UGA` | **null** | FCS — KEI not published (`used_in_spread=false`); existing rule |
| Idaho @ Utah | yes `FCS:IDHO@UTAH` | **null** | FCS — same |
| FIU @ USF | yes | −19.74 | |
| East Carolina @ Alabama | yes | −26.22 | |
| UTEP @ Oklahoma | yes | −33.61 | |
| Missouri State @ Texas A&M | yes | −32.25 | |
| North Texas @ Indiana | yes | −33.12 | |
| Boise State @ Oregon | yes | −23.97 | |
| Miami @ Stanford | yes | +27.95 (home STAN) | |
| Clemson @ LSU | yes | −2.21 | |
| Wisconsin vs Notre Dame | yes `WIS@ND` | −16.67 | |
| Louisville vs Ole Miss | yes `LOU@MISS` | −11.53 | |
| SMU @ Florida State | yes | +8.35 (home FSU) | |
| Washington State @ Washington | yes | −18.62 | |

**Do not rewrite `apply_cfb_kei`.** FCS null KEI is existing house behavior; board may show the row from odds/slate membership with KEI blank — never invent FCS books.

---

## Edge Board routes

| Route | Behavior |
|---|---|
| `/edge-board` | **redirect → `/edge-board/ncaam`** (`apps/web/app/edge-board/page.tsx`) — CBB default |
| `/edge-board/cfb` | CFB board (`app/edge-board/[sport]/page.tsx`) |
| `/edge-board/cfb?week=0` / `?week=1` | week tabs |
| **CFB Overview / desk hrefs** | `pro-sport-desk.ts` / `sport-pro-nav.ts` → **`/edge-board/cfb`** (correct sport; **missing `?week=1`**) |
| Project Game secondary | `/edge-board/cfb` |
| Slate secondary | `/edge-board/cfb` (“Edge Board (markets)”) |

### How sport defaults to CBB

1. Bare `/edge-board` hard-redirects to `ncaam`.
2. `resolveSportKey(resolved?.sport, "ncaam")` fallback is also NCAAM if sport missing.
3. CFB product links already point at `/edge-board/cfb` — **not** the bare redirect. Production “defaults to CBB” for users hitting global Edge Board or a bad link; CFB Overview is sport-correct but week-wrong.

### CFB week default bug (code)

```ts
// app/edge-board/[sport]/page.tsx
const cfbWeek = sportKey === "cfb" && cfbWeekRaw === "1" ? 1 : 0; // missing → Week 0
week1Count = gameCount(all.filter((r) => r.week === 0)); // labels swapped
fullCount = gameCount(all.filter((r) => r.week === 1));
```

Default filter = **Week 0**. Tab count badges are **swapped** (Week 0 tab shows W0 count under wrong variable name; Week 1 tab uses `fullCount`).

### How a row is built

```
loadAssembledEdgeBoardRows("cfb")
  → pullOddsRows("cfb") via odds-api.fetchEdgeBoard  (SPORT_KEY_MAP.cfb)
  → withFallback → edge_board_fallback_cfb.json if live empty
  → resolveKeiGames("cfb") → bundled cfb-kei pack (kei_spread_home only)
  → ensureAllKeiGamesOnBoard + mergeKeiIntoEdgeBoardRows
  → applyCfbTrustedMarketToRows (clears untrusted best)
stampCfbEdgeBoardWeek(rows) → filter by cfbWeek
```

Edge / Tag UI uses KEI vs trusted Best only (not Model). PASS when market cleared or missing.

### Project Game UNC@TCU Week-1 label

`project-game/page.tsx`:

- `defaultHome = home \|\| "TCU"`, `defaultAway = away \|\| "UNC"`
- `week = Number(firstValue(sp.week) ?? **1**)` → bare `/pro/cfb/project-game` = **UNC @ TCU labeled Week 1**

Slate dropdown labels use real `W${g.week}` from Aug-17 artifact (UNC@TCU is W0 in JSON) — default form state still lies.

---

## Odds join

| Item | Finding |
|---|---|
| **Client** | `apps/web/lib/odds-api.ts` — **existing**; do not invent a new client |
| **Sport key (real)** | **`cfb` → `americanfootball_ncaaf`** already in `SPORT_KEY_MAP` |
| **Env keys** | `ODDS_API_KEY`, `ODDS_API_KEY_BACKUP` via `apps/web/lib/odds-api-keys.ts` (+ embedded backup constant in that file) |
| **This Cloud VM** | `ODDS_API_KEY` / `BACKUP` **unset** in process env at audit time — live pull untested here; production Vercel may still hold keys |
| **Open** | Preferenced first book in configured book list from the **current** Odds `/odds` snapshot — **not** a historical opening-lines endpoint. Honest product language: “Open” ≈ preference-book snapshot, or show `—` if policy wants true open only |
| **Best / Current** | Best away spread / total across allowed books (juice tiebreak) → row.`best` |
| **Empty live payload** | `pullOddsRows` returns `[]` → `withFallback` loads `apps/web/data/processed/edge_board_fallback_cfb.json` (`capturedAt=2026-07-31`, 252 priced rows including UNC@TCU +6.5/+7.0) |
| **Trusted guard** | Absurd Best vs KEI (≥12 pts) or single-book outlier → clears `best`, book=`untrusted` |

**Named causes Open/Current look blank on production (any of):**

1. Board defaults to **Week 0** / stale slate UX so user stares at closed games.
2. KEI pack has **`market_spread_home: null`** — Edge/Tag never precomputed.
3. Live Odds pull fails or returns 0 NCAAF events → fallback or empties; trusted-market then blanks junk.
4. Match-key miss between Odds full names and KEI abbrs (less likely for FBS; FCS often no book).
5. User lands on global `/edge-board` (NCAAM) and sees “No Slate Yet”.

**Stop condition met:** Odds sport key **named** (`americanfootball_ncaaf`) and slate JSON path **named**. Proceeding to Phase 1 allowlist is allowed after operator gate.

---

## Tag rules (verbatim from code)

From `apps/web/lib/cfb-trusted-market.ts`:

```ts
export const CFB_PLAY_EDGE_PTS = 4.0;
export const CFB_LEAN_EDGE_PTS = 2.5;
export const CFB_OUTLIER_VS_OPEN_PTS = 3.5;
export const CFB_ABSURD_VS_KEI_PTS = 12;
export const CFB_SINGLE_BOOK_ABSURD_PTS = 8;

export function cfbEdgeTag(absEdge: number | null | undefined): "PLAY" | "LEAN" | "PASS" {
  if (absEdge == null || !Number.isFinite(absEdge)) return "PASS";
  if (absEdge >= CFB_PLAY_EDGE_PTS) return "PLAY";
  if (absEdge >= CFB_LEAN_EDGE_PTS) return "LEAN";
  return "PASS";
}
```

Mirrored in `data/ops/cfb-kei-rules-2026.md` and Python `tag_from_edge` / `tag_thresholds` (early weeks PLAY 4.0 / LEAN 2.5).

**House truth for this pass:** LEAN ≥ **2.5**, PLAY ≥ **4.0**, PASS default.  
Brief’s “LEAN ≥ 1, PLAY ≥ 2.5” is **not** what live CFB code uses — **do not invent new thresholds**; keep 2.5 / 4.0.

---

## Why Open/Current are blank (named cause)

**Primary desk causes (confirmed in repo):**

1. **UI official slate stuck on `as_of=2026-08-17`** with no scores — Week 0 still “upcoming.”
2. **CFB Edge Board defaults to `week=0`** unless `?week=1`; Overview links omit the query.
3. **KEI pack has no market join** (`market_spread_home=null`) — Edge/Tag stay PASS/empty until live Odds Best survives the trusted-market guard.
4. **Odds join may be empty or fallback** — empty → dashes (correct); July fallback can supply numbers that the trusted guard then blanks as absurd vs post-close KEI.

Not causes for this pass: missing `americanfootball_ncaaf` map key (already present); missing KEI W1 rows for FBS Family A (present).

---

## Phase 1 allowlist

1. **Close Week 0 on UI slate artifact** — copy finals from engine schedule into `cfb-official-slate-2026.json`; stamp `as_of=2026-08-31`; extend `CfbWeekBoardGame` + slate UI for scores/status=final; keep W0 rows.
2. **Default week = 1** — `parseOfficialSlateWeek`, Edge Board `cfbWeek`, Overview/desk deep links `?week=1`; fix swapped week tab counts.
3. **Project Game** — default week from slate matchup (UNC@TCU → week 0) or stop defaulting UNC/TCU as W1; dropdown already has correct W# once slate is stamped.
4. **KEI** — rebuild via existing `build_cfb_kei_futures_2026.py` only if pack drift; **do not** rewrite `apply_cfb_kei`. Confirm W1 FBS KEI still present after any rematerialize.
5. **Odds** — keep `fetchEdgeBoard` + `americanfootball_ncaaf`. Prefer live pull; if 0 events, market columns `—` + footer “waiting on Odds API”. Do **not** invent opens. Document that current client “Open” is preference-book from current snapshot (or leave Open blank if operator insists on true historical open — no new scraper).
6. **Edge/Tag** — only when KEI + trusted Best; thresholds unchanged (2.5 / 4.0).
7. **Deep link** — CFB Overview Edge Board → `/edge-board/cfb?week=1`. Optional: bare `/edge-board?sport=cfb` only if a redirect already exists; do not break NCAAM default for other sports.
8. **Docs** — `CFB_EDGEBOARD_WEEK1_SCORECARD.md`; `CFB_EDGEBOARD_BLOCKER.md` only if production Odds cannot return NCAAF.
9. **Out of scope** — power, WP, shock, Utah blocker, NFL/CBB/MLB product trees (except sport-key map if somehow missing — already present).

---

## Blockers already visible

| Blocker | Severity | Notes |
|---|---|---|
| UI slate ≠ engine close | **Must fix Phase 1** | Allowlisted artifact edit |
| Edge Board week default 0 + swapped counts | **Must fix Phase 1** | Code allowlist |
| Project Game UNC@TCU as Week 1 | **Must fix Phase 1** | Default week/home mapping |
| Live Odds empty in this agent env | **Acceptable** | Ship KEI-only + dashes if prod key also fails; write `CFB_EDGEBOARD_BLOCKER.md` naming env/plan — **do not invent lines** |
| FCS KEI null (TNST@UGA, IDHO@UTAH) | **Informational** | Existing `apply_cfb_kei` — leave |
| Stale `kei_lines_cfb.json` / July odds fallback | **Hygiene** | Bundled pack is SoT; fallback must not invent; prefer empty over wrong-week PLAY |
| Utah natty 6.2% | **Prior blocker** | `docs/CFB_ENGINE_BLOCKER.md` — untouched |
| Global `/edge-board` → NCAAM | **Product default** | CFB clicks must use `/edge-board/cfb?week=1`; do not retarget all sports to CFB |

---

## Grep evidence (Phase 0)

Commands executed (summarized hits):

- `official-slate|20260817|Week 0` → UI JSON Aug 17; publisher; `cfb-official-slate.ts`; slate/project-game pages.
- `ODDS_API|americanfootball_ncaaf` → `odds-api.ts` map `cfb: "americanfootball_ncaaf"`; keys helper.
- `apply_cfb_kei|cfb-kei-w0|used_in_spread` → `cfb_kei.py`, builder script, web pack, product_desk.
- Edge tags → `cfb-trusted-market.ts` PLAY 4.0 / LEAN 2.5; Edge Board page week filter.

---

## Phase 0 gate

**Ready for Phase 1** after operator sign-off:

- Odds sport key: **`americanfootball_ncaaf`**
- Slate JSON path: **`apps/web/lib/data/cfb-official-slate-2026.json`**
- KEI SoT path: **`apps/web/lib/data/cfb-kei-w0-w1-2026.json`** (mirror of model-service pack)
- No new odds client required
- No power / WP / Utah edits proposed

**Awaiting gate before any product code or artifact mutation.**
