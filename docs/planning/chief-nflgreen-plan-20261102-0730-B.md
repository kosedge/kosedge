# Worker B — Product/service/reliability audit

**Scope:** `chief-nflgreen-plan-20261102-0730` · Worker B · READ-ONLY  
**When:** 2026-11-02 06:40–06:45 EST · CERT=0 · not EVAL · not GREEN · not #6 · not market/enterprise PASS  
**Owner Clear:** `OWNER_CLEAR_t5170u_PLAN_20261102.md` sha8 `eb248e91`  
**PE EXISTING:** `PE_EXISTING_EVIDENCE_t5170u.md` (filed ~06:41 EST) — VERIFY-reuse, not redo  
**Inspected tips:** `#688` `6f29b4a2` · `#695` `bff7c734` · `#697` `0aad8d75` · product tip `origin/cursor/usermenu-header-mount-260c` · `origin/deploy-vercel` · R5 HEAD `455a8e43` · jobs draft `#655` `0b69caaed`/`3d3a4152d`  
**Access proof:** git objects + `gh pr view` (read) + PE packet. No login, no secrets, no Railway/Vercel runtime, no paid Odds, no 2024–26 protected rows. Sparse checkout 12% — product files read via `git show` (not missing code).  
**R5:** CLOSED (`08aa20a3`). Not restarted.

PE Cos/PE stamps (`c7775dae`, `4cd506bd`, `0c5c52ab`, `879da1be`, `fafa3b39`, …) are **receipt IDs, not git objects**. Marked sealed-by-PE, not “missing code.”

---

## 1. VERIFY-reuse vs OWNER CLEAR

| Closes today (no new work) | Needs OWNER CLEAR before any Cursor send |
| --- | --- |
| `#695` `bff7c734` API refuse draft ACCEPT (Alex `64b3d53a` / Cos `9d5b066f`) | Live 320–375 Sign Out QA (Secure Form HOLD; AUTH PARTIAL) |
| `#697` `0aad8d75` export KEI C10 CLOSED VERIFIED draft (transport/JSON refuse) | Entitled smoke (DEFERRED; ACCESS_MATRIX `4cd506bd` sealed) |
| AC-S4/S6 Cos ACCEPT `c7775dae` PASS on **staging**; S3 PARTIAL; staging≠prod | Age / `history_lagging` gates (PE: UNKNOWN, Needs Alex) |
| Board-refresh disable ACCEPT `0c5c52ab` (Cos `d5ec4bfb`) | Stripe intent / billing test lifecycle (`fafa3b39` DISABLED) |
| P14 freshness `879da1be` Paper≠EXEC (do not treat as EXEC) | Export empty-`lines` **business** policy (refuse vs honest-empty) |
| G1 anon `private,no-store` PASS (PE) | `#655` jobs auth merge + Railway live (C10 HOLD) |
| BILLING_PATH_ID `fafa3b39` sealed DISABLED | Any draft→`deploy-vercel` merge / paid / EVAL / R5 |

---

## 2. Compact table

