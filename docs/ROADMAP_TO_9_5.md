# Roadmap: Structure, Organization, Professionalism, Enterprise-Grade, Scalability → 9.5

This document defines what “9.5” means for each dimension and lists **concrete, ordered actions** to get there. Subscription/billing is out of scope.

---

## How to use this roadmap

- **Phases** are ordered: do Phase 1 first, then 2, then 3. Within a phase, items can be done in parallel where there are no dependencies.
- **Owner:** one person can own the whole roadmap or you can split by phase/dimension.
- **Done criteria:** each bullet is done when the change is merged and (where noted) tests/docs updated.

---

## 1. Structure → 9.5

**Target:** Clear, consistent route and layout hierarchy; no naming bugs; every route group has an explicit layout where it adds value; one security/runtime “gate” (middleware) so structure is predictable.

### 1.1 Fix naming and routing bugs

| Action | Location | Detail |
|--------|----------|--------|
| Rename route handler so Next.js picks it up | `app/(pro)/pro/activate/rout.ts` → `route.ts` | File must be named `route.ts` for App Router. Move the GET handler into `route.ts` and delete `rout.ts`. |
| Fix route segment typo | `app/(pro)/pro/[sport]/exicution/` → `execution/` | Rename folder `exicution` → `execution`. Update any `<Link href>` or `redirect()` that point to `/pro/.../exicution` to use `execution`. Search: `exicution`. |

### 1.2 Add missing layouts (optional but recommended for 9.5)

| Action | Location | Detail |
|--------|----------|--------|
| (docs) layout | Create `app/(docs)/layout.tsx` | Shared chrome for insights: e.g. wrap children with `SiteHeader` + a narrow container so insights index and `[slug]` share the same shell. Reuse existing `SiteHeader` and optionally `Container`. |
| Auth layout | Create `app/auth/layout.tsx` | Minimal layout for signin/signup/error: centered card, logo, same background as rest of app so auth pages feel part of the product. |
| Pro layout (optional) | Create `app/(pro)/pro/layout.tsx` | If you want one place for “Pro shell” (e.g. breadcrumb “Pro” or subtle nav) for `/pro`, `/pro/welcome`, and any Pro page that isn’t under `[sport]`. Otherwise skip. |

### 1.3 Single runtime “gate”: middleware

| Action | Location | Detail |
|--------|----------|--------|
| Create middleware | Create `app/middleware.ts` (or `middleware.ts` at app root) | Export a single `middleware(request)` that: (1) calls `NextResponse.next()`, (2) passes the response to `addSecurityHeaders(response)` from `@/lib/security/headers`, (3) returns that response. Do **not** add auth or Pro gating here (per your request). This gives you one place for security headers and, later, optional rate limiting. |

**Structure 9.5 checklist:** No `rout`/`exicution`; (docs) and auth have layouts; middleware applies security headers. Route groups and file names are consistent.

---

## 2. Organization → 9.5

**Target:** One source of truth for env; shared constants for URLs and cache TTLs; docs match code; API responses and errors follow one contract.

### 2.1 Single source of truth for env

| Action | Location | Detail |
|--------|----------|--------|
| Use `env` in DB client | `lib/db.ts` | Replace `process.env.DATABASE_URL` and `process.env.NODE_ENV` with `env` from `@/lib/config/env`. Keep the same fallback for DATABASE_URL if you use it in tests (or use env only and set in test setup). |
| Use `env` in Redis client | `lib/cache/redis.ts` | Replace `process.env.REDIS_URL` with `env.REDIS_URL`. |
| Use `env` in logger | `lib/logger.ts` | Replace `process.env.NODE_ENV` and `process.env.LOG_LEVEL` with `env.NODE_ENV` and `env.LOG_LEVEL`. |
| Use `env` in security headers | `lib/security/headers.ts` | Replace `process.env.NODE_ENV` with `env.NODE_ENV` for the HSTS branch. |
| Use `env` in API error handler | `lib/api/error-handler.ts` | Replace `process.env.NODE_ENV` with `env.NODE_ENV` so production/development behavior is consistent with the rest of the app. |
| Use `env` in error UIs (optional) | `app/error.tsx`, `components/error/ErrorBoundary.tsx` | Replace `process.env.NODE_ENV` with `env.NODE_ENV` for dev-only error details. (If these run only on client, ensure `env` is not imported in a way that pulls server-only code into client bundle; if in doubt, keep `process.env.NODE_ENV` here.) |
| Sentry configs | `sentry.server.config.ts`, `sentry.client.config.ts`, `sentry.edge.config.ts` | Prefer reading from `env` for `NODE_ENV` if you can do so without circular dependency; otherwise leave as-is and add a one-line comment: “Sentry reads NODE_ENV at build/runtime; env schema documents it.” |
| next.config | `next.config.ts` | Leave `process.env.VERCEL` as-is (build-time, not in app env schema). |

