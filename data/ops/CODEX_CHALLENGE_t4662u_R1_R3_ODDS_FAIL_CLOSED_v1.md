# CODEX_CHALLENGE — t4662u R1–R3 Odds fail-closed v1

Lane: **Codex / independent challenge** (Ryan DECISION **a984759c** · COS_ORDER t4662u R1–R3)
Not the implementer. No repairs. No merge / deploy / paid Odds / env / F2 / CERT.
Does **not** self-grade PASS. IMV grades the tip.

| pin | value |
|---|---|
| Challenged tip | `a2f86c448dccce91a1a823cbc4dde0413871e117` · #650 DRAFT `cursor/odds-fail-closed-r1-r3-d90e` |
| Authority | COS_ORDER sha8 (this order) · DECISION **a984759c** · matrix **d0aac2d4** · evidence **1401f586** |
| Parent design | ODDS_FAIL_CLOSED_DESIGN **886ceb2a** · receipt **a2f86c44** (Cursor claim: 7 DENIED / 1 AUTHORIZED_JOB / 2 UNAVAILABLE_HONEST) |
| Prior vacuous class | **88a08cae** / **75141507** G-C7-VACUOUS — close or reopen |
| Scope of this paper | Sealed DRAFT tip only. Web choke + tests + leftover request hops. |
| Verdict of this paper | **CHALLENGE_FILED** · **NOT** PASS · **NOT** a ship ticket |

Hard locks honored: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · A1 restore HOLD · B HOLD · R4 emergency HOLD.

Codex did **not** call the-odds-api (paid or free). Did not change env, deploy, merge, or repair.

---

## What the sealed tip already does well (not a pass)

These are facts so IMV does not treat this paper as a redo of Cursor discovery.

- A web choke exists: `apps/web/lib/odds-acquire/acquire.ts` is the only `apps/web` runtime constructor of `https://api.the-odds-api.com` / `https://widget.the-odds-api.com`.
- `REGISTERED_ODDS_ACQUIRE_JOB_IDS` is an empty `Set`. No production web job can enter ALS. `WARM_PAGE_DATA_JOB_ID` is refused at `enterAuthorizedOddsJobContext`.
- `ODDS_WEB_PAID_FETCH_ALLOW` must equal `"1"` **and** ALS must already be a CRON_SECRET-verified registered job. Flag alone does not acquire. Evidence 1401f586: the flag is absent in Vercel.
- `/api/odds/[sport]/compare` no longer calls `fetchOddsComparison`. Cache miss / Redis absent returns `{source:"none",reason:"paid_fetch_denied"}`.
- Rate-limit exemption is Bearer `CRON_SECRET` only. `x-kosedge-warm` / `x-vercel-cron` no longer skip the limiter.
- Direct web callers (`fetchEdgeBoard`, futures, preseason, widget, `fetchAlternateSpreadSnapshot`) go through `oddsAcquire` and catch `PaidFetchDenied`.
- Tip delta is **apps/web + one CI grep + tests only** (37 files). `services/model-service/src/celerybeat_schedule.py` and `services/model-service/src/services/odds_api.py` are not in the diff — beat/worker code is not accidentally gated by this commit.
- Cursor does not self-grade PASS on the receipt.

The challenge is that **B1 (“ordinary page/SSR/GET/preview/user reads NEVER initiate paid Odds”) is implemented as a Vercel hostname filter**, not an end-to-end acquisition boundary. User-read still has live hops to Railway `fetch_odds`. Several oracles are the same vacuous class as G-C7-VACUOUS (88a08cae).

---

## Gaps found (index)

Severity: **BLOCKING** = would RETURN / FAIL if IMV applies B1 / S4 / S5 / S6 / C7-tests strictly · **HIGH** · **MEDIUM** · **LOW** · **NOTE**.

