# NFL Pro Premium Readiness Report

**Date:** 2026-07-31 (ALL LIVE pass)  
**Branch:** `cursor/nfl-pro-all-live-0861` → `deploy-vercel`  
**Production:** https://www.kosedge.com  
**Prior score:** 91/100 (P0 close-out)  
**This pass:** Sync audit + shippable P1 close-out + model-service source sync

---

## 1. How close we are

**Score: 96 / 100 — ALL LIVE for preseason week 1.**

**Verdict:** Every primary NFL Pro navigation surface on www returns 200 with real content. Model board is sane (DAL@NYG `spread_home` **+1.88**, market +2.5). This pass closes remaining empty-execution gap, ships a dedicated player preview index, surfaces writer camp intel + fresh ESPN injury headlines on Camp/Injuries, syncs model-service sanity fixes onto `deploy-vercel` source, and polishes slate mobile layout. Remaining −4 are true follow-ons: native PRE game sims on Railway, official 2026 weekly injury designations (still prior-week fallback in intel tables), and owned full news-break markdown posts beyond preview-sourced camp intel.

---

## 2. ALL LIVE checklist

| URL | Status | Notes |
| --- | --- | --- |
| [/pro/nfl](https://www.kosedge.com/pro/nfl) | **OK** | Hub + Camp Desk strip |
| [/pro/nfl/previews](https://www.kosedge.com/pro/nfl/previews) | **OK** | 32/32 index |
| [/pro/nfl/previews/KC](https://www.kosedge.com/pro/nfl/previews/KC) | **OK** | Full article |
| [/pro/nfl/previews/DAL](https://www.kosedge.com/pro/nfl/previews/DAL) | **OK** | Full article |
| [/pro/nfl/slate/today](https://www.kosedge.com/pro/nfl/slate/today) | **OK** | PRE market+camp-ref + REG |
| [/pro/nfl/camp](https://www.kosedge.com/pro/nfl/camp) | **OK** | Headlines + writer intel + injury strip + 32 beats |
| [/pro/nfl/fair-lines](https://www.kosedge.com/pro/nfl/fair-lines) | **OK** | Week 1 board incl. DAL@NYG +1.88 |
| [/pro/nfl/edges](https://www.kosedge.com/pro/nfl/edges) | **OK** | 369 thresholded edges |
| [/pro/nfl/standings](https://www.kosedge.com/pro/nfl/standings) | **OK** | Labeled 2025 final fallback |
| [/pro/nfl/stats](https://www.kosedge.com/pro/nfl/stats) | **OK** | Labeled sim strength |
| [/odds/nfl](https://www.kosedge.com/odds/nfl) | **OK** | Rows > 0 (multi-book compare) |
| [/pro/nfl/teams](https://www.kosedge.com/pro/nfl/teams) | **OK** | 32-team directory |
| [/pro/nfl/teams/KC](https://www.kosedge.com/pro/nfl/teams/KC) | **OK** | Preview wired |
| [/pro/nfl/execution](https://www.kosedge.com/pro/nfl/execution) | **OK** | Fixed empty window (days_ahead 120) |
| [/pro/nfl/injuries](https://www.kosedge.com/pro/nfl/injuries) | **OK** | Camp injury headlines + labeled table |
| [/pro/nfl/player-previews](https://www.kosedge.com/pro/nfl/player-previews) | **OK** | New MVP/OPOY + skill outlook index |
| Model DAL@NYG | **OK** | +1.88 vs market +2.5 (target +1.8..+2.5) |

---

## 3. Sync audit (Phase 1)

| Item | Result |
| --- | --- |
| `origin/deploy-vercel` tip (pre-pass) | `f24ce484` — P0 PRE camp-ref + Camp Desk |
| Vercel production | `dpl_63wE7fNzQX6vFy7f4asEMijcS2qz` @ `f24ce484` (Ready) |
| `nfl-second-order-edge` unique | Model sanity blend/abbr/canary commits + deploy scripts |
| PR #26 | **MERGED** into deploy-vercel |
| PR #25 | Open vs `nfl-second-order-edge`; content already on deploy-vercel via cherry-picks — close as superseded |
| Railway fair-lines | LIVE — 168 lines @ `days_ahead=120`; DAL@NYG sane |
| Railway CLI token in this agent | Unauthorized — no redeploy required (board already on canary `sanity-fix-20260730i-live-odds-blend`) |

---

## 4. What shipped this pass

1. **Model-service source sync** onto deploy-vercel (live odds blend, abbr pack lookup, W1–4 supervised skip, deploy script, ops reports). Railway already serving the fixed board — redeploy skipped (CLI auth + already-correct canary).  
2. **Execution Monitor** — `days_ahead` 21→120 + Week 1–2 fallback so preseason calendar no longer shows 0 games.  
3. **Training Camp Desk** — writer camp intel from all 32 season-preview sources/angles + ESPN injury/availability strip.  
4. **Injuries page** — fresh public ESPN injury headlines above the labeled intel table + Camp Desk CTA.  
5. **Player Previews** — `/pro/nfl/player-previews` (MVP/OPOY + half-PPR skill ladder); hub IA + desk footer wired; `/pro/nfl/players` redirect.  
6. **Slate mobile polish** — abbr titles on small screens, stacked market/ref grid, tighter padding.  
7. File-tracing includes for camp/injuries preview content.

---

## 5. What could not go live (and why)

| Item | Why |
| --- | --- |
| Native PRE game sims | Model SQL/schedule still REG-only; camp-ref + market path is the honest premium substitute |
| Official 2026 weekly injury designations | `/nfl/intel/injuries` still lands on latest prior week (2025 W18); public ESPN camp headlines fill the gap |
| Full writer news-break markdown posts | Templates exist; no separate break corpus beyond preview-sourced camp intel |
| Railway redeploy from this agent | `RAILWAY_TOKEN` unauthorized for CLI; board already verified sane — no functional gap |
| External prediction-market venues | P2 — model futures desk remains |

---

## 6. Score bridge (91 → 96)

| Item | Delta |
| --- | --- |
| Execution empty → Week 1 board | +1 |
| Player preview index live | +1 |
| Writer camp intel (32) + injury headlines | +2 |
| Slate mobile / nav polish | +1 |
| Held for native PRE sims + official 2026 injury weeks | −4 from 100 |

---

## 7. Production pins

- **Vercel project production branch:** `deploy-vercel` (never `restore-working-ui`)
- **Model service:** `https://model-service-production-e253.up.railway.app`
- **worker_build_id (last verified):** `sanity-fix-20260730i-live-odds-blend` (from prior Railway canary; DAL@NYG still +1.88)
