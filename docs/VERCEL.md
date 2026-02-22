# Vercel deployment

Use this setup for reliable builds and to avoid "failed to load" after deploy.

## Recommended (repository root as Root Directory)

1. In Vercel Project Settings → **General**:
   - **Root Directory**: leave **empty** (use the repository root).

2. **Build & Development Settings**:
   - **Framework Preset**: Next.js
   - **Install Command**: `pnpm install --frozen-lockfile`
   - **Build Command**: `pnpm run build:web`
   - **Output Directory**: leave default (not used when Root Directory is repo root; Next.js output is under `apps/web/.next`).

3. **Environment variables** (Settings → Environment Variables):
   - `DATABASE_URL` — required for auth. For build-only you can use a dummy: `postgresql://build:build@localhost:5432/build`.
   - `AUTH_SECRET` — required in production (min 32 characters).
   - `ODDS_API_KEY` — for live Edge Board data ([the-odds-api.com](https://the-odds-api.com)).
   - `ODDS_API_KEY_BACKUP` — optional; used when the primary key is rate-limited.

## If you use Root Directory = `apps/web`

- **Install Command**: `pnpm install --frozen-lockfile`
- **Build Command**: `pnpm run build`

pnpm will resolve the workspace from the cloned repo. Ensure `DATABASE_URL` and `AUTH_SECRET` are set so Prisma and NextAuth work at build/runtime.

## Troubleshooting

- **Build fails with "Cannot find module"**: Use repo root as Root Directory and Build Command `pnpm run build:web` so workspace dependencies (e.g. `@kosedge/contracts`) are installed and linked.
- **Empty env vars**: The app coerces empty strings to `undefined` for optional env vars (see `lib/config/env.ts`), so Vercel’s empty placeholders will not break the build.
- **Edge Board shows no data**: Add `ODDS_API_KEY` (and optionally `ODDS_API_KEY_BACKUP`) in Vercel env; redeploy.
