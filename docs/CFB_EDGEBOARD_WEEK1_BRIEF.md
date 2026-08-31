# CFB Edge Board — Week 1 operational pass (tonight)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after #337 + #338  
**Tag truth:** `cfb-week0-close-2026-08-31`  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31` · seed `20260831` · N=10000

This is **not** a ratings pass. Power, WP curve, year-shock, Utah title %, and KEI formula stay put.

The desk is broken because the **board** still reads the Aug 17 Week 0 slate and has **no book join**. Research already moved. Edge Board did not.

---

## 0. What “done and good” means tonight

A user on production can:

1. Open CFB Edge Board and see **Week 1 unplayed games**, not Sat Aug 29 finals as if they have not happened.
2. See **KEI line + KEI total** on those rows from the existing `apply_cfb_kei` / W0-W1 pack rebuilt after close.
3. See **Open** and **Current/Best** when The Odds API (or the house odds join already used for CBB/NFL) returns NCAAF.
4. See **Edge** and **Tag** only when both KEI and a real book price exist. Otherwise dashes. Tag default **PASS**.
5. Official slate page `as_of` matches engine `2026-08-31`. Week 0 rows show **finals**. Week 1 is the default tab.
6. Stamp everywhere: `v0.15-power-sot` · `as_of=2026-08-31`. No `v0.9-inseason`. No `2026-08-17` on live surfaces.

“Fire on” tonight means: the board is an honest KEI-vs-market desk with PASS default. It does **not** mean loud PLAY tags or selling Utah 6.2%.

If Odds API has no CFB key / empty slate, ship the board with KEI filled and market columns explicitly empty. That is still a successful pass. Inventing -21.5 because “OSU should be a three-score favorite” is an automatic fail.

---

## 1. Laws

Inherited. Still binding.

1. One engine. One `as_of=2026-08-31`.
2. Do not reshuffle top-7 power.
3. Do not train on Week 0. Scores go on the slate. Power does not move.
4. Do not invent market prices. Ever.
5. No team-id branches.
6. No second CFB stack.
7. NFL/CBB/MLB product files untouched unless a shared odds sport-key map is missing `ncaaf` / `americanfootball_ncaaf`.
8. KEI is the published game line. Not E[wins]. Not natty %.
9. Utah blocker stays. Not this pass.
10. Do not stretch WP / playoff scale.
11. Preview prose is regenerated from artifacts if it must change. Do not hand-type sides.
12. Tag thresholds stay house: PASS default, LEAN ≥ 1, PLAY ≥ 2.5 (or whatever the live Edge Board already uses — **read it, do not invent new thresholds**).

---

## 2. Production bugs you must confirm in Phase 0

Already observed on kosedge.com (2026-08-30 night):

| Surface                 | Observed                                                                                    | Required                  |
| ----------------------- | ------------------------------------------------------------------------------------------- | ------------------------- |
| `/pro/cfb`              | stamp `v0.15-power-sot` · `as_of 2026-08-31`                                                | keep                      |
| `/pro/cfb/projections`  | new E[wins] board (MIA 10.12, OSU 9.54, USF E#15/P#42)                                      | keep                      |
| `/pro/cfb/project-game` | stamp `v0.15-power-sot`; slate dropdown still “W0/W1”; default UNC/TCU labeled Week 1       | fix mapping               |
| `/pro/cfb/slate`        | `as_of 2026-08-17` · `cfb-official-slate-v2-dual-20260817` · default **Week 0** · no scores | close + default Week 1    |
| `/edge-board`           | defaults to **CBB**, “No Slate Yet”, no Open/Best                                           | CFB sport key + odds join |
| CFB Edge Board          | looks like last week; no open/current                                                       | Week 1 + real books       |

---

## 3. Phase 0 — Discovery (READ ONLY)

Write `docs/CFB_EDGEBOARD_AUDIT_WEEK1.md` before any edit.

### Greps

```bash
rg -n "official-slate|cfb-official-slate|W0/W1|week_0|Week 0|as_of 2026-08-17|20260817" \
  apps/web services/model-service scripts/cfb | head -300

rg -n "ODDS_API|the-odds-api|americanfootball_ncaaf|ncaaf|fair-lines|fair_lines|open_line|best_line" \
  apps/web services | head -300

rg -n "apply_cfb_kei|cfb-kei-w0|kei_lines_cfb|used_in_spread" \
  apps/web services/model-service scripts/cfb | head -200

rg -n "PASS|LEAN|PLAY|edgeThreshold|TAG_" apps/web --glob '*edge*' | head -150
```

### Required audit headings

```markdown
# CFB Edge Board Audit — Week 1

## Slate artifact

path, as_of, week field, whether home_score/away_score exist, who reads it

## KEI pack

path, week coverage (W0 vs W1), used_in_spread, builder script

## Edge Board routes

/edge-board vs /pro/cfb Edge Board tab — real hrefs
how sport defaults to CBB
how a row is built (KEI join + odds join)

## Odds join

env keys (ODDS_API_KEY etc.)
sport key for CFB (must find real key, do not guess and hope)
open vs current vs best
what happens on empty payload today

## Tag rules (verbatim from code)

## Why Open/Current are blank (named cause)

## Phase 1 allowlist

