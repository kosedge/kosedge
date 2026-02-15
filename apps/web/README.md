# Kos Edge – Web App

Next.js 16 application for Kos Edge Analytics.

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

## Prisma

- Generate client: `pnpm prisma:generate` (also runs on `postinstall`)
- Migrate: `pnpm prisma:migrate`
- Studio: `pnpm prisma:studio`

## Tech

- Next.js 16 (Turbopack), React 19, TypeScript
- Prisma (Postgres), NextAuth, Tailwind
