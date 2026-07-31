# Prod stack health — 2026-07-31

## Verdict

**www.kosedge.com is live on Vercel production** (`deploy-vercel` tip). DNS, TLS, Railway model-service health, and core Pro routes respond. User-reported “will not load” was **not** a hard outage from our probes; the real risks were **unbounded upstream waits** (Odds API + Railway) that can make Edge Board / Slate / Overview feel hung when an upstream stalls, plus a few **404 entry paths**.

## Status table

| Layer | Status | Evidence |
|-------|--------|----------|
| **Vercel** | OK | Project `kosedge`, production branch `deploy-vercel`, latest Ready; aliases `www.kosedge.com`, `kosedge.com`, `kosedge.vercel.app` |
| **Railway** | OK | `model-service-production-e253.up.railway.app` `/health` + `/health/db` 200; `/nfl/fair-lines?days_ahead=200` returns ~241 joined lines (~1.3s) |
| **GitHub** | OK tip / noisy CI | `origin/deploy-vercel` matches production SHA; `pr-check.yml` only triggers on `pull_request` so push runs show “workflow file issue” (does not block Vercel Git deploy) |
| **DNS** | OK | `www` + apex → `cname.vercel-dns.com` / Vercel IPs; apex redirects to www |
| **Page load** | OK (hardened) | `/` ~100–200ms TTFB; `/pro/nfl/overview` ~0.8s; `/edge-board/nfl` ~2.5s; `/pro/nfl/slate/today` ~1.4s |

## Immediate probe results (agent, 2026-07-31 ~16:33–16:40 UTC)

| URL | HTTP | TTFB | Notes |
|-----|------|------|-------|
| `https://www.kosedge.com/` | 200 | ~0.11s | TLS OK, Vercel, HTML ~35KB |
| `https://kosedge.com/` | 200 | ~0.26s | Redirect → www |
| `https://www.kosedge.com/pro/nfl/overview` | 200 | ~0.8s | Overhaul markers present |
| `https://www.kosedge.com/api/ping` | 200 | ~0.08s | `{"ok":true}` |
| `https://www.kosedge.com/edge-board/nfl` | 200 | ~2.5s | Content (PLAY/LEAN/PASS) present |
| `https://www.kosedge.com/pro/nfl/slate` | **404 → fixed** | — | No index route; now redirects to `/today` |
| Railway `/health` | 200 | ~50ms | `{"status":"ok"}` |
| Railway `/nfl/fair-lines` (default 14d) | 200 | ~1.1s | `count:0` (season open outside window) |
| Railway `/nfl/fair-lines?days_ahead=200` | 200 | ~1.3s | `count:241`, market join OK |

## Root cause / failure modes

1. **Hang risk (primary code fix):** Several server fetches had **no timeout** (`odds-api`, `edge-board-tonight`, `nfl-data-freshness`, preseason odds) or **60s** caps (`nfl-fair-lines`, MLB boards). A slow Odds API or cold Railway could hold SSR until the platform killed the function → browser “never loads.”
2. **404 aliases:** `/pro/nfl/slate`, `/pro/nfl/boards`, `/pro/nfl/edge-board` returned Next 404; nav uses `/pro/nfl/slate/today` and `/edge-board/nfl`, but typed/bookmarked paths looked “broken.”
3. **Not the issue this time:** Wrong production branch (confirmed `deploy-vercel`), domain on wrong project, Railway down, middleware/paywall blocking `/pro/*` (proxy only rate-limits `/api/*`).
4. **Noise:** GitHub `PR Checks` on push to `deploy-vercel` fails immediately (workflow `on: pull_request` only). Vercel still auto-deploys from Git.

## Fixes shipped

- Shared `upstreamFetch` with 8s / 12s / 20s budgets + graceful empty fallbacks.
- Odds API, fair-lines, MLB boards, freshness banner, edge-board tonight/page, preseason odds all bounded.
- NFL Edge Board assembly **parallelizes** Odds + fair-lines.
- Redirects: `/pro/nfl/slate` → `today`, `/pro/nfl/boards` + `/pro/nfl/edge-board` → `/edge-board/nfl`.

## Production pointers

- Project: `prj_C6AKSLK2gHV3G9A6TI5lml6MHIJe` (team `kos-edge-analytics-projects`)
- Prod branch: `deploy-vercel`
- Model service: `https://model-service-production-e253.up.railway.app`
- Env present on Vercel prod: `MODEL_SERVICE_URL`, `INTERNAL_API_SECRET`, `ODDS_API_KEY`, `DATABASE_URL` (no `REDIS_URL`)
