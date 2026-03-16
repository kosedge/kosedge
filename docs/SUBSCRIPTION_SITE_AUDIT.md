# Kos Edge – Subscription site audit & rating

**Scope:** apps/web (Next.js) as a subscription business product.  
**Date:** 2025 (audit snapshot).

---

## Overall rating: **6.2 / 10**

| Dimension           | Score | Notes |
|--------------------|--------|-------|
| Structure          | 7/10   | Clear app/router, lib, components; some duplication. |
| Organization       | 6.5/10 | Good layout and docs; Pro vs public boundaries fuzzy. |
| Professionalism    | 6/10   | Polished UI and stack; auth/gating and billing incomplete. |
| Enterprise-grade   | 5.5/10 | Solid foundations; subscription and API discipline missing. |
| Scalability        | 6.5/10 | Monorepo, contracts, env; no middleware, weak API patterns. |
| **Subscription-ready** | **4/10** | **Schema and Pro logic exist; no paywall, no Stripe, Pro content not gated.** |

---

## 1. Structure — 7/10

**Strengths**

- Next.js App Router with clear route groups: `(pro)`, `(docs)`.
- `lib/` is well split: auth, config, api (response, error-handler), security, cache, sports, odds, KEI, date-format, etc.
- Shared `packages/contracts` for types (e.g. EdgeBoard).
- Prisma schema is coherent (User, Account, Session, subscription fields).

**Gaps**

- No `middleware.ts`: no single place for auth or Pro gating.
- Pro layout doesn’t enforce access; only `/pro` page checks `isProUser()`.
- Some route/layout duplication (e.g. edge-board vs pro hub).

**Verdict:** Good base and separation of concerns; missing a clear “gate” layer (middleware or layout-level checks) for Pro.

---

## 2. Organization — 6.5/10

**Strengths**

- README (root + apps/web), CONTRIBUTING, ARCHITECTURE, DEPLOYMENT, API docs.
- Project layout table in apps/web README.
- Env via single Zod-validated module; no scattered `process.env`.

**Gaps**

- AUTH_SETUP.md says “Routes under `/pro/*` are protected by middleware” — false; no middleware and most Pro routes are open.
- Typo: `pro/activate/rout.ts` (should be `route.ts`); activate flow doesn’t drive `isProUser()` (DB-only).
- API routes don’t use shared `lib/api/error-handler.ts`; error handling is ad hoc.

**Verdict:** Docs and layout are above average; a few docs are outdated and error-handling patterns aren’t applied consistently.

---

## 3. Professionalism — 6/10

**Strengths**

- Themed UI (Tailwind, CSS variables, kos-* tokens), ErrorBoundary, error/global-error pages, Pino logging.
- NextAuth v5, Prisma, typed env, `jsonError`/`jsonOk` in one route; security lib (rate-limit, sanitize, headers).

**Gaps**

- Pro content is not actually gated: `/pro/welcome`, `/pro/[sport]/*`, KEI lines, power ratings, etc. are reachable without being Pro.
- No Stripe (or other) billing; ProPricing CTAs go to `/pro/welcome`; “activate” route doesn’t set DB subscription.
- Inconsistent API error handling and no shared wrapper used in routes.

**Verdict:** Looks and feels professional; for a paid product, access control and billing are not at “launch” level.

---

## 4. Enterprise-grade — 5.5/10

**Strengths**

- Env validation with fail-fast on bad config.
- Centralized logger, auth helpers, contracts package.
- Prisma migrations, indexes on User (email, role, subscriptionStatus).
- Vercel deploy with lockfile and monorepo-friendly config.

**Gaps**

- No middleware for auth/Pro, so no single enforcement point.
- No API versioning or consistent error schema across routes.
- Subscription state is DB-only with no payment provider or webhooks.
- No E2E or integration tests for auth/Pro/billing.

**Verdict:** Foundations (config, auth, DB, deploy) are solid; subscription lifecycle and API discipline are not yet enterprise-grade.

---

## 5. Scalability — 6.5/10

**Strengths**

- Monorepo (apps/web, packages/contracts) and clear boundaries.
- Edge-board and odds APIs use in-memory cache with TTL; Redis lib present.
- Static data (e.g. KEI) and heavy assets excluded from serverless bundle.

