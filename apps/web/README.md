# Kos Edge Web

Next.js 16 app for Kos Edge Analytics: public site, Pro hub, edge board, odds, and insights.

## Run locally

```bash
# From repo root (pnpm workspace)
pnpm install
pnpm dev
# Or from this app
cd apps/web && pnpm dev
```

- Dev server: [http://localhost:3000](http://localhost:3000)
- Optional: `pnpm dev:local` runs on `http://127.0.0.1:3000`

## Environment variables

See [Conventions](#conventions) for required vs optional.

| Variable                                       | Required          | Description                                                         |
| ---------------------------------------------- | ----------------- | ------------------------------------------------------------------- |
| `DATABASE_URL`                                 | Yes (run + build) | PostgreSQL connection string                                        |
| `AUTH_SECRET`                                  | Yes (production)  | NextAuth secret (min 32 chars)                                      |
| `NODE_ENV`                                     | No                | `development` \| `test` \| `production`                             |
| `ODDS_API_KEY`                                 | No                | [The Odds API](https://the-odds-api.com) key (NCAAM etc.)           |
| `ODDS_WIDGET_ACCESS_KEY`                       | No                | Odds widget embed (server-only)                                     |
| `MODEL_SERVICE_URL`                            | No                | Upstream model service for edge board                               |
| `INTERNAL_API_SECRET`                          | No                | Secret for server-to-server edge board calls                        |
| `REDIS_URL`                                    | No                | Redis URL; when set, rate limiting uses Redis (multi-instance safe) |
| `LOG_LEVEL`                                    | No                | `debug` \| `info` \| `warn` \| `error`                              |
| `NEXT_PUBLIC_SENTRY_DSN` / `SENTRY_AUTH_TOKEN` | No                | Sentry error tracking                                               |

Create `.env.local` from `.env.example` (if present) and set at least `DATABASE_URL` and `AUTH_SECRET` for full auth.

## Tests

```bash
# Unit / integration tests (Vitest)
pnpm test

# With UI
pnpm test:ui

# Single run with coverage
pnpm test:coverage
```

- Tests live in `__tests__/` and next to code as `*.test.ts` / `*.spec.ts`.
- Coverage is reported in `coverage/`; CI can enforce thresholds (see `vitest.config.ts`).

## Build & deploy

```bash
pnpm build
pnpm start
```

- Output: standalone in `.next` (see `next.config.ts`).
- Production: set `DATABASE_URL`, `AUTH_SECRET`, and any optional env on the host or in your deployment platform.

## Conventions

- **Prisma client**: Import from `#prisma` (path alias in `tsconfig.json` and `vitest.config.ts` to `src/generated/prisma`). Use `#prisma` in app code; avoid `@/src/generated/prisma`.
- **API errors**: Use `withErrorHandler(handler)` and throw `ApiError(statusCode, message, code?, details?)` for consistent JSON and logging.
- **Logging**: Use `logError` / `logInfo` from `@/lib/logger`; avoid `console.error` in API and server code.
- **Auth**: Pro gating via `isProUser()` and `hasRole()` from `@/lib/auth/pro`; session from `auth()` in `@/lib/auth`.

## Project layout

- `app/` — Next.js App Router (routes, layouts, pages)
- `components/` — React components (layout, auth, error)
- `lib/` — Auth, DB, API helpers, security, cache, logger
- `prisma/` — Schema and migrations (client generated into `src/generated/prisma`)
- `__tests__/` — Vitest tests

See [CODE_REVIEW.md](./CODE_REVIEW.md) for architecture notes and improvement history.
