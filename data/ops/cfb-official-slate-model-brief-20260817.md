# Brief-ready — In-house Official Slate on `/pro/cfb/model`

**Date:** 2026-08-17  
**Device context:** Mobile product pass (futures #257 already live)  
**Status:** Shipped as packaged desk SoT — not a greenfield build  
**Do not:** touch Odds API historical burns or `/Volumes/KosEdgeData/raw/odds/**` (Mac owns archive)

## Verdict

Official Slate is already on the CFB model hub and dedicated slate route. Next work is **gap closure + weekly refresh discipline**, not a full scrape rewrite.

| Surface | Live? | Notes |
|---------|-------|-------|
| `/pro/cfb/model` | Yes | `CfbOfficialSlatePanel` · Week 0/1 tabs · Project → deep links |
| `/pro/cfb/model?week=1` | Yes | Full W1 list renders |
| `/pro/cfb/slate` | Yes | Same artifact / attribution |
| `/pro/cfb/project-game` | Yes | Loads slate row via query params |

**Artifact:** `apps/web/lib/data/cfb-official-slate-2026.json`  
**Version:** `cfb-official-slate-v2-dual-20260817` · `as_of` 2026-08-17 · primary ESPN pack `2026-08-13`  
**Publisher:** `scripts/cfb/publish_official_slate_2026.py`  
**Ops log:** `data/ops/cfb-official-slate-20260817.md`

## Source stack (current)

| Role | Source | Credit / call shape |
|------|--------|---------------------|
| Primary | Packaged ESPN team schedule | Offline season file — **not** live-scraped each publish |
| Fact-check | The Odds API NCAAF **events** | `/v4/sports/americanfootball_ncaaf/events` only — **no historical** |
| Desk doctrine | KosEdge slate is SoT | Railway remote boards do not override (`resolveWeekBoard`) |

Tried / not used this pass: CFBD `/games` (needs key), NCAA.com 2026 scoreboard (404), SportsDataverse 2026 parquet (not a live publish), Wikipedia (featured only).

## Counts (W0–W1)

| Week | Published | FBS–FBS | Fact-check accepted | Unconfirmed (ESPN-only) |
|------|----------:|--------:|--------------------:|------------------------:|
| 0 | 8 | 6 | 8 | 0 |
| 1 | 89 | 43 | 43 | 46 (mostly FCS openers) |
| **Total** | **97** | **49** | **51** | **46** |

Conflicts: **none**. Only-in-Odds-API (not added): 13 later-season matchups correctly excluded.

## Product gaps (ordered)

1. **Network / TV empty** — `network` is null on 97/97 rows; venue is filled. Fill when a cheap non-historical source exists.
2. **Primary freshness lag** — ESPN pack `primary_as_of=2026-08-13` vs slate `as_of=2026-08-17`. Kickoff moves need a primary-file refresh *before* re-publish, not a live ESPN scrape bolted onto the page.
3. **W2+ not in desk artifact** — Hub/tabs only expose weeks `[0,1]`. Extend only when primary pack + fact-check agree; do not invent from Odds API alone.
4. **W1 FCS honesty** — 46 `unconfirmed_secondary` is correct (books rarely list FCS). UI already says unconfirmed ≠ invented; optional: filter chip “FBS–FBS only” on mobile model panel.
5. **Model hub density** — Default Week 0 is sparse (8 games). Consider defaulting to soonest week with games, or a one-line “Week 1 · 89 games” CTA above tabs (UX only).
6. **CFBD optional upgrade** — If `CFBD_API_KEY` appears later, use as third fact-check — still not historical odds warehouse work.
7. **No PLAY / spread bake-in** — Keep `used_in_spread=false` on the slate artifact; Project Game stays research-fair.

## Non-goals (this brief)

- Full live NCAA/ESPN scrape pipeline on every page view
- Odds API historical endpoints or warehouse burns
- NFL season-engine jobs
- Blending book lines into sim %

## Suggested next PR (small)

**Title sketch:** CFB Official Slate — model-hub UX + refresh checklist  

- Optional: FBS–FBS filter + default-week polish on `/pro/cfb/model`  
- Ops: document “replace ESPN pack → re-run publish with events fact-check” as the weekly ritual  
- Skip scrape automation unless primary pack ingest is already trivial in-repo

## Smoke checklist (mobile)

- [ ] `/pro/cfb/model` shows Official Slate attribution + Week 0/1 tabs  
- [ ] Week 0: UNC @ TCU (or current W0 opener) + Project →  
- [ ] Week 1: dense list, unconfirmed FCS labeled honestly  
- [ ] `/pro/cfb/slate` matches the same `slate_version`  
- [ ] Credits: ESPN primary + Odds API **events** fact-check only — no historical calls  
