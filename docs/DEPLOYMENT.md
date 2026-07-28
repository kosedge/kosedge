# Deployment

Guidance for deploying Kos Edge: **Vercel** (web), **Railway** (model service), and **GitHub** (source + CI).

## Phone / Cursor Cloud: make Vercel, Railway, and GitHub talk

Use this when driving work from [cursor.com/agents](https://cursor.com/agents) or the Cursor mobile app.

### Already connected

- **GitHub ↔ Cursor Cloud**: this repo runs cloud agents from `kosedge/kosedge`.
- **GitHub ↔ Vercel**: production/preview Environments on the repo show Vercel is linked and auto-deploys.

### You still need to do (once)

1. **Railway ↔ GitHub**
   - Open [railway.app](https://railway.app) → New Project → Deploy from GitHub → `kosedge/kosedge`.
   - Service settings:
     - Root Directory: `/services/model-service`
     - Config File: `/services/model-service/railway.toml`
   - Generate a public domain; copy the HTTPS URL.
2. **Vercel ↔ Railway**
   - In Vercel project env vars, set:
     - `MODEL_SERVICE_URL=https://<your-railway-domain>`
     - `INTERNAL_API_SECRET=<same value as Railway>`
   - On Railway, set the same `INTERNAL_API_SECRET` plus any DB/Redis vars the model service needs.
3. **Cursor Cloud secrets** (so phone agents can deploy/inspect)
   - [Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents): add `VERCEL_TOKEN`, `RAILWAY_TOKEN`, and optionally `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `RAILWAY_SERVICE_ID`, `MODEL_SERVICE_URL`, `INTERNAL_API_SECRET`.
4. **Optional GitHub Actions Railway deploy**
   - Repo secrets: `RAILWAY_TOKEN`, `RAILWAY_SERVICE_ID`
   - Repo variable: `ENABLE_RAILWAY_DEPLOY=true`
5. **Vercel MCP (desktop once)**
   - Authenticate the Vercel MCP server in Cursor desktop; phone-only agents use the CLI + `VERCEL_TOKEN` instead.

Repo helpers: `.cursor/environment.json`, `scripts/setup-cloud-tooling.sh`, `AGENTS.md`.

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