**Note (Edge):** `middleware.ts` runs in the Edge runtime. Do **not** import `@/lib/config/env` in middleware if that module (or its dependencies) use Node-only APIs. In `lib/security/headers.ts`, for the HSTS branch you can keep a single `process.env.NODE_ENV === "production"` check so the file stays Edge-safe, or pass a boolean from middleware (e.g. `request.nextUrl.hostname !== "localhost"`). The rest of the app should use `env` from `lib/config/env`.

### 2.2 Constants: URLs and cache TTLs

| Action | Location | Detail |
|--------|----------|--------|
| Create app constants module | Create `lib/constants.ts` | Export: `SITE_URL` (from env or default `"https://www.kosedge.com"`), `CACHE_TTL_ODDS_SEC`, `CACHE_TTL_EDGE_BOARD_SEC`, `CACHE_STALE_WHILE_REVALIDATE_SEC`. Define numeric TTLs in one place (e.g. 21600, 600, 3600) and document meaning. |
| Use SITE_URL in metadata | `app/layout.tsx` | Set `metadataBase: new URL(env.SITE_URL ?? "https://www.kosedge.com")` or use constant; add `SITE_URL` to env schema as optional if you want it configurable. |
| Use constants in API routes | `app/api/edge-board/[sport]/today/route.ts`, `app/api/edge-board/ncaam/today/route.ts`, `app/api/odds/[sport]/compare/route.ts` | Replace magic numbers for cache TTL and `cache-control` with imports from `lib/constants.ts`. |
| Odds widget base URL | `app/api/odds-widget/[sport]/route.ts` | Move `WIDGET_BASE` (and any other widget constants) into `lib/constants.ts` or `lib/odds-api.ts` and import. |

### 2.3 Docs and code alignment

| Action | Location | Detail |
|--------|----------|--------|
| Fix AUTH_SETUP.md | `apps/web/AUTH_SETUP.md` | Remove or rewrite the sentence that says “Routes under `/pro/*` are automatically protected by middleware.” State the current behavior: e.g. “Pro gating is implemented per-page; middleware does not enforce auth.” |
| Fix activate route comment | `app/(pro)/pro/activate/route.ts` (after rename) | Update the “TEMP” / “replace with Stripe” comment to be accurate (e.g. “Temporary activation for testing; not used for subscription entitlement.”). |
| README project layout | `apps/web/README.md` | Ensure the “Project layout” table includes `lib/constants.ts` and `middleware.ts` once they exist. |

### 2.4 API response contract

| Action | Location | Detail |
|--------|----------|--------|
| Standardize success | All API route handlers that return JSON | Use `jsonOk(data, init?)` from `@/lib/api/response` for 200 responses so success shape is consistent. |
| Standardize errors | All API route handlers | Use `jsonError(status, message, { code })` for error responses. Prefer wrapping handlers with `withErrorHandler` from `@/lib/api/error-handler` so thrown `ApiError` and `ZodError` become the same JSON shape; or manually call `handleApiError(error)` in catch blocks and return its result. |
| Use logError everywhere | Every API route catch block | Replace `console.error` with `logError(error, { route: "..." })` in register, odds-widget, and ncaam/today. |

**Organization 9.5 checklist:** Env only from `lib/config/env` (with noted exceptions); constants for site URL and cache TTLs; docs match behavior; all API routes use `jsonOk`/`jsonError` and `logError`.

---

## 3. Professionalism → 9.5

**Target:** Every API validates input and handles errors the same way; no raw `console.error` in routes; security headers and (optionally) rate limiting are on; UI and logging feel consistent.

### 3.1 API: validation and error handling