| id | gap | hunt item | severity | Cursor already deferred? |
|---|---|---|---|---|
| G-PROXY-LIVE | User-read SSR/API still default `oddsMode:"live"` into model-service `/nfl/fair-lines` → `fetch_odds` | 1, 5 | **BLOCKING** (B1 / “no web surface acquires”) | S9 “not part of web DRAFT” — B1 was not scoped that way |
| G-CFB-RAIL-LIVE | CFB assemble (gate OPEN or warm) hits `/cfb/edge-board-odds`; warehouse miss → `_live_pull_events` (`allow_live=True`) | 1, 4, 5 | **BLOCKING** (S4/S5 DENIED) | Web order inverted; Railway live leftover unnamed |
| G-S6-CLIENT-SNAP | Line-curve POST treats client `snapshot` as fresh book alts (`researchOnly:false`) | 5 | **BLOCKING** (S6 fabricate) | L1 only classifies fixtures |
| G-C7-VACUOUS-2 | Fail-closed suite greps / `False`-adjacent regex / stubbed `fetch` that cannot see Railway or count `oddsAcquire` | 6 | **HIGH** (reopens 88a08cae) | Inventory claimed I1–I6/L1/U1–U3 |
| G-NCAAM-PROXY | `ncaam/today` dropped web Odds but proxies model-service `/edge-board/ncaam/today` → `_fetch_odds_ncaab` | 1 | **HIGH** (S3 DENIED) | “align retire scope” only |
| G-S7-SOURCE-LIE | Denied futures bundles still `source="The Odds API"`; CFB page prints that source; I2 accepts `—` | 5, 6 | **HIGH** (S7 honesty) | Note string loosened |
| G-I3-STUB | I3 warm `fetch(origin)` is stubbed to dummy 200; never executes assemble through warm | 4, 6 | **HIGH** (S5 / C5) | I3 listed as proof |
| G-ALS-OMIT-INTENT | `oddsAcquire` omits-intent ≠ deny; request loaders do not pass `intent:"request"` | 7 | **MEDIUM** (latent ALS leak) | Empty registry today |
| G-COMPARE-NONE-CDN | Denied compare body shipped with `s-maxage=21600` | 3 | **MEDIUM** (B2 / none-cache) | Line-curve none TTL is 60s; compare is 6h |
| G-S1-NO-SOT | Compare never reads `odds_snapshots`; never writes cache; always `none` | 3 | **MEDIUM** (S1 SoT claim) | Fail-closed empty is allowed under B2 |
| G-FLAG-EMPTY-SET | `ODDS_WEB_PAID_FETCH_ALLOW=1` + valid cron still cannot acquire (empty Set) — rollback prose overclaims | 8 | **MEDIUM** (flag misuse) | Empty Set is intentional deny |
| G-C1-NOT-SOLE | `odds-fetch.ts` claims sole `oddsAcquire` caller; futures/widget/preseason/line-curve call acquire directly; `acquire.ts` has no `server-only` | 1, 6 | **MEDIUM** | CI grep ≠ runtime sole exit |
| G-E1-ABSENT | No Vercel env-name attestation (E1); C7 ledger not on tip; C8 flag absent in `odds_api.py` | 6, 8 | **MEDIUM** | C7/C8/E1 left off R1 |
| G-S10-GREP | Beat “untouched” oracle is two `toContain` strings | 6, 7 | **LOW** (code untouched; oracle vacuous) | Diff fact is stronger than the test |
| G-RL-PROXY | I4/I6 call `rateLimit()` directly; do not execute `proxy.ts` | 2, 6 | **LOW** | Function body is the right deny |

No gap below asserts occurrence of the 2026-10-27 credit burn, MAE, CERT, PLAY, or that beat/worker was broken by this tip.

---

## 1. Request-path / SSR / GET escapes that can still hit the-odds-api.com

### G-PROXY-LIVE — web choke is not the user-read boundary
**Severity:** BLOCKING for B1 · **Deferred?** S9 only (model-service “not in this DRAFT”)

B1 / receipt: ordinary page/SSR/GET/preview/user reads never initiate paid Odds.

Tip implements that as: do not `fetch('https://api.the-odds-api.com…')` from `apps/web` unless ALS+flag+registered job. `fetchNflFairLines` default is still **live**:

```685:711:apps/web/lib/nfl-fair-lines.ts
  const oddsMode = params.oddsMode ?? "live";
  ...
  if (!useReusePost && oddsMode !== "live") {
    url.searchParams.set("odds_mode", oddsMode);
  }
```

When `oddsMode` is the default `"live"`, the query param is **omitted**. Model-service GET defaults to the same:

