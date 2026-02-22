# Kos Edge Web — Code Review

**Scope:** `apps/web` (Next.js 16, App Router, Prisma, NextAuth).  
**Goal:** Enterprise-grade, scalable, professional; long-term maintainability.

---

## Overall rating: **7.5 / 10**

**Summary:** Strong foundation (schema, auth, lib structure, types). Implemented: register route with `withErrorHandler` + `ApiError`, all `console.error` → `logError`, unified `#prisma` alias, shared `ErrorScreen` component, `apps/web` README, Redis-backed rate limiter when `REDIS_URL` is set, rate-limit tests, coverage thresholds and CI step. Some existing tests (register mocks, UserMenu, pro.test) still need fixes for full green CI.

---

## Category ratings (1–10)

| Area | Score | Notes |
|------|--------|--------|
| **Architecture & structure** | 8 | Clear app/(pro), (docs), lib/, components/. Route groups and Prisma schema are well thought out. |
| **Security** | 6.5 | Sanitize, rate-limit, CSP/headers **now applied** via `proxy.ts`. Register still uses `console.error`; use logger for consistency. |
| **Data & API** | 7.5 | Prisma + Zod + contracts package. Env validated at startup. In-memory cache in routes is fine for single-instance; document or move to Redis for scale. |
| **Auth** | 7.5 | NextAuth + JWT, role/subscription in DB, `isProUser`/`hasRole` used correctly. Pro activation still cookie-based temp hack. |
| **Error handling & observability** | 7 | Central `ApiError` + `handleApiError`, Sentry, pino logger. Some routes still use `console.error` and don’t use `withErrorHandler`. |
| **Testing** | 6 | Vitest + RTL, good register and pro/auth tests. No middleware or API integration tests; coverage not enforced. |
| **Consistency & polish** | 6.5 | Typo fixes (activate route, execution path). Import mix of `@/` and `@/src/generated/prisma`. Some duplication (error UI). |
| **Documentation** | 7 | `docs/API.md` is useful. Inline comments where it matters. Missing: ADR or “how we structure X,” runbooks. |
| **Scalability** | 7 | Standalone build, optional Redis, DB connection handling. Rate limiter is in-memory (per-instance); need Redis-backed for multi-instance. |

---

## What’s already strong

- **Prisma schema:** Clear domains (auth, sports, markets, writeups), indexes and relations documented.
- **Env:** Zod-validated in `lib/config/env.ts`; optional vs required is explicit.
- **Lib layout:** `lib/auth`, `lib/security`, `lib/cache`, `lib/api` are easy to find and extend.
- **Pro gating:** `isProUser()` and redirect-on-pro in `/pro` page is the right pattern.
- **Contracts:** Shared types in `@kosedge/contracts` keep API and UI in sync.
- **Next config:** `poweredByHeader: false`, standalone output, sensible Turbopack root.

---

## Critical fixes (done or do next)

### 1. **Activate route was broken** — fixed

- **Was:** `app/(pro)/pro/activate/rout.ts` (typo). Next only recognizes `route.ts`, so `/pro/activate` did nothing.
- **Done:** Added `app/(pro)/pro/activate/route.ts` and removed `rout.ts`.

### 2. **Execution route typo** — fixed

- **Was:** `exicution` in path and overview link.
- **Done:** New `app/(pro)/pro/[sport]/execution/page.tsx`, link in overview updated to `execution`, old `exicution` page removed.

### 3. **Wire security and rate limiting** — fixed

- **Was:** `lib/security/rate-limit.ts` and `lib/security/headers.ts` were never used.
- **Done:** `proxy.ts` (Next 16’s middleware) now calls `rateLimit(request)` and `addSecurityHeaders(response)` so API rate limits and CSP/headers apply to all matching requests.

### 4. **Register route: logging and error handling**

- **Issue:** Uses `console.error` and manual try/catch instead of `logError` and `handleApiError` / `withErrorHandler`.
- **Recommendation:** Use `withErrorHandler` (or equivalent) and `logError` so behavior matches other APIs and docs.

---

## Suggestions for “damn, that’s good” tier

### Structure & consistency