| Action | Location | Detail |
|--------|----------|--------|
| Wrap live-line in try/catch | `app/api/live-line/route.ts` | Wrap the handler body in try/catch; on throw, return `handleApiError(error)` or use `withErrorHandler`. Use `jsonOk` for success (already does). |
| Zod for live-line query | `app/api/live-line/route.ts` | Parse query with a small Zod schema (pregameSpread, homeScore, awayScore, minutesRemaining, optional marketSpread) and return `jsonError(400, ...)` with code `VALIDATION_ERROR` when invalid. |
| Use withErrorHandler or handleApiError | `app/api/edge-board/[sport]/today/route.ts`, `app/api/edge-board/ncaam/today/route.ts`, `app/api/odds/[sport]/compare/route.ts`, `app/api/auth/register/route.ts`, `app/api/odds-widget/[sport]/route.ts` | Either wrap the exported GET/POST in `withErrorHandler(handler)` or in the catch block call `return handleApiError(error)`. Ensure every route returns `NextResponse` from the shared helpers for errors. |
| Replace console.error with logError | `app/api/auth/register/route.ts`, `app/api/odds-widget/[sport]/route.ts`, `app/api/edge-board/ncaam/today/route.ts` | Use `logError(e instanceof Error ? e : new Error(String(e)), { route: "register" })` (and similar for others) so all API errors go through the same logger. |

### 3.2 Security and resilience

| Action | Location | Detail |
|--------|----------|--------|
| Apply security headers in middleware | Done in Structure 1.3 | Middleware calls `addSecurityHeaders(NextResponse.next())` so every response gets CSP, X-Frame-Options, etc. |
| Optional: rate limit API routes | `lib/security/rate-limit.ts` + selected routes | If Redis is available, apply rate limiting to auth (register, sign-in) and/or high-cost routes (e.g. edge-board, odds compare). Document in README that rate limiting is on when REDIS_URL is set. |

### 3.3 Code hygiene

| Action | Location | Detail |
|--------|----------|--------|
| Use ArticleLayout or remove | `components/layout/ArticleLayout.tsx`, `components/layout/Container.tsx` | If no page uses ArticleLayout, either wire it to (docs) insight pages or remove it (and document that Container is for future use). Avoids “dead” shared code. |

**Professionalism 9.5 checklist:** All API routes use shared error handling and logging; live-line and other public APIs validate input with Zod where applicable; security headers on all responses; no stray console.error in routes.

---

## 4. Enterprise-grade → 9.5

**Target:** Security headers and optional rate limiting; consistent error contract and logging; tests for critical paths; clear runbooks and structure docs.

### 4.1 Security and headers (covered above)

- Middleware applies security headers (Structure).
- Optional rate limiting when Redis is configured (Professionalism).

### 4.2 Error contract and observability

| Action | Location | Detail |
|--------|----------|--------|
| Document API error shape | `docs/API.md` or README | Add a short “Error responses” section: all JSON errors have `error: string` and optional `code: string`; 4xx/5xx use same shape. Point to `lib/api/response` and `lib/api/error-handler`. |
| Ensure request IDs where useful | `app/api/edge-board/[sport]/today/route.ts` (already has) | Other high-value or state-changing routes (e.g. register) can add an `x-request-id` header on response for support/debugging. Optional. |

### 4.3 Tests

| Action | Location | Detail |
|--------|----------|--------|
| Test error handler | Create `__tests__/lib/api/error-handler.test.ts` | Test that `handleApiError` returns correct status and body for `ApiError`, `ZodError`, generic Error, and unknown. |
| Test API response helpers | Create `__tests__/lib/api/response.test.ts` | Test `jsonError` and `jsonOk` return correct status and body shape. |
| Test one critical API route | e.g. `__tests__/api/live-line/route.test.ts` | Request with valid and invalid query params; assert 200 with expected shape and 400 with error body. |
| Test middleware (optional) | Create `__tests__/middleware.test.ts` or E2E | Assert that a request to a public page gets security headers (e.g. X-Frame-Options, CSP present). |

### 4.4 Documentation

| Action | Location | Detail |
|--------|----------|--------|
| ARCHITECTURE.md | `docs/ARCHITECTURE.md` | Add a “Security” subsection: middleware applies headers; optional rate limiting; env and secrets via single module. |
| DEPLOYMENT.md | `docs/DEPLOYMENT.md` | Mention that middleware runs on every request and list required env for production (AUTH_SECRET, DATABASE_URL, etc.) in one place. |

**Enterprise 9.5 checklist:** Error contract documented; critical API and error-handling paths tested; security and deployment documented.

---

## 5. Scalability → 9.5

**Target:** Cache and external calls are configurable and documented; structure supports adding new routes and features without clutter; no unnecessary duplication.

### 5.1 Cache and config