## Blockers already visible
```

Stop if you cannot name the Odds sport key and the slate JSON path. Do not invent a new odds client.

---

## 4. Phase 1 — Implementation (allowlist only)

Do in this order.

### 4.1 Close Week 0 on the official slate artifact

The engine already locked:

- UNC 15–10 TCU
- SJSU 26–42 USC
- NCSU 8–34 UVA
- HAW 27–37 STAN
- NMSU 17–34 FSU
- MEM 27–21 UNLV

Write those into the **same** official-slate artifact the UI reads. Stamp `as_of=2026-08-31`. Status = final. Do not delete Week 0 rows — show them as final.

Default tab / default Edge Board filter = **Week 1 unplayed**.

Fix the Project Game bug: UNC @ TCU must not be labeled Week 1.

### 4.2 Rebuild the KEI W1 board from existing mapper

Run the existing `scripts/cfb/build_cfb_kei_futures_2026.py` (or whatever the audit names). Do not rewrite `apply_cfb_kei`.

Week 1 rows that must exist (confirm against official slate; do not invent extras):

Family A (audit games — big favorite, lesser opponent):

- Ball State @ Ohio State
- Texas State @ Texas
- Tennessee State @ Georgia
- Idaho @ Utah (FCS — KEI ok, do not invent a book if Odds has no FCS)
- FIU @ USF
- East Carolina @ Alabama
- UTEP @ Oklahoma
- Missouri State @ Texas A&M
- North Texas @ Indiana

Live checks:

- Boise State @ Oregon
- Miami @ Stanford
- Clemson @ LSU
- Wisconsin vs Notre Dame (Lambeau)
- Louisville vs Ole Miss (Nashville)
- SMU @ Florida State (Monday)
- Washington State @ Washington

If a game is not on the official slate JSON, skip it. Do not add by hand.

### 4.3 Join Open + Current/Best

Use the **existing** odds client the CBB/NFL boards use.

- Sport key: whatever the house already maps for NCAAF. If missing, add one key to the existing map. That is the only allowed shared-file edit.
- Open = opening line from the feed if the client already stores it. If the client only has current, show Current/Best and leave Open as `—`. Do not fake an open.
- Best = best available price across books the client already shops.
- If the API returns 0 CFB events: market columns stay `—`, footer says “waiting on Odds API”, **do not** write consensus from memory.

### 4.4 Edge + Tag

```
edge_line = signed difference KEI vs Best
tag = existing house thresholds (read from code)
```

No book ⇒ no edge ⇒ no tag (or explicit PASS with “no market”).  
Never tag off Model vs market. Only KEI vs market.

### 4.5 Default sport / deep link

CFB Overview “Edge Board” must land on the CFB board with Week 1 selected, not global CBB `/edge-board`.

`/edge-board?sport=cfb` (or the real query the app already uses) must switch the pill and the payload.

---

## 5. What you will not change

- `priors.SCORE_NOISE_SD`, `STRENGTH_NOISE`, `WIN_PROB_MARGIN_SD`
- power SoT numbers
- futures / Utah natty
- KEI definition
- NFL DepthSot skip rule
- Tag thresholds (unless they are hardcoded wrong for CFB only — then document, do not silently change)

---

## 6. Deliverables

| File                                    | When                                                          |
| --------------------------------------- | ------------------------------------------------------------- |
| `docs/CFB_EDGEBOARD_WEEK1_BRIEF.md`     | this brief in-repo                                            |
| `docs/CFB_EDGEBOARD_AUDIT_WEEK1.md`     | Phase 0                                                       |
| `docs/CFB_EDGEBOARD_WEEK1_SCORECARD.md` | Phase 1                                                       |
| `docs/CFB_EDGEBOARD_BLOCKER.md`         | only if odds client cannot see NCAAF and you refuse to invent |

### Scorecard minimum

| Check                              | After                             |
| ---------------------------------- | --------------------------------- |
| Slate `as_of`                      | 2026-08-31                        |
| Week 0 rows                        | finals, not upcoming              |
| Default week on Edge Board + Slate | Week 1                            |
| Engine stamp                       | `v0.15-power-sot`                 |
| KEI present on Week 1 FBS rows     | yes                               |
| Open column                        | real or `—` (never invented)      |
| Current/Best column                | real or `—`                       |
| Edge/Tag                           | only when both KEI and Best exist |
| UNC–TCU labeled                    | Week 0 final                      |
| Power top-7                        | unchanged                         |
| Utah blocker file                  | still present                     |
| NFL/CBB/MLB product diffs          | none                              |

Dump command: existing `scripts/cfb/cfb_dump_canaries.py` plus a new small `scripts/cfb/cfb_dump_edgeboard.py` **only if** the repo already dumps board rows that way. Prefer printing from the same loader the page uses.

---

## 7. Done / not-done / blocker

### Done

- Slate closed and dated 2026-08-31
- Week 1 is the live board
- KEI on Week 1 from existing mapper
- Market columns honest
- Deep link from CFB desk works
- Canaries / power untouched
- CI green under existing path-based NFL skip

### Not done

- Invented opens
- PLAY spam on cupcakes
- Power refit
- “OSU -28 because we want to fire”
- CBB-default still catching CFB clicks

### Blocker (acceptable)

- Odds API plan/key has no NCAAF → ship KEI-only board + `docs/CFB_EDGEBOARD_BLOCKER.md` naming the missing key. Operator adds the key; you do not scrape books.

---

## 8. Operator “fire on” rule after merge

Even with a working board:

- Default tag is PASS.
- Family A cupcakes: research-fair + KEI display. Do not PLAY a 28-point favorite just because WP is now 0.98.
- Edge ≥ house PLAY threshold **and** a named driver in one sentence before anything is loud.
- Utah / USF season numbers stay off this board.

Tonight’s win is a **working desk**. Not a card of plays.