- **Prisma imports:** Prefer one convention. Either:
  - `@/src/generated/prisma` everywhere, or
  - Add a path alias like `#prisma` → `./src/generated/prisma` and use that in app code so generated code is clearly namespaced.
- **Error UI:** `error.tsx` and `global-error.tsx` share a lot of markup. Extract a shared `ErrorLayout` or component to avoid drift.
- **API route pattern:** Standardize on:
  - `withErrorHandler(handler)` (or a small wrapper that does rate-limit + error handling),
  - `logError` / structured logger instead of `console.error`,
  - Consistent JSON error shape (you already have this in `handleApiError`).

### Security & production

- **Env:** For production, consider splitting:
  - “Required at boot” (e.g. `AUTH_SECRET`, `DATABASE_URL`) — fail fast with a clear message if missing.
  - “Optional features” (e.g. `ODDS_API_KEY`, `REDIS_URL`) — keep optional with Zod.
- **Rate limiting:** For multiple instances, use Redis-backed rate limiter (e.g. `rate-limiter-flexible` with Redis store) and wire it in middleware.
- **CSP:** Tighten when possible (e.g. reduce `unsafe-inline` / `unsafe-eval` as tooling allows).

### Testing & quality

- **Middleware test:** Add a small test that asserts middleware applies rate limit and security headers (e.g. by calling the middleware with mock request/response).
- **Coverage:** Add a CI step that fails if coverage drops below a threshold (e.g. 70% for `lib/` and `app/api/`).
- **E2E:** One or two Playwright (or similar) flows for critical paths (e.g. signup → signin → pro redirect) would round out “enterprise grade.”

### Data & performance

- **In-memory caches:** `sportCache` and `compareCache` in API routes work for a single instance. Document that they are per-process and, when you scale horizontally, move to Redis (you already have `getCached`/`setCache`).
- **DB:** Consider connection pooling (e.g. PgBouncer) and, if you add read replicas, a pattern for read-only vs write connections.

### Docs & onboarding

- **README in `apps/web`:** Short “how to run, env vars, test, deploy” so a new engineer can go from clone to running app quickly.
- **Architecture decision or “conventions” doc:** One-pager on “how we do auth,” “how we do API errors,” “where types live” so structure stays consistent as the team grows.

---

## What was implemented (this pass)

1. **Register route** — uses `withErrorHandler(registerHandler)` and throws `ApiError` for 400/409; errors logged via `handleApiError`.
2. **Logging** — all `console.error` in API routes and `lib/cache/redis.ts` replaced with `logError`.
3. **Prisma alias** — `#prisma` path alias in `tsconfig.json` and `vitest.config.ts`; all imports updated; documented in README Conventions.
4. **Shared error UI** — `components/error/ErrorScreen.tsx`; `error.tsx` and `global-error.tsx` use it.
5. **README** — `apps/web/README.md` with run, env, test, build/deploy, and Conventions.
6. **Redis rate limiter** — when `REDIS_URL` is set, `lib/security/rate-limit.ts` uses `RateLimiterRedis` (lazy-init); otherwise in-memory.
7. **Tests & coverage** — `__tests__/lib/security/rate-limit.test.ts`; coverage thresholds (30%) in `vitest.config.ts`; CI step “Web test coverage (enforce thresholds)”. Vitest setup JSX fixed (use `React.createElement` in `.ts`).
8. **Vercel reliability** — `docs/VERCEL.md`, env empty-string coercion in `lib/config/env.ts`, `lib/data-paths.ts`, root script `vercel-build`.

## What to change next (priority order)

1. **Fix existing test mocks** — register.test (prisma mock shape), UserMenu.test (session/link mocks), pro.test (next-auth/server in vitest).
2. **Raise coverage thresholds** — after tests are green, consider 50%+ and add more unit tests for `lib/` and API routes.
3. **Optional:** E2E (Playwright) for signup → signin → pro redirect.

---

## Summary

The codebase is in good shape for a company product: clear domains, sensible tech choices, and real security/observability building blocks. The main gaps are **wiring** (middleware, consistent error/logging in routes) and **consistency** (imports, error UI, logging). The two bugs (activate route name, execution path) are fixed. Implementing the “critical” and “change first” items would make an engineer open the repo and think “damn, that’s good.”
