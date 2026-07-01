# Enterprise Readiness Checklist

This checklist tracks *verified* readiness items. It is intentionally strict and should match what CI and runtime behavior actually enforce.

## Current Score

## 🎯 Current Status: **8.9/10** - Strong Production Foundation

The platform is materially hardened and deployable, but a few final architecture and productization items remain before claiming "fully enterprise-grade."

## Verified in Code/CI

### Security & Access

- [x] API rate limiting covers auth and non-auth endpoints (`apps/web/proxy.ts`)
- [x] Non-spoofable limiter identity strategy (no raw `Authorization` keying)
- [x] Security headers applied in proxy path
- [x] Pro entitlement enforced at shared `/pro/*` layout boundary
- [x] Temporary cookie-based Pro activation route removed

### Reliability & Backend

- [x] Model-service CORS hardened (production requires explicit origins)
- [x] Model-service packaging metadata includes runtime dependencies
- [x] Odds snapshot job now persists rows to `odds_snapshots` (append-only)
- [x] Model-service tests include persistence integration coverage

### Testing & Quality Gates

- [x] Lint + typecheck + test + build run in CI
- [x] Critical coverage gate (`pnpm test:web:critical`)
- [x] Default web coverage gate now enforces non-zero thresholds
- [x] Playwright smoke workflow exists and runs separately

### Deployment

- [x] Web deployment workflow (Vercel)
- [x] Model-service image publish workflow (GHCR) with optional deploy hook trigger

### Runtime Boundaries

- [x] Boundary check for Python files under `apps/web` (`check:web-python-boundary`)
- [x] `apps/web/package.json` is blocked from executing Python scripts
- [x] Root scripts no longer execute Python files directly from `apps/web`
- [x] Python execution entrypoints live under `services/pipeline`

## Remaining To Reach 9.5+ / "Audit-Ready"

- [ ] Complete physical migration of legacy Python source files from `apps/web` into `services/pipeline` (execution boundary is done; source relocation is still in progress)
- [ ] Add subscription billing enforcement path (checkout/webhook lifecycle) so entitlement updates are fully automated
- [ ] Add model-service runtime deployment target integration (beyond image publish) in all environments
- [ ] Expand API route integration tests (especially edge-board and odds compare routes)
- [ ] Replace `next-auth` beta dependency with stable release once compatible with current stack

## Practical Next Step For MLB Model Work

You now have a stable enough foundation to start MLB model development without compounding core platform risk. Keep the items above as concurrent hardening tracks while MLB model features land.