**Gaps**

- Pro check is per-page and DB-heavy (`isProUser()` on every protected page); no middleware or short-lived token/cache.
- No rate limiting applied on API routes in the audit (lib exists, usage not confirmed everywhere).
- No feature flags or gradual rollout pattern for subscription features.

**Verdict:** Will scale for read-heavy and content; needs a clearer, scalable access layer and billing pipeline for subscription growth.

---

## 6. Subscription-readiness — 4/10 (critical)

**What’s in place**

- User model: `subscriptionStatus`, `subscriptionPlan`, `subscriptionStart`, `subscriptionEnd`; `UserRole.PRO` / `ADMIN`.
- `isProUser()` correctly interprets role + active subscription with end date.
- ProPricing UI and Pro hub pages exist.

**What’s missing**

1. **Pro content is not gated**  
   Only `/pro` (landing) calls `isProUser()` and redirects. All other `/pro/*` routes (welcome, [sport], kei-lines, power-ratings, etc.) do **not** check; anyone can open the URLs and see content.

2. **No payment integration**  
   No Stripe (or other) checkout, customer portal, or webhooks. Subscription fields are never set by a payment flow.

3. **Activate route is misleading**  
   `pro/activate/rout.ts` sets cookies that `isProUser()` does not use; Pro status is DB-only. So “activate” does not grant Pro in the current logic.

4. **No server-side enforcement layer**  
   No middleware to redirect unauthenticated or non-Pro users from `/pro/*` (except the single landing page).

**Verdict:** Data model and Pro logic are good; for a real subscription business you need: Pro gating on every Pro route (or middleware), Stripe (or equivalent) plus webhooks, and removal/fix of the activate flow so it aligns with DB/Stripe.

---

## Recommended priorities (in order)

1. **Gate Pro content**  
   - Add Next.js `middleware.ts` that, for `/pro/*` (except `/pro` and maybe `/pro/welcome` for post-login), requires auth and Pro (session + DB or cached Pro flag) and redirects else to `/pro` or sign-in.  
   - Or add a shared Pro layout that calls `isProUser()` and redirects if false.  
   - Ensure every Pro route is behind this (or equivalent) so paid content is not publicly accessible.

2. **Integrate billing**  
   - Add Stripe (or chosen provider): Checkout Session for new subscriptions, Customer Portal for management, webhooks to update `User.subscriptionStatus`, `subscriptionPlan`, `subscriptionEnd`.  
   - Wire ProPricing CTAs to Stripe Checkout; replace or remove the cookie-based activate route so entitlement is driven by DB + webhooks.

3. **Align docs and code**  
   - Update AUTH_SETUP.md (and any similar docs) so they describe actual behavior (no middleware today; Pro gating only on `/pro` until you add it).  
   - Fix `pro/activate/rout.ts` → `route.ts` if you keep the file; otherwise remove or replace with a real “grant trial” or post-checkout redirect.

4. **Harden API surface**  
   - Use `lib/api/error-handler.ts` (or a single wrapper) in all API route handlers so errors return a consistent shape and status codes.  
   - Apply rate limiting and security headers on key API routes.

5. **Tests**  
   - Add tests for: Pro gating (e.g. redirect when not Pro), auth flow (sign-in/sign-out), and at least one critical API (e.g. edge-board or register).  
   - Add E2E for: visit `/pro/kei-lines` as guest → redirect to sign-in or Pro; after “Pro” → can see content.

---

## Summary

- **Structure and organization:** Good for a growing product; a 7 and 6.5 are fair.  
- **Professionalism and enterprise:** Undermined by open Pro content and no real billing; 6 and 5.5.  
- **Scalability:** Fine for traffic and code layout; needs a proper access and billing layer for 7+.  
- **Subscription business:** Today it’s a **4/10** — schema and Pro logic exist but paywall and payments are missing and Pro content is not protected.

**Bottom line:** With Pro gating (middleware or layout) and Stripe (or equivalent) wired to the DB, the same codebase can credibly sit at **7–7.5/10** for a subscription product and scale from there.
