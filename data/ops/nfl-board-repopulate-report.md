# NFL Board Repopulate + Edge Board Polish Report

**Date:** 2026-07-30 (overnight)  
**Scope (this agent):** Edge Board LOOK + Hub IA polish verification / restore  
**Data/API work:** Handled by sibling (fair-lines 167, KEI/PLAY, projections, `MODEL_SERVICE_URL`) — sims not re-run here.

---

## Verdict

**Premium Edge Board polish + Hub IA are already live on production** via `deploy-vercel`. No UI merge or redeploy was required tonight.

| Surface | Status |
|--------|--------|
| Edge Board look (PLAY green / PASS muted, Edge·Tag, Market vs Model) | **LIVE** |
| Selective publish (YELLOW, LEAN off spreads, PLAY ≥2.5) | **LIVE** |
| Hub IA (Weekly Slate / Betting Desk / Props & Fantasy / Team Intel / Model Governance) | **LIVE** |
| HTTP smoke (boards below) | **200** |

---

## Git / deploy ancestry

| Commit | What | On `origin/deploy-vercel`? |
|--------|------|----------------------------|
| `e31843b9` `edge-board-premium-polish` | Original visual hierarchy (Market/Model/Decision, tag chrome) | Visual chrome **merged forward** via restore |
| `e0d12411` | Restore NFL Hub IA + Edge Board polish on deploy | **YES** |
| `2eef52d2` | Restore Edge Board polish **with selective NFL PLAY tags** | **YES** |
| Tip `3e522691` | Current production branch tip | **YES** |

Diff `deploy-vercel` vs `edge-board-premium-polish` is **policy only** (selective publish / `nfl-publish-policy` + server `publishTag`), not a visual regression. Visual helpers (`tagClassName`, `edgeCellClass`, `COL_MARKET` / `COL_MODEL` / `COL_DECISION`, `TagPlayCell`) match the polished board.

**Vercel production:** `https://www.kosedge.com` · project `kos-edge-analytics-projects/kosedge` · latest Ready production deploy ~2h before this check (`kosedge-fa4oa20wv-…`). CSS deploy id observed: `dpl_Az7fNMBapqbdJ7X6Zwa1pzTwGAJt`.

---

## Live Edge Board smoke (`/edge-board/nfl`)

**URL:** https://www.kosedge.com/edge-board/nfl

Observed in browser (2026-07-30):

- 16 games · current week slate populated
- Columns: **Market / Model / Decision** (+ Edge / Tag hierarchy)
- Tag pills: **PLAY** `bg-edge-green` → `rgb(57, 255, 20)` on black text; **PASS** muted `bg-white/10`
- PLAY edge cells: `bg-edge-green/25` chrome with side favor
- Counts sampled: **10 PLAY · 0 LEAN · 54 PASS** (LEAN=0 expected — selective publish disables LEAN on spreads)
- Footer: `NFL tags — PASS default. Spread PLAY ≥2.5 (LEAN off). Total PLAY only 2.5–3.0 (≥3 PASS). … KEINFL: Kos Edge Index.`

---

## Hub IA smoke (`/pro/nfl/overview`)

**URL:** https://www.kosedge.com/pro/nfl/overview

Sections present:

1. **Weekly Matchups** / Weekly Slate path  
2. **Betting Desk** (KEI Lines → Edges → Props)  
3. **Props & Fantasy**  
4. **Team Intel**  
5. **Model Governance & Health**

CTA: Open live edge board / Open weekly slate — gold primary styling intact.

---

## HTTP smoke (www.kosedge.com)

| Path | HTTP |
|------|------|
| `/edge-board/nfl` | 200 |
| `/pro/nfl/overview` | 200 |
| `/pro/nfl/fair-lines` | 200 |
| `/pro/nfl/edges` | 200 |
| `/pro/nfl/props` | 200 |
| `/pro/nfl/projections` | 200 |

---

## What was *not* done (by design)

- No heavy Railway sims / densify  
- No rewrite of EdgeBoard off selective publish back to old LEAN bands (would undo Priority-1 selective publish)  
- No new Vercel deploy (production already serving polished `deploy-vercel` tip)  
- Writers/articles out of scope  

---

## Restored / confirmed artifacts

- **Look:** PLAY/LEAN/PASS color system, Edge/Tag decision hierarchy, Market (Best) vs Model (KEINFL) column chrome  
- **Behavior:** Selective publish YELLOW + `spread_play_v2_cap7` path via `nfl-publish-policy` / server tags  
- **IA:** NFL Pro hub section structure from `pro-sport-ia.ts`  

Sibling data notes (not re-verified end-to-end here): fair-lines ~167 rows, KEI/PLAY live, projections up, `MODEL_SERVICE_URL` fixed.
