# #12 GO-1c — assemble CDN Cache-Control delivery + optional cron warm (2026-09-04)

**Status:** DRAFT PR only — CoS owns squash after honesty receipts on www. Do not merge from this note.

**Prior:** GO-1 bootstrap (`data/ops/edge-board-cold-assemble-hydrate-20260904.md`). GO-1b diagnose SoT (prod probe): code sets full `PAGE_DATA_CACHE_CONTROL`; live wire showed strip; CDN HIT path still fine for budgets. HOLD GO-2. No budget moves.

## Honesty receipts (H1–H4) — GO-1b diagnose

| ID | Claim | Evidence |
| --- | --- | --- |
| **H1** | App origin sets `PAGE_DATA_CACHE_CONTROL = public, s-maxage=45, stale-while-revalidate=45` via `pageDataJsonResponse` for non-empty assemble 200 | `apps/web/lib/page-data-cache.ts`; unit + source-lock tests |
| **H2** | Live www assemble **200** returned client-visible `cache-control: public` only (**s-maxage missing**) | GO-1b probe asm2: `http=200`, `cache-control: public`, `x-vercel-cache: MISS`, ~21s TTFB |
| **H3** | CDN still cached despite strip — HIT / STALE path meets budgets | GO-1b asm3: HIT ~75ms (`age: 16`); later STALE (`age: 67`) with same bare `public` |
| **H4** | First MISS remains origin-cold (~10–25s or 504 at pageData 25s) — do **not** waive MISS forever for real users | asm1 504 ~25.3s `private, no-store`; Phase A `01` 24980 ms vs `04` 767 ms |

## Root cause (strip)

**Not** middleware / `next.config` / security headers / `force-dynamic` invent.

Vercel CDN behavior: when a Function sets **only** `Cache-Control` (with `s-maxage` / `stale-while-revalidate`), the edge **strips** those directives from the **client-visible** header before send — leaving bare `public` — while still honoring them for CDN storage. Documented:

> If you set `Cache-Control` without a `CDN-Cache-Control`, the Vercel CDN strips `s-maxage` and `stale-while-revalidate` from the response before sending it to the browser.

SoT: https://vercel.com/docs/caching/cdn-cache

## Fix (A — primary)

`pageDataCacheHeaders` now sets matching:

- `Cache-Control: PAGE_DATA_CACHE_CONTROL` (or `private, no-store`)
- `CDN-Cache-Control: <same>`

so the full 45s band survives on the wire for non-empty 200s. Empty / 503 / 504 stay no-store on both. As-of remains book vintage (never `Date.now()`). TTL stays **45** (CoS: no TTL >60).

## Optional warm (B — cheap)

Vercel Cron every minute → `GET /api/cron/warm-page-data` (`maxDuration` 40):

- Warms NFL `assemble?slate=week1` + CFB `assemble?week=1`
- Auth: `CRON_SECRET` Bearer and/or `x-vercel-cron`
- Rate-limit skip for cron/warm headers
- **Does not invent SoT** — HTTP GET existing assemble only

## Post-merge honesty (www)

After CoS squash + Vercel promo, re-probe:

1. Assemble 200 `Cache-Control` **and** `CDN-Cache-Control` include `s-maxage=45`
2. MISS then HIT within 45s band
3. Cron warm path 200 without inventing rows / as-of

HOLD GO-2 until those receipts land.