| Action | Location | Detail |
|--------|----------|--------|
| Centralize cache TTLs | Done in Organization 2.2 | `lib/constants.ts` holds TTLs; routes import them. Makes it easy to tune or feature-flag cache per environment. |
| Document Redis usage | `apps/web/README.md` or `docs/ARCHITECTURE.md` | One paragraph: when REDIS_URL is set, rate limiting (and any future cache) use Redis; when not set, behavior is documented (e.g. no rate limiting, or in-memory fallback if you add one). |

### 5.2 Route and feature scaling

| Action | Location | Detail |
|--------|----------|--------|
| Pro route index | Optional: add `app/(pro)/pro/[sport]/page.tsx` | If you want `/pro/ncaam` to redirect to `/pro/ncaam/overview` or show a sport landing, add a minimal page; otherwise the current “only child routes” setup is fine. Document in STRUCTURE.md that `[sport]` has no index page by design. |
| Avoid duplicate logic | Review `app/api/edge-board/ncaam/today/route.ts` vs `app/api/edge-board/[sport]/today/route.ts` | If NCAAM route is a thin wrapper that could call the same logic as [sport], consider extracting shared logic to a function in lib and both routes calling it. Reduces drift when you change cache or auth. |

### 5.3 Imports and boundaries

| Action | Location | Detail |
|--------|----------|--------|
| Barrel files (optional) | e.g. `lib/api/index.ts` | Export `jsonError`, `jsonOk`, `handleApiError`, `withErrorHandler`, `ApiError` from one place so routes can `import { jsonError, jsonOk, withErrorHandler } from "@/lib/api"`. Keeps API surface clear as you add more helpers. |
| STRUCTURE.md | `docs/STRUCTURE.md` | Add a line that new API routes should use `@/lib/api` (or `@/lib/api/response` and `@/lib/api/error-handler`) and validate input with Zod where applicable. |

**Scalability 9.5 checklist:** Cache and Redis behavior documented; shared API logic where two routes do the same thing; clear convention for new routes and imports.

---

## 6. Implementation order (phases)

### Phase 1 – Quick wins (1–2 days)

1. Rename `rout.ts` → `route.ts` and fix `exicution` → `execution`.
2. Create `lib/constants.ts` with SITE_URL and cache TTLs; use in layout and one API route as a pilot.
3. Use `env` from `lib/config/env` in `lib/db.ts`, `lib/cache/redis.ts`, `lib/logger.ts`, `lib/security/headers.ts`, `lib/api/error-handler.ts`.
4. Replace `console.error` with `logError` in register, odds-widget, ncaam/today.
5. Fix AUTH_SETUP.md and activate route comment.

### Phase 2 – Middleware and API discipline (2–3 days)

6. Add `middleware.ts` that applies `addSecurityHeaders` to `NextResponse.next()`.
7. Wire all API routes to use `jsonOk`/`jsonError` and `withErrorHandler` (or `handleApiError` in catch). Add Zod for live-line query.
8. Use constants for cache and `cache-control` in all edge-board and odds API routes.
9. Move odds-widget base URL (and any other magic strings) to constants.

### Phase 3 – Layouts and docs (1–2 days)

10. Add `app/(docs)/layout.tsx` and `app/auth/layout.tsx`.
11. Update README project layout and ARCHITECTURE/DEPLOYMENT with security and env.
12. Document API error shape in docs/API.md or README.

### Phase 4 – Tests and polish (2–3 days)

13. Add tests for error-handler and response helpers; add one API route test (e.g. live-line).
14. Optional: middleware/E2E test for security headers; optional: rate limiting on auth routes when Redis is set.
15. Optional: barrel `lib/api/index.ts`; optional: extract shared edge-board logic; optional: Pro layout.

---

## 7. Definition of “9.5” per dimension (recap)

| Dimension | 9.5 means |
|-----------|-----------|
| **Structure** | No naming bugs; (docs) and auth have layouts; middleware is the single place for security headers; route groups and file names are consistent. |
| **Organization** | One env source; shared constants for URLs and TTLs; docs match code; all API routes follow the same response/error contract. |
| **Professionalism** | Every API validates input and uses shared error handling and logging; security headers on all responses; no dead shared components without a decision. |
| **Enterprise-grade** | Security and rate limiting (when Redis is set) documented and applied; error contract documented; tests for error-handler and at least one critical API. |
| **Scalability** | Cache and Redis behavior documented; shared logic for duplicate route behavior; clear conventions for new routes and imports. |

---

## 8. Out of scope (as requested)

- Subscription, billing, Stripe, Pro gating, and paywall are **not** part of this roadmap.
- This roadmap does not change product behavior for users; it only improves structure, organization, professionalism, enterprise-grade quality, and scalability.
