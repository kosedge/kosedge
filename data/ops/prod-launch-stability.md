# Production launch stability — frequent deploys

How we keep **www.kosedge.com** up through many daily/weekly Vercel deploys without leaving users on a blank black screen.

## Production truth

| Layer | Source of truth |
|-------|-----------------|
| Vercel web (`kosedge`) | Branch **`deploy-vercel`** only |
| Railway model-service | Branch `restore-working-ui` |
| Project | `prj_C6AKSLK2gHV3G9A6TI5lml6MHIJe` / team `team_hmIaPkOAqXs6gr3Yt4pyEVqi` |

Never point Vercel Production Branch at `restore-working-ui`.

## Why “black screen” happens

Site chrome uses near-black `#070a0f`. Any failure that clears the React tree looks like a pure black void:

1. **Stale tabs after redeploy (most common under rapid ship)** — HTML/`_next/static/chunks/*` hashes change; old clients throw `ChunkLoadError` / “Failed to fetch dynamically imported module”.
2. **Client render crash** — uncaught error in a client island; without a visible boundary you get black.
3. **Broken static assets** — e.g. case-sensitive logo path `/Brand/` vs `/brand/` (Linux/Vercel).
4. **Upstream hang** — SSR waiting on Railway/Odds without timeouts (mitigated via `upstreamFetch`).

## Built-in mitigations (apps/web)

| Control | Where |
|---------|--------|
| One-shot reload on chunk/import failure | `components/DeploymentRecovery.tsx` (root layout) |
| Visible loading (not void) | `app/loading.tsx`, `app/(pro)/loading.tsx` |
| Inline-styled error UI (works if CSS chunk missing) | `global-error.tsx`, `error.tsx`, `BootShell` |
| React error boundary | `components/error/ErrorBoundary.tsx` |
| Brand path case safety | `/brand/*` assets + `/Brand/:path*` → `/brand/:path*` redirect + `public/Brand` copies |
| Immutable hashed assets | `Cache-Control` on `/_next/static/*` |
| Upstream timeouts | shared `upstreamFetch` (see prod-stack-health notes) |

## Post-deploy SOP (every production ship)

1. Confirm Vercel deployment **Ready** on `deploy-vercel` and aliased to `www.kosedge.com`.
2. Run smoke:

```bash
bash scripts/prod-smoke.sh https://www.kosedge.com
```

Must pass: `/`, `/pro/nfl/overview`, `/pro/nfl/slate/today`, `/edge-board/nfl`, `/api/ping`, logo paths.

3. Optional browser check (Playwright/Puppeteer): homepage + NFL overview show logo/nav text; no uncaught pageerrors blanking the root.
4. Railway sanity (if pages pull model data):

```bash
curl -sS --max-time 15 "$MODEL_SERVICE_URL/health"
curl -sS --max-time 15 "$MODEL_SERVICE_URL/health/db"
```

5. Record deploy id + SHA in ops notes when investigating incidents.

## Operator checklist when a user reports black screen

1. Fresh private window → does content render?
   - **Yes** → almost certainly stale tab / chunk mismatch → hard refresh once; confirm `DeploymentRecovery` is in the current deploy.
   - **No** → capture HTML (`curl`), console, failed `/_next/static` URLs, Vercel runtime logs.
2. Compare production SHA vs `origin/deploy-vercel`.
3. Re-run `scripts/prod-smoke.sh`.
4. Do **not** accept “works if you hard refresh” as the only fix — keep chunk recovery + visible boundaries shipped.

## Deploy cadence guidance

- Prefer fewer, larger production deploys over dozens of tiny ones in an hour.
- Preview deploys are fine; promote one Ready build to production aliases.
- After merge to `deploy-vercel`, wait for Ready before further force-pushes that invalidate chunks again.