component | exact source/evidence | actual gap | owner | next bounded Cursor work order | deterministic done criterion | dependencies/permission | realistic duration | success successor / failure fallback
--- | --- | --- | --- | --- | --- | --- | --- | ---
Sign-in / register | `apps/web/app/auth/signin/page.tsx`; `app/api/auth/register/route.ts` @ product tip; Auth.js credentials + bcrypt + zod min-8 | Code present. Live `/auth/signin` Secure Form e14/e17/e18 HOLD. Runtime UNKNOWN. | PE / host | Do **not** remount. If CLEAR: fill-name ping + one sign-in happy/fail on named host only. | Named host returns 200 form + invalid creds stay on page with error; no secret print. | OWNER CLEAR + vault fill. No credential read by agent. | 1 QA session | AUTH can move past PARTIAL for **desktop sign-in only** / remain UNKNOWN
Sign-out `#688` | Tip `6f29b4a2` OPEN vs `deploy-vercel` (not ancestor). Vitest UserMenu+header 14/14; D1 PE ACCEPT `3ae6a641` / Cos `83e3cbad`; AUTH PARTIAL `f7e567ed` Cos `26353794`. `UserMenu.tsx` `signOut({ callbackUrl: "/" })`. **Not** on `deploy-vercel` `SportProHeader`. | Draft-only mount. Live 320/375 Sign Out **NOT RUN / UNKNOWN**. Prod header has no UserMenu. | PE + Cos (reuse) | VERIFY-reuse only. Optional P2 live QA 320 **and** 375: open menu → Sign Out → session gone → `/`. No auth rewrite. | Screenshot/video both widths; `signOut` fires; post-logout `/` unauth chrome. Mobile overflow/obstruction fail = not done. | OWNER CLEAR + Secure Form host. Mobile real QA remains separate. | 1 QA session (0 code if pass) | AUTH can leave PARTIAL / stay `f7e567ed` PARTIAL
Roles / entitlements | `getEntitledProAccessState` EXISTING @ `apps/web/lib/auth/pro.ts` product tip + `deploy-vercel`. ACCESS_MATRIX `4cd506bd` sealed. G1 residual WAIVED `a9a0ab23`. Entitled smoke DEFERRED. R5 HEAD `pro.ts` is **stale** (no entitled/OPEN_ACCESS path). | JWT `token.role` set at login; entitled path re-reads Prisma (good). `ACTIVE` **and** future `subscriptionEnd` required — `CANCELLED`+valid end = forbidden. OPEN_ACCESS exact `"true"` bypasses entitlement on `getProAccessState` (Insights uses entitled path). Smoke DEFERRED. | PE | Do **not** redo matrix. If CLEAR: one entitled + one forbidden synthetic using existing `pro.test.ts` only (no new scored tests). | Existing vitest entitled/forbidden/expired still green; no OPEN_ACCESS grant via `NEXT_PUBLIC_*`. | Entitled smoke = OWNER CLEAR. No prod env read. | Reuse: 0. Smoke: 1 session | Smoke PASS recorded / remain DEFERRED
Billing disabled | `ProPricing.tsx`: paid CTAs → `/auth/signup?callbackUrl=/pricing` (“Until checkout is fully launched”). No Stripe files on product tip. BILLING_PATH_ID `fafa3b39` sealed · Stripe intent-only **MISSING** · DISABLED. | No checkout session, webhook, or test-lifecycle beyond paper ID. | PE / Ryan | Paper-only. Do **not** add Stripe. | Receipt restates DISABLED + missing intent. No live charge. | Paid HOLD. New Stripe = OWNER CLEAR (not today). | 0 (reuse) | Stay DISABLED / do not invent lifecycle
Freshness / cache | `nfl-data-freshness.ts`; `page-data-cache.ts` (`private,no-store` + occupancy); board-refresh ACCEPT `0c5c52ab`; P14 `879da1be` Paper≠EXEC; G1 anon no-store PASS. Age/`history_lagging` UNKNOWN (Needs Alex). | Banner filters transport/DR/`injuries:` — HTTP 503 + empty blockers still shows. Live age gates UNKNOWN. Paper≠EXEC. | PE + Alex (gates) | VERIFY `0c5c52ab`. Do **not** EXEC P14. Alex names age-gate contract before any code. | No new freshness EXEC. Age-gate UNKNOWN until Alex. | Needs Alex for gates. No Odds. | Reuse: 0. Gates: blocked | Record UNKNOWN / do not promote Paper to EXEC
API refuse `#695` | Tip `bff7c734` OPEN draft. `nfl-c10-consumer-refuse.test.ts` + addendum. C10 down→503 / timeout→504; no invented `lines`/`rows`/`count`; dual `private,no-store`. 14/14 offline. Alex PASS_RO `64b3d53a` Cos ACCEPT `9d5b066f`. | Draft≠merge≠#6. Live C10/Railway UNKNOWN. | Cos (reuse) | VERIFY-reuse. No redo. | Receipt cites `bff7c734` + Cos ACCEPT. No new route test. | None for reuse. Merge = OWNER + C10. | 0 | Stay draft ACCEPT / do not claim #6
Export KEI C10 `#697` | Tip `0aad8d75` CLOSED VERIFIED draft. 25 pytest. Transport/JSON → exit 1, OUT untouched. Addendum gaps **left as-is**: empty `lines` → exit **0** + `games:[]`; blank teams skip; non-numeric `spread`/`total` → uncaught `ValueError` (not `return 1`). | Transport refuse verified. **Business** empty/malformed-success **open**. Not #6. | Cos (reuse) + optional P1 | VERIFY transport. P1 only if OWNER names empty-success policy (honest-empty vs refuse). Tests only; no script edit unless named. | Transport 25/25 still green. If P1: empty/`ValueError` cases asserted to the **named** policy. | P1 needs OWNER policy sentence. No Odds HTTP. | Reuse: 0. P1: 1 session / 1 test file | Honest-empty or refuse sealed / leave reported gaps
Jobs ownership / retry / idempotency | Product tip `main.py` `/api/jobs/pull-odds-snapshot` **no** handler auth. `#655` OPEN draft: `APIRouter(prefix="/api/jobs", dependencies=[Depends(require_kosedge_internal)])` + `test_jobs_internal_auth.py`. Celery `acks_late` default true; broker retry on startup. Ledger/camp-SOT have natural-key idempotency; **jobs enqueue is not owner-keyed**. | Unauth enqueue on product/`deploy-vercel` tree. Live Railway UNKNOWN (do not probe). No per-user job owner. Duplicate POST = new `task_id`. | Eng (draft exists) | Do **not** merge `#655` today. VERIFY-reuse inspection only unless OWNER + Railway/C10 CLEAR. | Inspection receipt: product tip ungated vs `#655` gated. Runtime stays UNKNOWN without CLEAR. | C10 HOLD · Railway workflow_dispatch CLEAR. Odds jobs = paid HOLD. | Inspection: 0. Merge: blocked | Stay DRAFT `#655` / do not live-probe
Alerts | `nfl_ops_alerts.py`: webhook (`NFL_ALERT_WEBHOOK_URL` or OPS/MLB fallback) + `nfl_ops_alert_events` persist; fail logs, returns bool. | Code present. Live delivery / table / on-call UNKNOWN. No customer-facing alert. | Ops | No drill. If CLEAR later: one synthetic persist test, no webhook fire. | Persist function still writes; no secret URL read. | Webhook URL = secret. No env read. | Blocked today | UNKNOWN / do not page
Backup / restore / rollback | `run-ownership-dr-backup.sh` + `dr_backup.py`: pg_dump, `verify_pg_dump` (pg_restore **verify**), retention, optional S3. Job `POST /api/jobs/run-nfl-dr-backup`. Freshness treats `dr_backup:` as ops-only (not board stale). | Backup+verify code present. **No `run_dr_restore` / customer rollback playbook.** Last backup / remote URI / restore drill UNKNOWN. | Ops | No drill, no S3. Paper: verify≠restore. | Receipt states verify-only. | Restore drill = OWNER + DB. | Blocked today | UNKNOWN last success / do not restore
Request / slate cost | `warm-page-data` cron: week1-only, “full-slate not warmed (Odds spend bound)”. `check_odds_api_credits.py` needs `ODDS_API_KEY` (forbidden). Rate-limit: 100/60s API, 10/60s auth write (memory if no Redis). | Spend **bound in code**; live remaining/last-cost UNKNOWN (paid HOLD). Ungated `/api/jobs/pull-odds-snapshot` is the cost hole if Railway live. | Ops / Cos | Do **not** run credits script. Bind cost hole to `#655` HOLD. | No Odds HTTP this run. | Paid / cap HOLD. | 0 | UNKNOWN credits / do not pull
Customer version / cutoff / probability / price / limitations | `fair-lines-api-board.ts` honesty envelope (`modelVersion`, `asOf`/`oddsAsOf` null unless vintage). `ProPricing` $0 / $5.99 / $12.99 / $116.91; CTA not checkout. Disclaimer: estimates, not advice. Coming Soon ON (`isFootballPublicNumbersDisabled` default true; heading “Coming soon”). CERT=0. NFL FairLinesClient window cutoff is **UI pastDays filter**, not cert cutoff. | No subscriber cert/version/cutoff stamp on football public numbers (Coming Soon). Price copy exists; pay path missing. Corrections = research (`t5168u`) not customer-facing. Empty 200 + `slateStatus` is the honesty pattern — export empty-success **diverges**. | Product | Do **not** publish cert copy. If P1: align export empty-success with `FAIR_LINES_HONEST_EMPTY_STATUSES` **or** OWNER-named refuse. | No cert/GREEN claim. Coming Soon stays ON. | CERT=0 · FREE_PUBLIC HOLD · #8 not PASS. | Copy-only blocked | Stay Coming Soon / do not redefine #8