```4660:4686:services/model-service/src/routes/nfl.py
    odds_mode: str = Query(
        "live",
        description=(
            "WS-02 DUP-C: live (default HTTP), skip (never fetch_odds), "
            ...
        ),
    ),
) -> Dict[str, Any]:
    """Customer/page-data fair-lines GET. Default odds_mode=live (one Odds HTTP)."""
```

`_resolve_nfl_fair_lines_market_events` then calls `fetch_odds` (`sports/americanfootball_nfl/odds`) — `services/model-service/src/services/odds_api.py:79-90` (`BASE_URL = "https://api.the-odds-api.com/v4"`).

User-read callers on this tip that **do not** pass `oddsMode: "skip"|"reuse"`:

| surface | gate? |
|---|---|
| `/pro/prediction-market` SSR (`page.tsx:50-54`) | **No** football kill switch. In Pro nav. |
| `/pro/[sport]/execution` NFL branch (`execution/page.tsx:66-70`) | **No** |
| `POST /api/nfl/season-engine/survivor` (`survivor/route.ts:78-82`) | **No** |
| `loadSeasonEngineMatchups` (`nfl-season-engine.ts:887-891`) | **No** |
| `resolveKeiGames("nfl")` (`resolve-kei-lines.ts:95-99`) | Indirect |
| `/api/nfl/fair-lines`, edges-desk, pickem | Football / cert surface closed **today**; live again if gate opens |
| NFL assemble week1 | **skip/reuse** (this tip honors that) |

1401f586 classified model-service request-path as NOT REACHABLE under C10 API Offline. That is a **Railway state**, not a deny in this tip. `ODDS_API_REQUEST_PATH_ALLOW` does not exist in `odds_api.py`. If any fair-lines GET still serves (and the web app is written as if it does), a Pro page load pays on Railway **without touching `oddsAcquire`**.

`installOddsHostFailOnHit` only watches `globalThis.fetch` URLs matching `*.the-odds-api.com`. A stubbed `http://localhost:8000/nfl/fair-lines` 200 is a **pass**. The suite cannot see this hop.

**Recommended test (do not implement):** SSR `prediction-market` / execution / survivor with dummy `MODEL_SERVICE_URL` mock that **fails the test** if the outbound URL has `odds_mode=live` or omits `odds_mode`. Model-service unit: GET `/nfl/fair-lines` with `ODDS_API_REQUEST_PATH_ALLOW` unset must not call `fetch_odds`. Codex did not hit Railway or Odds.

### G-CFB-RAIL-LIVE — S4/S5 “DENIED even if gate opens” is false
**Severity:** BLOCKING for S4/S5 · **Deferred?** no (web inverted; Railway live remains)

Web `loadCfbCurrentMarketRows` no longer calls `pullVercelLiveCfbRows`. It `upstreamFetch`es `${MODEL_SERVICE_URL}/cfb/edge-board-odds`.

Model-service:

```424:433:services/model-service/src/routes/cfb.py
@router.get("/edge-board-odds")
def cfb_edge_board_odds() -> Dict[str, Any]:
    ...
    return current_cfb_odds_events()
```

```273:316:services/model-service/src/services/cfb_edge_board_odds.py
def current_cfb_odds_events(..., allow_live: bool = True) -> Dict[str, Any]:
    warehouse, warehouse_as_of = _load_warehouse_events(clock)
    if warehouse:
        return {...}
    if not allow_live:
        return {..., "source": "none", ...}
    live, live_as_of, live_source = _live_pull_events()
```

`_live_pull_events` → `fetch_odds(endpoint="sports/americanfootball_ncaaf/odds")`. Route does not pass `allow_live=False`.

Today the football kill switch short-circuits assemble **before** this hop (`CFB_EDGE_BOARD_PUBLIC_ENABLED=false`, env override absent). That is 1401f586 CONDITIONAL/LATENT. Matrix S4/S5 claimed **DENIED** (double-closed: gate **plus** choke even if `*_EDGE_BOARD_INTERNAL` is set). I1 S4 / I3 **open the gate** and only assert `probe.hits === []` on the **web** fetch stub. When the gate is open, warm `* * * * *` → `/api/edge-board/cfb/assemble` → Railway live-pull-on-warehouse-miss. That is the latent paid path 1401f586 already named — **not closed on this tip**.

