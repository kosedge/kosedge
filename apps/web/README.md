# Kos Edge – Web App

Next.js 16 application for Kos Edge Analytics. Enterprise-grade structure: centralized env validation, consistent API responses, and clear project layout for scalability.

## Running locally

**Always run from the monorepo root** (`/kosedge`), not from `apps/web`:

```bash
# From repo root: install deps (required after clone or if you see "next/dist/bin/next" missing)
pnpm install

# Start dev server on port 3000
pnpm dev:web:3000
```

One-shot (install + start):

```bash
pnpm bootstrap:web
```

From `apps/web` you can run:

```bash
pnpm dev          # or: pnpm dev -- --port 3000
pnpm dev:webpack  # without Turbopack (use if Turbopack has resolution issues)
```

## Deploy (Vercel)

1. **Root Directory (required for monorepo):**
   - Open your project on [Vercel Dashboard](https://vercel.com/dashboard).
   - Go to **Settings** (sidebar) → **Build and Deployment** (or **Build & Development**).
   - Scroll down to the **Root Directory** section.
   - Click **Edit**, enter **`apps/web`**, then **Save**.
2. **Framework Preset:** Next.js (auto-detected from `vercel.json`).
3. Install and build run from monorepo root via `apps/web/vercel.json`:
   - **Install:** `cd ../.. && pnpm install --frozen-lockfile`
   - **Build:** `cd ../.. && pnpm run build:web`
4. **Lockfile:** Keep `pnpm-lock.yaml` at repo root in sync. After changing any `package.json` in the repo, run `pnpm install` (or `pnpm install --lockfile-only`) at repo root and commit the updated lockfile so Vercel installs succeed.
5. Node 20 is used (`.nvmrc` and `engines` in `package.json`).

## Project layout (scalability)

| Area | Path | Purpose |
|------|------|---------|
| App routes | `app/` | Next.js routes, layouts, pages |
| API | `app/api/` | Route handlers; use `jsonOk`/`jsonError` from `lib/api/response.ts` and `handleApiError`/`withErrorHandler` from `lib/api/error-handler.ts`; use `logError` instead of `console.error` |
| Config | `lib/config/env.ts` | Single env source (Zod); not imported in Edge middleware |
| Constants | `lib/constants.ts` | SITE_URL, cache TTLs, odds-widget base URL; used by layout and API routes |
| Shared lib | `lib/` | Auth, DB, cache, logger, live-line, kei-lines, etc. |
| Data (static) | `data/processed/` | Excluded from serverless bundle via `next.config` |
| Contracts | `packages/contracts` | Shared types (e.g. EdgeBoard) across services |

**Redis:** When `REDIS_URL` is set, Redis-backed features (e.g. rate limiting when implemented) use it. When not set, the app runs without Redis-dependent features. See `docs/ARCHITECTURE.md`.

## Tests

- From repo root: `pnpm test:web` (runs web app tests via the workspace).
- From `apps/web`: `pnpm test` or `pnpm run test run` (Vitest is launched via `scripts/run-vitest.mjs`, which resolves the local `vitest` CLI from this package's dependencies; no global install required).

## Prisma

- Generate client: `pnpm prisma:generate` (also runs on `postinstall`)
- Migrate: `pnpm prisma:migrate`
- Studio: `pnpm prisma:studio`

## Tech

- Next.js 16 (Turbopack), React 19, TypeScript
- Prisma (Postgres), NextAuth, Tailwind
