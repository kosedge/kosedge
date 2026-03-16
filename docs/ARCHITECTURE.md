# Architecture

High-level structure and security for the Kos Edge monorepo and web app.

## Apps and packages

- **apps/web** – Next.js app (App Router). Reads env from `lib/config/env`, applies security headers in middleware, and exposes API routes that follow the shared contract (see [API.md](./API.md)).
- **packages/contracts** – Shared types and schemas (e.g. EdgeBoard) used by the web app and any backend services.

## Security

- **Middleware** – A single `middleware.ts` at the web app root runs on every request (except static assets). It applies security headers via `addSecurityHeaders(NextResponse.next())` from `lib/security/headers.ts`: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, and HSTS in production. No auth or Pro gating in middleware; that is done in layouts and server components.
- **Env and secrets** – A single validated env module (`lib/config/env.ts`) is used across the app. Secrets (e.g. `AUTH_SECRET`, `DATABASE_URL`, `INTERNAL_API_SECRET`) are never exposed to the client. Middleware does not import this module so it remains Edge-compatible; it uses `process.env.NODE_ENV` only where needed (e.g. HSTS).
- **Rate limiting (optional)** – When `REDIS_URL` is set, rate limiting can be applied to auth and high-cost API routes. When not set, no rate limiting is applied unless an in-memory fallback is added. See [DEPLOYMENT.md](./DEPLOYMENT.md) and `apps/web/README.md` for Redis usage.

## Cache and Redis

- **Cache TTLs** – Centralized in `lib/constants.ts` (e.g. edge-board, odds compare). API routes import these and use `cacheControlHeader()` for `Cache-Control` so behavior is tunable in one place.
- **Redis** – When `REDIS_URL` is set, the Redis client in `lib/cache/redis.ts` is used. Currently used for caching where wired; future use can include rate limiting. When not set, the app runs without Redis-dependent features (no rate limiting, no Redis-backed cache).