NFL assemble on this tip is better: `pullOddsRows` denies, then `fetchNflFairLines({ oddsMode: "skip"|"reuse" })`. CFB is the hole.

### G-NCAAM-PROXY — S3 web deny, Railway still pays
**Severity:** HIGH · **Deferred?** “confirm retire scope”

`/api/edge-board/ncaam/today` no longer calls `fetchNcaabEdgeBoard`. On cache miss it `fetch`es `${MODEL_SERVICE_URL}/edge-board/ncaam/today`. Model-service `_fetch_odds_ncaab` (`edge_board.py:184-226`) still `httpx.get`s `{ODDS_API_BASE}/sports/basketball_ncaab/odds`.

Public callers without `INTERNAL_API_SECRET` get 401 when the secret is set (Vercel: PRESENT). Internal/secret-bearing request-path still pays. Assemble `/api/edge-board/ncaam/assemble` is public and uses web `pullOddsRows` → `oddsAcquire` (denied). Two different ncaam stories; only one is denied.

I1 S3 accepts `401` **or** `200` with `paid_fetch_denied` **or** `source==="snapshot"`. A 401 before any hop keeps the test green.

---

## 2. Header-spoof bypass

**Acquisition:** headers never enter `enterAuthorizedOddsJobContext`. Spoofed `x-kosedge-warm` / `x-vercel-cron` cannot set ALS. No production caller of `enterAuthorizedOddsJobContext` exists outside tests. **No header→paid bypass on the web choke.**

**Rate-limit:** `isVerifiedCronSecretRequest` is Bearer secret only (`rate-limit.ts:135-148`). Function-level I4/I6 are real for that function.

**G-RL-PROXY (LOW):** production wiring is `apps/web/proxy.ts` (`proxy()` → `rateLimit`). I4/I6 never import `proxy`. A future rename/skip of `proxy.ts` would leave I4/I6 green.

Warm still **sends** `x-kosedge-warm: 1` on the public assemble GET (observational; no Authorization forwarded). That is not an acquisition grant.

`authorizeCron` on warm uses `===` rather than constant-time compare. Not an Odds escape.

---

## 3. Cache-miss / Redis-absent fallthrough

Compare (`route.ts:108-116`) and ncaam/today (after model miss) do **not** live-pull on the web side. Redis absent (1401f586: no `REDIS_URL`) ⇒ compare is always `none`. **No web fallthrough to Odds on S1.**

**G-S1-NO-SOT (MEDIUM):** S1 promised SoT `odds_snapshots` read. The handler never writes `compareCache` / Redis and never calls model-service. Honest empty, not a snapshot board.

**G-COMPARE-NONE-CDN (MEDIUM):** `CACHE_HEADERS` is `public, s-maxage=21600, stale-while-revalidate=3600` on the **denied** body. Line-curve design (matrix §4) forbade caching `none` > 60s. A later SoT read would stay invisible behind a 6h CDN `none`.

`today` (non-ncaam) on miss still runs `assembleEdgeBoardRows` (NFL → `pullOddsRows` deny + fair-lines skip/reuse; NBA → fallback rows, no `pullOddsRows` in that function). Direct Odds deny holds; NFL fair-lines skip holds.

---

## 4. warm-page-data latent paid path

Warm itself does not call `oddsAcquire` and cannot enter ALS (`WARM_PAGE_DATA_JOB_ID` throws). Schedule still `* * * * *` (R6 not authorized). Football gate closed ⇒ assemble 503 before CFB Railway hop.

**G-I3-STUB (HIGH):** I3 sets dummy key + `CRON_SECRET` + both `*_EDGE_BOARD_INTERNAL=true`, then `warmGET`. `installOddsHostFailOnHit` answers **every non-Odds URL** with `{ok:true,rows:[],events:[]}`. Warm’s `fetch(origin + /api/edge-board/cfb/assemble)` never reaches the assemble handler. The follow-up `assembleGET` is a second, in-process call — still stubbing model-service to empty events, so `_live_pull_events` never runs. I3 proves “web fetch stub saw no Odds host.” It does **not** prove C5 (`source!=="vercel_live"` / 0 Odds client invocations) once Railway is in the loop.