---

## 3. One dependency-aware integration path

1. **Cos stamp VERIFY-reuse** (this file + PE packet). No worker. Closes `#695`/`#697`/AC-S4/S6/board-refresh/billing-ID as *existing*.
2. **Alex (07:15)** — age/`history_lagging` contract + empty-success **semantics** (honest-empty vs refuse). Contradiction pass only; no new science.
3. **If Ryan CLEARs after 07:30 (pick at most two):**  
   **P1** empty-success draft tests (depends on Alex/Ryan policy sentence) → independent RO → Chief.  
   **P2** live 320+375 Sign Out (depends on Secure Form HOLD lift).  
   Cos is sole integration owner. **Do not** start `#655`, Stripe, freshness EXEC, entitled smoke, or R5.
4. **Merge/deploy** only if a later CLEAR names `deploy-vercel` (AGENTS production contract). This planning PR is **not** that.
5. **Failure anywhere:** stop; keep PARTIAL/UNKNOWN; do not redefine eight targets.

---

## 4. Release rehearsal checklist (not a release)

- [ ] CERT=0 · Coming Soon ON · OPEN_ACCESS unset/closed · billing DISABLED
- [ ] `#688` still DRAFT; prod `SportProHeader` has no UserMenu until merge CLEAR
- [ ] `#695`/`#697` draft≠#6; empty-`lines` export still documented gap unless P1 named
- [ ] No `/api/jobs/*` merge; no live Odds; no credits script
- [ ] AC-S4/S6 staging PASS ≠ prod; S3 PARTIAL stands
- [ ] Sign-out 320 **and** 375 real QA recorded or explicitly UNKNOWN
- [ ] Entitled smoke DEFERRED or CLEARED with named users
- [ ] Age gates named by Alex or UNKNOWN
- [ ] DR: last backup UNKNOWN; verify≠restore
- [ ] Customer copy: no cert/version/cutoff as GREEN; prices ≠ checkout
- [ ] Production ship bar remains AGENTS: PR → `deploy-vercel` + Production Gate (not `restore-working-ui`, not R5)

