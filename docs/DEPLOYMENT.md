# Deployment

Guidance for deploying the Kos Edge web app (e.g. to Vercel).

## Middleware

Middleware runs on **every request** (except static files and `_next` internals). It applies security headers only; it does not perform auth or Pro gating. Ensure the middleware matcher in `apps/web/middleware.ts` stays in sync with any new static asset patterns so non-HTML routes are not unnecessarily run through middleware.

## Required and optional environment variables

Set these for production (and as needed for staging):

| Variable | Required | Purpose |
|----------|----------|---------|
| `AUTH_SECRET` | Yes (for auth) | NextAuth; min 32 chars. Generate with `openssl rand -base64 32`. |
| `DATABASE_URL` | Yes (for DB) | PostgreSQL connection string for Prisma. |
| `NODE_ENV` | Set by platform | Usually `production`; app reads from `lib/config/env`. |
| `SITE_URL` | Optional | Canonical site URL for metadata and redirects; defaults to `https://www.kosedge.com` if unset. |

Optional (feature-dependent):

- **Auth / OAuth:** `AUTH_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
- **Internal APIs:** `INTERNAL_API_SECRET`, `MODEL_SERVICE_URL`
- **Odds / widget:** `ODDS_API_KEY`, `ODDS_API_KEY_BACKUP`, `ODDS_WIDGET_ACCESS_KEY`
- **Redis:** `REDIS_URL` – when set, enables Redis-backed features (e.g. rate limiting if implemented)
- **Error tracking:** `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_AUTH_TOKEN`
- **Logging:** `LOG_LEVEL` (e.g. `info`, `debug`)

Build-time only (not in app env schema): `VERCEL`, etc.

## Web app root and build

For monorepo deploys (e.g. Vercel), set **Root Directory** to `apps/web`. Install and build from repo root as documented in `apps/web/README.md` (e.g. `pnpm install`, `pnpm run build:web`) so workspace dependencies resolve correctly.