`warm-page-data-cron.test.ts` is substring locks (`toContain("CRON_SECRET")`, `toContain("x-kosedge-warm")`). Same class as 88a08cae G-C7-VACUOUS.

---

## 5. Line-curve / Pro paths — pay or fabricate

### G-S6-CLIENT-SNAP — client snapshot is treated as a job book
**Severity:** BLOCKING for S6 · **Deferred?** no

GET `/api/line-curve` returns `lineCurveUnavailablePayload()` and does not call `fetchAlternateSpreadSnapshot`. Good for **pay**.

POST `/api/line-curve` (`route.ts:94-118`): if the Pro client sends `body.snapshot` with a parseable `capturedAt` within 30 minutes, `classifyAltSnapshot` returns **`tier:"fresh"`, `researchOnly:false`**. `getLineCurve` then `priceAlternateSurface` on that JSON. There is no job id, signature, or ALS check. Matrix S6 required a **job-acquired** snapshot, else STALE / model curve labeled “Market alt prices unavailable” — **never fabricated book alt prices**.

`allowLiveOddsFetch` still exists on the service (`service.ts:38-71`). HTTP routes do not set it (containment grep). The live adapter remains and still calls `oddsAcquire` if anyone sets the flag.

L1 only runs `classifyAltSnapshot` on the Missouri fixture. It never POSTs an unsigned snapshot and never asserts `researchOnly:true` for client-minted `capturedAt=now`.

Optimize POST: missing legs → honest unavailable. Supplied `legA`/`legB` are priced as given (client-trusted quotes). Secondary to the snapshot hole.

### G-S7-SOURCE-LIE — denied futures still branded The Odds API
**Severity:** HIGH · **Deferred?** I2 loosened

`loadNflFuturesOdds` / `loadCfbFuturesOdds` / `fetchNflPreseasonOddsMarkets` call `oddsAcquire` and map `PaidFetchDenied` → `status:"unavailable"`. Direct pay: denied.

`emptyBundle` keeps `source: CFB_FUTURES_ODDS_SOURCE` (`"The Odds API"`). `/pro/cfb/futures` always renders “Market odds from {market.source}” (`page.tsx:122-124`) plus `honestyNote="Missing book prices show —."`. Denied reads look like an Odds API empty book, not a fail-closed deny. NFL awards/projections still call the loader on every SSR; they do not gate on football Coming Soon the way edge-board does.

I2:

```204:208:apps/web/__tests__/lib/odds-fail-closed-request-paths.test.ts
    expect(nfl.status === "unavailable" || nfl.status === "no_key").toBe(true);
    ...
    expect(nfl.note).toMatch(/unavailable|as-of|—/i);
```

Dummy `ODDS_API_KEY` is set, so `no_key` should be impossible. The note regex matches an em-dash that already lives on the **success** player-futures sentence. This is G-C7-VACUOUS (`"False" in text`) in another costume.

---

## 6. Vacuous tests (G-C7-VACUOUS-2)

**Severity:** HIGH — reopens 88a08cae rather than closing it.

| oracle | what it actually asserts | what it cannot catch |
|---|---|---|
| U3 / `check-odds-acquire-choke.sh` | `git grep the-odds-api.com` under `apps/web` excluding `lib/odds-acquire/`, `scripts/`, tests, md | `apps/web/scripts/*` still contain the host; **all of model-service**; IP/env URL; `oddsAcquire` call-count |
| S10 | file text contains `pull-odds-season-cadence` and `https://api.the-odds-api.com/v4` | beat crash, queue rename, request-path `fetch_odds` still live |
| I2 note | `/unavailable\|as-of\|—/i` | success notes; `source:"The Odds API"` on deny |
| I1 S2/S3 | status ∈ {200,401}; source none **or** snapshot | 401 before Odds; Railway pay |
| I3 | warm 200 + `probe.hits===[]` | assemble via origin; Railway CFB live |
| I4/I6 | `rateLimit()` 11th call is 429; compare body `none` | `proxy.ts` not executed; compare limiter is 100/min not 10 |
| L1 | `classifyAltSnapshot` tiers | POST client snapshot; live adapter |
| `odds-compare-payload` | `route` string `not.toContain("fetchOddsComparison")` | other modules pulling |
| `warm-page-data-cron.test.ts` | `toContain` / `not.toContain` | runtime |
| `installOddsHostFailOnHit` | `globalThis.fetch` host allowlist | `requests`/`httpx` on Railway; in-process `oddsAcquire` that throws before fetch (counted as 0 hits, which is correct for deny, **silent** if a new client bypasses `fetch`) |