---

## 5. Customer acceptance tests (named; not run this audit)

| ID | Surface | Pass |
| --- | --- | --- |
| CAT-A1 | Sign in invalid | Error stays on `/auth/signin`; no session |
| CAT-A2 | Sign in valid | Lands `callbackUrl` or `/pro/welcome`; menu shows email/name |
| CAT-A3 | Sign out desktop | Menu → Sign Out → `/` + signed-out chrome |
| CAT-A4 | Sign out 320 and 375 | Same as A3; control ≥ touch; menu not clipped by sticky header |
| CAT-E1 | Anon football numbers | Coming Soon; no invented KEI/edges |
| CAT-E2 | Entitled Pro | `getEntitledProAccessState==authorized` sees entitled desk; forbidden sees pricing/closed — **DEFERRED** |
| CAT-B1 | Paid plan click | No Stripe; signup/pricing only while DISABLED |
| CAT-F1 | C10 down | API 503/504, no empty-success board, `private,no-store` (draft `#695`) |
| CAT-X1 | Export C10 down | exit 1, OUT unchanged (`#697`) |
| CAT-X2 | Export 200 + empty `lines` | Behavior matches **OWNER-named** policy (today: exit 0 + `games:[]` — not refuse) |
| CAT-C1 | Version/as-of | `asOf`/`oddsAsOf` null unless vintage; no request clock |
| CAT-C2 | Limitations | Disclaimer + Coming Soon visible; no cert/GREEN |

---

## 6. Effort ranges (inspected code, not calendar)

| Work | Files / size | Effort |
| --- | --- | --- |
| VERIFY-reuse stamp | 0 code | Cos only |
| P1 empty-success tests | extend existing 435-line pytest; script 68 lines unchanged unless policy | 1 Cursor session |
| P2 mobile Sign Out QA | 0 code if pass; `UserMenu.tsx` ~110 lines if fail | 1 QA session |
| `#655` jobs auth (not today) | already drafted; `test_jobs_internal_auth.py` 156 lines | VERIFY 0; merge blocked |
| Stripe lifecycle | **no files** | blocked — not a TODAY package |
| Entitled smoke | `pro.ts` 127 lines + `pro.test.ts` | 1 session after CLEAR |
| Age gates | freshness module + Needs Alex | blocked |
| DR restore playbook | backup verify exists; restore fn missing | not TODAY |

---

## 7. TODAY dispatch packages (max 2 workers + Cos)

**Cos (integration owner, not a 3rd worker):** synthesize A+B; no new scientific choice; no ACK loop.

**P1 — Empty/malformed-success business semantics (draft tests only)**  
build → existing `#697` pytest green → add cases for empty `lines` / blank teams / non-numeric (policy **named in CLEAR**) → no production script change unless CLEAR says refuse → one independent RO → Chief.  
**In:** `apps/web/tests_pipeline/test_export_kei_lines_nfl_c10_refuse.py` (+ optional page-data 200-empty oracle). **Out:** Odds, EVAL, `#6` PASS, script rewrite without policy.  
**Fallback:** keep `#697` addendum gaps 1–3 as reported.

**P2 — Live 320–375 Sign Out QA (no product rewrite)**  
build = existing `#688` 14/14 → real 320 **and** 375 Sign Out on named host → in-scope CSS/hit-target fix **only if** QA fails → one independent RO → Chief.  
**Out:** CSRF/entitlement/forecast gates; Secure Form code until HOLD lifts.  
**Fallback:** AUTH PARTIAL `f7e567ed` stands.

If Ryan CLEARs **zero** of P1/P2: **no Worker B implementation today.** Reuse is already closed.

Do **not** dispatch: Stripe, `#655` merge, freshness EXEC, entitled smoke, R5, paid Odds, backup restore, alert drills.

---

## 8. UNKNOWN runtime (not missing code)

- Live Sign Out 320/375; Secure Form `/auth/signin` e14/e17/e18 host
- Entitled user against prod/staging (smoke DEFERRED)
- AC-S3 / AC-S4/S6 on **prod** (staging PASS only)
- Railway `/api/jobs/*` auth, celery owners, retry live
- Alert webhook delivery + `nfl_ops_alert_events` rows
- Last DR backup, remote URI, restore drill
- Odds remaining / last-request cost
- Age / `history_lagging` live gates
- Stripe (no intent)
- `OPEN_ACCESS_PREVIEW` **prod** value (do not read env)

---

## 9. AGENTS / policy conflicts

| Policy | Conflict |
| --- | --- |
| AGENTS.md | Production PRs → **`deploy-vercel`**. `restore-working-ui` is a thinner shell — not live. This run’s ManagePullRequest preferred base is `restore-working-ui`; cloud base is R5 `cursor/t5155u-r5-n1-market-1033`. **This PR is planning-only on the R5 base; it is not a production ship.** |
| AGENTS Railway | `deploy-railway.yml` needs C10 CLEAR. `#655` cannot ship without it. |
| OWNER CLEAR t5170u | No merge/deploy/paid/EVAL/R5 restart. Honored. |
| Eight targets | None close. `#6`/`#8` **not** redefined by `#695`/`#697`/Coming Soon. |
| R5 HEAD vs product | R5 `apps/web/lib/auth/pro.ts` lacks `getEntitledProAccessState`. Do not treat R5 tree as product SoT. |

---

## 10. CERT

CERT=0 · planning only · draft≠merge · R5 CLOSED · paid HOLD · Stage C / R2 HOLD / R3 STOP preserved · targets 0/8 · Worker B complete 06:45 EST.