U1/U2 (direct `oddsAcquire` + `fetch` spy) and I5 (compare miss → none + 0 hits) are the non-vacuous cores. They do not cover G-PROXY-LIVE / G-CFB-RAIL-LIVE / G-S6-CLIENT-SNAP.

C7 contract (1401f586 §7) asked for msw fail-on-hit against `*.the-odds-api.com` **and** “0 Odds client invocations.” The suite never spies `oddsAcquire` / `fetch_odds` call counts. A refactor that used `http.request` or Railway would stay green.

`odds-api.test.ts` / `cfb-edge-board-asof.test.ts` wrap pulls in `withAuthorizedOddsJob` (`NODE_ENV=test` + `TEST_ODDS_ACQUIRE_JOB_ID`). Those tests **exercise the allow path**, not fail-closed. Fine if labeled. They must not be cited as I5 evidence.

---

## 7. Beat/worker vs ALS leak

**Beat/worker accidentally broken:** **No, not by this tip.** Diff does not touch Celery beat, `tasks.py`, or `odds_api.py`. Authorized pull-odds cadence remains in source. S10’s oracle is still vacuous (G-S10-GREP).

**Ordinary web inheriting job context:** `enterAuthorizedOddsJobContext` is test-only. ALS cannot be set on a production request today.

**G-ALS-OMIT-INTENT (MEDIUM, latent):**

```41:48:apps/web/lib/odds-acquire/acquire.ts
  if (args.intent && args.intent !== "job") {
    deny(caller, { intent: args.intent });
  }
  if (!isAuthorizedOddsAcquireContext()) {
    deny(caller);
  }
```

Omitting `intent` does not deny. `paidOddsGet`, futures, preseason, widget, and `fetchAlternateSpreadSnapshot` omit it. If a future registered web job sets ALS and then **in-process** calls `loadAssembledEdgeBoardRows` / `loadNflFuturesOdds` / `fetchAlternateSpreadSnapshot`, those “request” functions inherit the job store and **pay**. Warm today uses outbound HTTP (new isolate) — safe. The boundary is “ALS present,” not “this call is a job.”

`vitest.setup.ts` sets `NODE_ENV=test`, which makes `TEST_ODDS_ACQUIRE_JOB_ID` registered. Fail-closed tests delete the allow flag. Parallel workers sharing `process.env.ODDS_WEB_PAID_FETCH_ALLOW` (U2 sets `"1"`) are a test-isolation smell, not a prod leak.

---

## 8. REGISTERED_ODDS_ACQUIRE_JOB_IDS / ODDS_WEB_PAID_FETCH_ALLOW misuse

**Empty Set:** correct for “no web acquisition job without a later CLEAR.” `isRegisteredOddsAcquireJob` is `Set.has` OR (`NODE_ENV==="test"` && `test-odds-acquire`).

**Flag:** absent ≠ `"1"` ⇒ `isAuthorizedOddsAcquireContext()` false. Matches C2 default DENY.

**G-FLAG-EMPTY-SET (MEDIUM):** matrix rollback says `ODDS_WEB_PAID_FETCH_ALLOW=1` “re-enables acquisition only for registered job contexts.” On this tip the Set is empty, so flag=`1` + valid `CRON_SECRET` still cannot acquire. That is fail-closed (good) and a **semantic trap** if ops set the flag expecting job refresh to resume on web. Beat/worker does not read this flag (good). No test asserts `REGISTERED_ODDS_ACQUIRE_JOB_IDS.size === 0` under `NODE_ENV=production`.

**C1 barrel:** `lib/odds-acquire/index.ts` is `server-only`. `acquire.ts` / `hosts.ts` / `odds-adapter.ts` are not. Callers import `acquire.ts` directly. Client `OddsCompareBoard` imports **types only** from `odds-api` (tree-shake dependent). Not a demonstrated browser pay path.

**C7 ledger / E1:** not on the tip. `odds_api.py` still logs remaining/used/last with no web `caller=`. E1 env attestation is not in `.github/workflows/pr-check.yml` (only `check-odds-acquire-choke.sh`).

---

## Reachability vs Cursor claim (this tip, not a grade)

| # | Cursor claim | Codex on tip a2f86c44 |
|---|---|---|
| S1 compare | DENIED + SoT | **Web DENIED** (none). **No SoT read.** CDN caches none 6h. |
| S2 edge-board NBA/… | DENIED | **Web DENIED** via choke. Assemble still *attempts* `pullOddsRows`. |
| S3 ncaam/today | DENIED | **Web no direct Odds.** **Railway `_fetch_odds_ncaab` still live** if secret/cache miss. |
| S4 NFL/CFB boards | DENIED even if gate open | NFL assemble skip/reuse **holds**. **CFB Railway live on warehouse miss.** Gate is the only CFB stop today. |
| S5 warm | DENIED | Warm does not acquire. **Latent CFB Railway pay if gate opens.** I3 does not prove it. |
| S6 line-curve | UNAVAILABLE_HONEST | GET honest. **POST client snapshot fabricates fresh book alts.** |
| S7 Pro futures | UNAVAILABLE_HONEST | Direct pay denied. **Source string still “The Odds API.”** Ungated Pro fair-lines SSR can still **pay via Railway**. |
| S8 widget | DENIED | Dummy key → acquire → deny → 404. Holds on web choke. |
| S9 model request-path | DENIED (C8 / C10) | **C8 absent.** Live defaults remain. C10 is env, not this commit. |
| S10 beat | AUTHORIZED_JOB | **Source untouched.** Oracle is a grep. |

---

## Recommended tests / locks (Codex does not implement)

Priority if CoS forwards a repair DRAFT (still no merge / no paid Odds / no flag / no R4):

1. **C8 on model-service** before any A1 talk: `ODDS_API_REQUEST_PATH_ALLOW` default deny on `fetch_odds` unless Celery task id ∈ sanctioned beat jobs. GET `/nfl/fair-lines`, `/cfb/edge-board-odds`, `/edge-board/ncaam/today` must not call Odds. (Needs CLEAR if treated as new work; named here because B1 fails without it.)
2. **Web fair-lines default `oddsMode:"skip"`** on every user-read caller listed in G-PROXY-LIVE; test the query string.
3. **CFB `current_cfb_odds_events(allow_live=False)`** on the request route; I3 must run assemble **through** warm’s fetch (not a stubbed origin) with a Railway mock that fails on Odds.
4. **S6** POST with unsigned `capturedAt=now` + fake alts → `researchOnly:true`, `reason:alt_market_unavailable`, no `priceAlternateSurface` on client prices.
5. **Invocation counter:** spy `oddsAcquire` + model `fetch_odds`; I1–I6 assert `toHaveBeenCalledTimes(0)` (or deny-before-fetch). Drop note regex / `"False"`-class greps as sufficiency proofs.
6. **S7** denied bundle `source!=="The Odds API"`; page banner “Market data unavailable / as-of”; I2 forbids `no_key` when dummy key is set.
7. **U3 grep** include `services/model-service/src/routes/**` as “must not add new request-path host literals without C8.”
8. **ALS:** request-path wrappers pass `intent:"request"` (always deny) even if ALS is set.

Do not “fix” by setting `ODDS_WEB_PAID_FETCH_ALLOW=1` or registering `warm-page-data`. Do not remove `ODDS_API_KEY` (R4 HOLD). Do not touch beat schedules.

---

## Non-actions (this lane)

- Did not implement repairs or edit #650 impl.
- Did not merge, deploy, restart, set-variables, or spend Odds.
- Did not grade PASS / FAIL as a ship verdict.
- Did not treat C10 Offline as proven on this box (not probed).
- Did not reopen F2, CERT, Coming Soon, or NFL NO-GO.

Signed: Codex independent challenge · t4662u R1–R3 · tip `a2f86c448dccce91a1a823cbc4dde0413871e117` · 2026-10-28
END
