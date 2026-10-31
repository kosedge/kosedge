# CODEX_CHALLENGE — t4668u R1–R3 FULL ACQUISITION GRAPH v2

Lane: **Codex / independent challenge** (Ryan DECISION **a984759c** · COS_ORDER **t4668u** · FREEZE **t4670u**)
Not the implementer. No repairs. No merge / deploy / paid Odds / env / F2 / CERT.
Does **not** self-grade PASS. IMV grades the tip.

| pin | value |
|---|---|
| Challenged tip (FROZEN) | `9e8518521116042051930628bd2d5cc5cca164f8` · #650 DRAFT `cursor/odds-fail-closed-r1-r3-d90e` |
| Freeze | t4670u — this paper grades **that SHA only**. If #650 HEAD moves, this paper is stale; do not retarget. |
| Lineage | `a2f86c44` → `8fd58c63` → `6962faeb` → `e4ca15c1` → `2d330166` → **`9e851852`** |
| Delta vs `2d330166` | eslint-only: `let ncaamCache` → `const ncaamCache` in `apps/web/app/api/edge-board/ncaam/today/route.ts` (dead after Railway proxy write removed). Acquisition graph unchanged. |
| Authority | COS_ORDER t4668u · FREEZE t4670u · DECISION **a984759c** · prior Codex paper sha256 **4acaea8b…** (#651, tip `a2f86c44`) · CoS RECEIPT **8219df64** |
| Parent design | ODDS_FAIL_CLOSED_DESIGN · receipt `a2f86c44` (Cursor claim: 7 DENIED / 1 AUTHORIZED_JOB / 2 UNAVAILABLE_HONEST) |
| Prior vacuous class | **88a08cae** / **75141507** G-C7-VACUOUS · #651 G-C7-VACUOUS-2 |
| Scope | Full acquisition graph: **apps/web (Vercel) + model-service (Railway)**. Cross-service B1. E6 mutation. Line-curve client snapshot not authoritative. HIGH S7 / NCAAM / I3 / C7 in disposition. |
| Verdict of this paper | **gaps-cleared-for-IMV** · **NOT** PASS · **NOT** a ship ticket · **NOT** CHALLENGE_FILED as a RETURN |

Hard locks honored: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · A1 restore HOLD · B HOLD · R4 emergency HOLD.

Codex did **not** call the-odds-api (paid or free). Did not change env, deploy, merge, or repair. Did not follow commits after `9e851852`.

---

## Verdict (read this first)

Ryan: do **not** PASS on Vercel-only paths. This hunt walked both sides.

The three **BLOCKING** gaps from Codex #651 (`G-PROXY-LIVE`, `G-CFB-RAIL-LIVE`, `G-S6-CLIENT-SNAP`) are **closed on tip `9e851852`** with request-path wraps **and** mutation oracles (`_boom` / runtime POST / query-string). HIGH `G-S7-SOURCE-LIE`, `G-NCAAM-PROXY`, `G-I3-STUB` are also **closed**. `G-C7-VACUOUS-2` is **downgraded to MEDIUM residual** (named gates now have non-grep oracles; leftover greps / I1-S3 `snapshot` OR remain).

No **new BLOCKING** user-read pay path was found on the frozen tip (web choke + Railway C8 + CFB `allow_live=False` + line-curve ignore-snapshot). Client-bundle/server-only work at `2d330166` holds at `9e851852`; the eslint `const` does not reopen NCAAM proxy.

**IMV may grade.** This paper does **not** PASS the tip, does **not** authorize merge/deploy/flag/paid Odds, and does **not** treat residuals as closed.

---

## What the frozen tip already does (not a pass)

Facts so IMV does not treat this paper as a redo of Cursor discovery or of #651.

- Web choke still exists: `apps/web/lib/odds-acquire/acquire.ts` is the only `apps/web` runtime constructor of `https://api.the-odds-api.com` / `https://widget.the-odds-api.com`. It now starts with `import "server-only"` (`2d330166`, still on this tip).
- `REGISTERED_ODDS_ACQUIRE_JOB_IDS` is an empty `Set`. No production web job can enter ALS. `WARM_PAGE_DATA_JOB_ID` is refused at `enterAuthorizedOddsJobContext`.
- `ODDS_WEB_PAID_FETCH_ALLOW` must equal `"1"` **and** ALS must already be a CRON_SECRET-verified registered job. Flag alone does not acquire.
- `/api/odds/[sport]/compare` still does not call `fetchOddsComparison`. Cache miss / Redis absent returns `{source:"none",reason:"paid_fetch_denied"}`.
- Rate-limit exemption is Bearer `CRON_SECRET` only.
- **Cross-service B1 (the #651 BLOCKING):** `fetchNflFairLines` defaults `oddsMode="skip"` and coerces `"live"` → `"skip"`. Model-service GET `/nfl/fair-lines` defaults `odds_mode="skip"`. Explicit `live` and reuse-without-supply fallthrough remap to skip unless `ODDS_API_REQUEST_PATH_ALLOW=1` (C8, unset = deny). `/nfl/edges/today` and `/mlb/edges/today` skip `fetch_odds` when C8 unset.
- **CFB Railway:** `/cfb/edge-board-odds` calls `current_cfb_odds_events(allow_live=False)`. Function default is `False`. Warehouse miss → `source=none`, no `_live_pull_events`.
- **S6:** line-curve POST never prices `body.snapshot`. Always `researchOnly` + `alt_market_unavailable`. No `getLineCurve` on the HTTP route.
- **S7:** denied NFL/CFB futures `source="unavailable"` (not `"The Odds API"`). CFB page prints “Market data unavailable / as-of” unless `status==="ok"`. I2 asserts source ≠ The Odds API and status ≠ `no_key`.
- **NCAAM:** web `/api/edge-board/ncaam/today` does not fetch Railway. Railway `/edge-board/ncaam/today` returns empty + `paid_fetch_denied` when C8 unset (does not call `_fetch_odds_ncaab`).
- **E6:** I-series `loadISeriesModules()` stubs dummy keys + `vi.resetModules()` before `env.ts` parse. `vitest.setup.ts` seeds dummy keys. E6 harness asserts `getOddsApiKeys() === [DUMMY_ODDS_KEY]`.
- **I3:** `odds-fail-closed-proxy.test.ts` runs warm’s origin fetch into real `assembleGET` and asserts `assembleHits.length >= 1` and `oddsHits === []`.
- **Client-safe acquire:** desks import `bookDisplay` from `lib/odds-book-display.ts`. `OddsCompareBoard` is `import type` only from `odds-api`. Known `'use client'` files do not value-import `odds-api` / `odds-acquire`.
- Tip delta `2d330166..9e851852` is **one token** (`let` → `const`). Beat/worker source is still not gated by C8 (authorized residual).
- Cursor does not self-grade PASS on the receipt.

---

## Full acquisition graph (frozen tip)

```text
BROWSER ('use client')
  OddsCompareBoard -----------> GET /api/odds/:sport/compare
  EdgeBoardSportClient -------> GET /api/edge-board/:sport/assemble
  Nfl*DeskClient -------------> bookDisplay (odds-book-display only)
  LineCurveResearchPanel -----> GET /api/line-curve  (no snapshot SoT)

VERCEL / apps/web  (user-read)
  compare                    cache/Redis only; miss = none / paid_fetch_denied
  edge-board/:sport/today    assemble / snapshot / none — pullOddsRows -> oddsAcquire DENY
  edge-board/ncaam/today     NO Railway hop; ncaamCache is const null; always deny
  edge-board/:sport/assemble pullOddsRows -> oddsAcquire DENY; NFL fair-lines skip|reuse
  line-curve GET/POST        lineCurveUnavailablePayload(); snapshot ignored
  line-curve/optimize        model/joint math on client legs; no getLineCurve / no Odds
  odds-widget/:sport         oddsAcquire -> PaidFetchDenied -> 404
  futures / preseason SSR    oddsAcquire -> unavailable / source=unavailable
  cron/warm-page-data        public GET assemble only (not an acquire job)
  fetchNflFairLines          odds_mode=skip (live coerced); persist default 0
       |
       v
RAILWAY / model-service  (same user-read request)
  GET/POST /nfl/fair-lines   default skip; live + reuse-without-supply => C8 or skip
  GET /nfl/edges/today       C8 else paid_fetch_denied (no fetch_odds)
  GET /mlb/edges/today       C8 else paid_fetch_denied
  GET /cfb/edge-board-odds   current_cfb_odds_events(allow_live=False); warehouse or none
  GET /edge-board/ncaam/today C8 else paid_fetch_denied (httpx NCAAB only if C8=1)

NOT user-read (inventory, not a #650 close claim)
  Celery beat pull_odds_snapshot / run_nfl_market_simulations  (AUTHORIZED_JOB; no C8)
  POST /api/jobs/pull-odds-snapshot (+ other /api/jobs/*)      (pre-existing enqueue; no C8)
  fetch_odds() itself                                          (no central C8; route wraps only)
```

B1 on this tip is **dual-sided**: web will not ask Railway for `live`, and Railway will not pay if asked, unless C8=`1` (env CLEAR / A1 HOLD — not set here).

---

## Severity index

Severity: **BLOCKING** = would RETURN / FAIL if IMV applies B1 / S4 / S5 / S6 / C7-tests strictly · **HIGH** · **MEDIUM** · **LOW** · **NOTE**.

| id | gap | hunt | severity on `a2f86c44` (#651) | severity on frozen `9e851852` |
|---|---|---|---|---|
| G-PROXY-LIVE | User-read SSR/API defaults live into `/nfl/fair-lines` → `fetch_odds`; edges/today hops | B1, Railway | **BLOCKING** | **CLOSED** |
| G-CFB-RAIL-LIVE | `/cfb/edge-board-odds` `allow_live=True`; warehouse miss live-pulls | S4/S5 | **BLOCKING** | **CLOSED** |
| G-S6-CLIENT-SNAP | Line-curve POST prices client `snapshot` as fresh book | S6 | **BLOCKING** | **CLOSED** |
| G-S7-SOURCE-LIE | Denied futures `source="The Odds API"` | S7 | **HIGH** | **CLOSED** |
| G-NCAAM-PROXY | ncaam/today proxies Railway `_fetch_odds_ncaab` | S3 | **HIGH** | **CLOSED** |
| G-I3-STUB | I3 warm `fetch(origin)` stubbed; never executes assemble | S5 / C5 | **HIGH** | **CLOSED** |
| G-C7-VACUOUS-2 | Greps / stubbed fetch cannot prove 0 invocations | C7 / 88a08cae | **HIGH** | **MEDIUM residual** (named gates now have `_boom` / runtime; leftover greps remain) |
| G-ALS-OMIT-INTENT | `oddsAcquire` omit-intent ≠ deny | ALS | **MEDIUM** | **MEDIUM residual** |
| G-COMPARE-NONE-CDN | Denied compare `s-maxage=21600` | B2 | **MEDIUM** | **MEDIUM residual** |
| G-S1-NO-SOT | Compare never reads `odds_snapshots` | S1 | **MEDIUM** | **MEDIUM residual** |
| G-FLAG-EMPTY-SET | Flag=`1` + cron still cannot acquire (empty Set) | rollback prose | **MEDIUM** | **MEDIUM residual** |
| G-C1-NOT-SOLE / client-bundle | `acquire.ts` had no `server-only`; `odds-api` client-importable | C1 / `2d330166` | **MEDIUM** | **MEDIUM residual** (`acquire.ts` now `server-only`; `odds-api.ts` still not) |
| G-E1-ABSENT | No E1 attestation; C7 ledger; C8 was absent | E1/C7/C8 | **MEDIUM** | **MEDIUM residual** (C8 function exists; still not inside `fetch_odds`) |
| G-S10-GREP | Beat “untouched” oracle is string contains | S10 | **LOW** | **LOW residual** (diff fact: beat/worker source untouched) |
| G-NCAAM-DEAD-CACHE | `const ncaamCache = null`; comment still says cache is SoT | tip `9e851852` | n/a | **NOTE** (fail-closed stronger; SoT comment is a lie) |
| G-FETCH-ODDS-UNGATED | `fetch_odds` / `_fetch_odds_ncaab` have no central C8 | defense-in-depth | unnamed | **MEDIUM residual** |
| G-JOBS-UNAUTH | `POST /api/jobs/pull-odds-snapshot` no auth / no C8 | full graph | unnamed | **NOTE** (pre-existing; not user-read B1; not a #650 close claim) |
| G-OPTIMIZE-CLIENT-QUOTES | optimize POST prices supplied `legA`/`legB` | S6 secondary | NOTE | **LOW residual** |
| G-C8-REOPEN | `ODDS_API_REQUEST_PATH_ALLOW=1` re-opens request-path live | A1 HOLD | named | **RESIDUAL** (documented; not set on this tip) |
| G-I1-S3-OR | I1 S3 still accepts `source==="snapshot"` as pass | C7 leftover | part of HIGH | **LOW residual** (proxy runtime is strict) |

No row below asserts occurrence of the 2026-10-27 credit burn, MAE, CERT, PLAY, or that beat/worker was broken by this tip. Hard-lock filenames are not in the `deploy-vercel…9e851852` delta.

---

## 1. G-PROXY-LIVE — CLOSED (full graph, not Vercel-only)

**#651:** `fetchNflFairLines` defaulted `oddsMode:"live"` and omitted the query param; Railway GET defaulted `"live"` → `fetch_odds`. Prediction-market / execution / survivor / season-engine paid on Railway without touching `oddsAcquire`. C8 did not exist.

**This tip:**

Web (`apps/web/lib/nfl-fair-lines.ts`):

```text
const requestedMode = params.oddsMode ?? "skip";
const oddsMode = requestedMode === "live" ? "skip" : requestedMode;
…
url.searchParams.set("odds_mode", oddsMode);   // always set on GET
```

User-read callers inspected (prediction-market, execution, survivor, season-engine, resolve-kei, edges-desk, `/api/nfl/fair-lines`, pickem) do **not** pass `oddsMode:"live"`. Default skip + live-coercion would still save them if they did.

Railway (`services/model-service/src/routes/nfl.py`):

- GET `/nfl/fair-lines` Query default `"skip"`.
- `_normalize_nfl_fair_lines_odds_mode` unknown → `"skip"`.
- `_resolve_nfl_fair_lines_market_events`: skip returns empty; reuse with supplied list returns that list; reuse-without-supply (`supplied_events is None`) would fall through to live **but** then `request_path_paid_odds_allowed()` must be true or it returns skip. Explicit live is the same C8 gate.
- GET `/nfl/edges/today`: C8 unset → `odds_feed_error="paid_fetch_denied"`; `fetch_odds` only in `else`.
- POST `/nfl/fair-lines` empty reuse (`odds_events=[]`, `odds_payload=[]`) sets `supplied=None` → live fallthrough → C8 skip. Mutation test `test_post_reuse_empty_denied_when_c8_unset`.

MLB (`routes/mlb.py` `/edges/today`): C8 unset returns `{source:none, reason:paid_fetch_denied}` before `fetch_odds`.

C8 (`services/model-service/src/services/odds_api.py`):

```text
def request_path_paid_odds_allowed() -> bool:
    return os.getenv("ODDS_API_REQUEST_PATH_ALLOW", "").strip() == "1"
```

Unset / any other value denies. `fetch_odds` itself is **not** gated (see G-FETCH-ODDS-UNGATED).

**Mutation oracles (would fail if wrap removed):**

| test | mutation |
|---|---|
| `test_nfl_fair_lines_odds_mode.py::test_get_default_odds_mode_skip_does_not_call_fetch_odds` | omit default skip / restore live default |
| `…::test_get_odds_mode_live_denied_when_c8_unset` | remove C8 remap |
| `…::test_reuse_without_supply_denied_when_c8_unset` | restore live fallthrough |
| `…::test_post_reuse_empty_denied_when_c8_unset` | empty POST pays |
| `test_nfl_routes.py::test_nfl_edges_today_does_not_fetch_odds_when_c8_unset` | remove edges wrap |
| `test_mlb_routes.py::test_mlb_edges_today_does_not_fetch_odds_when_c8_unset` | remove MLB wrap |
| `odds-fail-closed-proxy.test.ts` runtime | default GET / `{oddsMode:live}` must send `odds_mode=skip` |

Direct Railway curl with `odds_mode=live` and C8 unset is **skip**, not pay. Web cannot ask for live. Dual deny.

**persist=1** does not re-open fetch when C8 unset (`test_nfl_projection_endpoints.py`). Warehouse paint of Current on skip is SoT read, not a live pull.

---

## 2. G-CFB-RAIL-LIVE — CLOSED

**#651:** web `loadCfbCurrentMarketRows` `upstreamFetch`es `${MODEL_SERVICE_URL}/cfb/edge-board-odds`; route called `current_cfb_odds_events()` with default `allow_live=True`; warehouse miss → `_live_pull_events` → `fetch_odds(sports/americanfootball_ncaaf/odds)`. S4/S5 “DENIED even if gate opens” was false.

**This tip:**

- `routes/cfb.py` `/edge-board-odds` → `current_cfb_odds_events(allow_live=False)`.
- `cfb_edge_board_odds.py` default `allow_live: bool = False`.
- Warehouse hit → `odds_snapshots` (beat SoT). Miss + not allow_live → `source=none`, `reason=warehouse_empty`. `_live_pull_events` is not reached.
- Web `apps/web/lib/cfb-edge-board-odds.ts` is `server-only`; order is Railway warehouse → shipped fallback → none. Type `vercel_live` remains in the union; I1 S4 asserts `market.source !== "vercel_live"`. No production caller passes `allow_live=True` (repo grep).

**Mutation oracles:** `test_default_allow_live_is_false_on_warehouse_miss` (revert default True → `_boom`); `test_cfb_edge_board_odds_route_never_live_pulls`; proxy grep `allow_live=False` and not `return current_cfb_odds_events()`.

Gate-open CFB assemble still cannot live-pull on Railway. I3 warm → assemble (proxy runtime) + host fail-on-hit = 0 Odds hits.

---

## 3. G-S6-CLIENT-SNAP — CLOSED (client snapshot not authoritative)

**#651:** line-curve POST treated `body.snapshot` as fresh book alts (`researchOnly:false`). Fabricate, not just pay.

**This tip:** after required-field checks, POST returns `lineCurveUnavailablePayload()` and never calls `getLineCurve` / `classifyAltSnapshot` / `priceAlternateSurface`. Comment names G-S6-CLIENT-SNAP.

Runtime: `odds-fail-closed-proxy.test.ts` POSTs unsigned `capturedAt=now` + Missouri fixture alts → `researchOnly:true`, `reason:alt_market_unavailable`, no `curve.points`, `probe.hits===[]`.

`getLineCurve` still exists on `lib/line-curve/service.ts` and will trust `req.snapshot` if a caller sets it. HTTP routes do not call it (containment grep + route source). `allowLiveOddsFetch` remains opt-in on the service; routes do not set it. Adapter `fetchAlternateSpreadSnapshot` still goes through `oddsAcquire` (I-series S6 live adapter → `unavailable_alt_market`, 0 hits).

**Residual (LOW):** `/api/line-curve/optimize` POST with supplied `legA`/`legB`/`book` runs `optimizeTwoLegLineCurve` (model/joint math on client-trusted quotes). No Odds HTTP. Same secondary class as #651. I1 S6 optimize-without-legs is honest unavailable.

---

## 4. HIGH disposition (stay on the card even though closed)

### G-S7-SOURCE-LIE — CLOSED

`emptyBundle` now: `source: status === "ok" ? "The Odds API" : "unavailable"` (NFL). CFB uses `CFB_FUTURES_ODDS_SOURCE` only when `ok`. `/pro/cfb/futures` prints “Market odds from {source}” only when `market.status === "ok"`; else “Market data unavailable / as-of.”

I2 S7: status `unavailable` (not `no_key`), source `unavailable` (not `"The Odds API"`), note `/unavailable|as-of/i` (em-dash success-path loophole from #651 is gone from the source assert). Dummy keys are required (E6) so `no_key` is not a vacuous pass.

Mutation: revert emptyBundle source to always `"The Odds API"` → I2 fails.

### G-NCAAM-PROXY — CLOSED

Web route: no `tryModelService`, no `fetch(…ncaam/today)`. After optional `INTERNAL_API_SECRET`, in-process `ncaamCache` (see NOTE) then `{source:none, reason:paid_fetch_denied}`. Runtime proxy test: 0 Railway hops, 0 Odds host hits.

Railway: C8 unset → empty + `paid_fetch_denied` before `_fetch_odds_ncaab`. Mutation: `test_ncaam_request_path_odds_deny.py` `_boom` on `_fetch_odds_ncaab` (cache cleared).

**NOTE G-NCAAM-DEAD-CACHE (this tip’s only unique delta):** `const ncaamCache = null` — never written after proxy removal. `if (ncaamCache)` is dead. Comment still says “Cache is the only SoT read.” Fail-closed is **stronger** (always deny). CDN still ships deny at `s-maxage=21600` (same class as compare). Not a pay escape.

Railway `_CACHE` is checked **before** C8. Cache is only populated after a C8=1 live fetch. Default-deny (C8 unset, cold) cannot warm it. Residual of **C8=1 reopen**, not of default ship state.

### G-I3-STUB — CLOSED

`odds-fail-closed-proxy.test.ts` “I3: warm origin fetch runs assemble GET (not a dummy 200)” intercepts `/assemble`, calls real `assembleGET`, requires `assembleHits.length >= 1` and `oddsHits === []`. This is the #651 recommended lock.

Companion I3 S5 in `odds-fail-closed-request-paths.test.ts` still runs `warmGET` **and** a separate `assembleGET` (weaker). Do not cite I3 S5 as the assemble-through-warm proof. The proxy test is the proof.

---

## 5. E6 mutation (I-series not vacuous on empty keys)

#651 / 88a08cae class: dummy-key-absent → loaders return `no_key` / never reach acquire → “denied” looks green.

This tip:

- `vitest.setup.ts` seeds `ODDS_API_KEY*` / `ODDS_WIDGET_ACCESS_KEY` before env parse.
- `loadISeriesModules()` : `stubDummyOddsKeys()` + `vi.resetModules()` + stub again, then dynamic import.
- Explicit test: `E6 harness: dummy keys parse into env before loaders` ties `getOddsApiKeys()` and `env.ODDS_API_KEY` to `DUMMY_ODDS_KEY`, and asserts `ODDS_WEB_PAID_FETCH_ALLOW !== "1"`.
- I2 forbids `no_key` when dummy key is set.

Mutation: remove setup keys **and** all `stubDummyOddsKeys()` → E6 fails; I2 can no longer pass via `no_key`. Removing only the I-series stub while leaving setup keys still parses — the harness test is the anti-vacuous pin.

---

## 6. Client-bundle / server-only (NEW tip hunt, graph unchanged at `9e851852`)

`2d330166` closed the Next client-build break: desks imported `bookDisplay` from `odds-api.ts`, which pulled `oddsAcquire` (`node:async_hooks`) into the browser chunk. Labels live in `lib/odds-book-display.ts`. `acquire.ts` is `server-only`. `9e851852` does not touch that graph.

| check | on frozen tip |
|---|---|
| `'use client'` value-import of `odds-api` | **none** (only `OddsCompareBoard` `import type`) |
| `'use client'` import of `odds-acquire` | **none** |
| `acquire.ts` `server-only` | **yes** (line 1) |
| `odds-acquire/index.ts` `server-only` | **yes** |
| `odds-api.ts` `server-only` | **no** — still dynamic-imports acquire inside `paidOddsGet` |
| `odds-book-display.ts` | labels only; no acquire / no Node builtins |
| proxy lock | 3 client files + `acquire.ts` contains `server-only` |

**No demonstrated browser pay path.** Residual: a **new** `import { bookDisplay } from '@/lib/odds-api'` in a client file would either fail the Next client build (dynamic `server-only` import) or re-open the `2d330166` class. There is no eslint/module boundary on `odds-api.ts` itself. Test does not scan every `'use client'` file (repo grep of `components/**` + `app/**` found no other value imports).

`9e851852` eslint `const` is not a bundle change.

---

## 7. G-C7-VACUOUS-2 — MEDIUM residual (not HIGH RETURN)

Named BLOCKING/HIGH gates now have non-vacuous oracles (`_boom` on `fetch_odds` / `_fetch_odds_ncaab` / `_live_pull`; runtime fair-lines query string; runtime snapshot POST; runtime ncaam no-Railway; I3 assemble dispatch; I2 source ≠ The Odds API; E6 key parse). That is enough to **downgrade** the 88a08cae reopen from HIGH RETURN to leftover-oracle residual.

Still vacuous / incomplete (do not cite as sufficiency):

| oracle | still cannot catch |
|---|---|
| U3 / `check-odds-acquire-choke.sh` | **web-only** `git grep the-odds-api.com`; misses `services/model-service` (`edge_board.py` still has `ODDS_API_BASE = "https://api.the-odds-api.com/v4"`; `odds_api.py` `BASE_URL`) |
| S10 | two `toContain` strings in beat + client; not a runtime “untouched” proof (diff is the stronger fact) |
| I1 S3 | `reason===paid_fetch_denied \|\| source==="snapshot"` — snapshot OR is leftover; proxy runtime is strict |
| I3 S5 (request-paths) | warm + separate assemble; not through warm’s fetch |
| I4/I6 | `rateLimit()` direct; `proxy.ts` not executed |
| L1 | `classifyAltSnapshot` only; HTTP POST is the proxy S6 test |
| `installOddsHostFailOnHit` | `globalThis.fetch` host allowlist; cannot see Railway `requests`/`httpx` |
| no `oddsAcquire` / `fetch_odds` call-count ledger | C7 “0 invocations” as a single counter is still absent |

A new Railway route that calls `fetch_odds` without C8 would stay green on the web suite (U3 still web-only). Model-service unit files cover the **known** request routes only.

---

## 8. Residuals (not closed this tip — leave in disposition)

### MEDIUM (from #651, still true)

- **ALS omit-intent:** `if (args.intent && args.intent !== "job") deny`. Omitting `intent` does not deny. Production loaders (`paidOddsGet`, futures, preseason, widget, `fetchAlternateSpreadSnapshot`) omit it and fail on ALS + empty registry + flag. Latent: a future registered web job that in-process calls request loaders would pay. Warm today uses outbound HTTP (new isolate) — safe. Empty Set is the current backstop, not `intent:"request"`.
- **Compare CDN `none` 6h:** `CACHE_HEADERS` `s-maxage=21600` on deny. NCAAM deny uses the same TTL. Line-curve none is `no-store`.
- **S1 no SoT:** compare never reads `odds_snapshots`; never writes cache on miss; always `none` when Redis empty. Fail-closed empty is allowed under B2; it is not a SoT read.
- **Flag empty Set:** `ODDS_WEB_PAID_FETCH_ALLOW=1` + valid cron still cannot acquire. Fail-closed (good) and a semantic trap if ops set the flag expecting web refresh. No test asserts `REGISTERED_ODDS_ACQUIRE_JOB_IDS.size === 0` under `NODE_ENV=production`.
- **C8 not inside `fetch_odds`:** new route + `from odds_api import fetch_odds` bypasses route wraps until review. `_fetch_odds_ncaab` is a second HTTP client (httpx + `ODDS_API_BASE`), C8 only at the route.
- **E1 / C7 ledger:** still absent on the tip.

### Beat / worker untouched (S10)

`celerybeat_schedule.py` still schedules `pull-odds-season-cadence` and `pull-odds-3am-refresh` → `TASK_PULL_ODDS_SNAPSHOT` on `CELERY_ODDS_QUEUE`. `tasks.py` `fetch_odds` / `fetch_odds_with_metadata` and `run_nfl_market_simulations` → `_fetch_live_nfl_market_lines_by_abbr` are **not** C8-gated. **Authorized residual.** This tip does not break them. S10 oracle remains grep.

Web does not POST `/api/jobs/*`.

### C8=`1` reopens (A1 HOLD / env CLEAR — not set here)

Setting `ODDS_API_REQUEST_PATH_ALLOW=1` re-opens:

1. GET `/nfl/edges/today` live NFL pull
2. GET `/mlb/edges/today` live MLB pull
3. GET `/edge-board/ncaam/today` `_fetch_odds_ncaab` (after process-cache miss)
4. GET/POST `/nfl/fair-lines` with `odds_mode=live` **or** reuse-without-supply fallthrough; `persist=1` can then write warehouse

Does **not** reopen: CFB `/edge-board-odds` (`allow_live=False` is hardcoded); beat/worker (already paid); web `fetchNflFairLines` live-coercion (web still sends skip unless a caller bypasses the helper).

Setting C8 is an env CLEAR, not a restore. Not done on this tip.

### NOTE — `POST /api/jobs/*` (full-graph inventory)

`services/model-service/src/main.py` `POST /api/jobs/pull-odds-snapshot` (and sibling job POSTs) enqueue Celery with **no** `Depends`, **no** `INTERNAL_API_SECRET`, **no** C8. Pre-existing. Not a user-read page/SSR/GET/preview path. Not introduced by #650. Not a failed close of G-PROXY-LIVE. Listed so Vercel-only review cannot pretend the Railway spend graph is only the five C8-wrapped routes.

---

## Reachability vs Cursor claim (frozen tip `9e851852`, not a grade)

| # | Cursor claim | Codex on `9e851852` |
|---|---|---|
| S1 compare | DENIED + SoT | **Web DENIED** (none). **No SoT read.** CDN caches none 6h. |
| S2 edge-board NBA/… | DENIED | **Web DENIED** via choke. Assemble still *attempts* `pullOddsRows` → deny. |
| S3 ncaam/today | DENIED | **Web no Railway.** **Railway C8-denied.** Dead in-process cache. |
| S4 NFL/CFB boards | DENIED even if gate open | NFL assemble skip/reuse **holds**. **CFB Railway `allow_live=False`.** Warehouse SoT only. |
| S5 warm | DENIED | Warm does not acquire. I3 proxy proves assemble dispatch + 0 Odds hits. |
| S6 line-curve | UNAVAILABLE_HONEST | GET honest. **POST ignores client snapshot.** Optimize prices supplied legs only. |
| S7 Pro futures | UNAVAILABLE_HONEST | Direct pay denied. **Source `unavailable` on deny.** Fair-lines SSR is skip + C8. |
| S8 widget | DENIED | Dummy key → acquire → deny → 404. Holds. |
| S9 model request-path | DENIED (C8) | **C8 present on known sync routes.** Default skip. `fetch_odds` itself unguarded. |
| S10 beat | AUTHORIZED_JOB | **Source untouched.** Oracle is a grep. |

---

## Client-bundle / server-only regression hunt (this freeze)

No **new** escape vs `2d330166`. The eslint `const` does not change NCAAM control flow (`ncaamCache` was already never assigned). Known client desks stay on `odds-book-display`. `acquire.ts` remains `server-only`. Hunt of `'use client'` files found no value import of `odds-api` / `odds-acquire`. Residual footgun: `odds-api.ts` is still a client-importable module that dynamic-imports acquire.

---

## Recommended locks if IMV RETURNS leftovers (Codex does not implement)

Not a repair ticket. Not a merge ticket.

1. Keep C8 **unset**. Do not treat `ODDS_API_REQUEST_PATH_ALLOW=1` as restore.
2. If a follow-up DRAFT is authorized: put C8 inside `fetch_odds` / `_fetch_odds_ncaab` (defense-in-depth); extend U3 grep to `services/model-service/src/routes/**`; drop I1 S3 `snapshot` OR; assert `REGISTERED_ODDS_ACQUIRE_JOB_IDS.size===0` in production NODE_ENV; pass `intent:"request"` on request wrappers.
3. Do **not** “fix” by setting `ODDS_WEB_PAID_FETCH_ALLOW=1` or registering `warm-page-data`. Do not remove `ODDS_API_KEY` (R4 HOLD). Do not touch beat schedules.

---

## Non-actions (this lane)

- Did not implement repairs or edit #650 impl.
- Did not merge, deploy, restart, set-variables, or spend Odds.
- Did not grade PASS / FAIL as a ship verdict.
- Did not follow commits after `9e851852` (t4670u FREEZE).
- Did not treat C10 Offline as proven on this box (not probed).
- Did not reopen F2, CERT, Coming Soon, or NFL NO-GO.

---

## Paper identity

| field | value |
|---|---|
| Path | `data/ops/CODEX_CHALLENGE_t4668u_R1_R3_FULL_GRAPH_v2.md` |
| Challenged tip | `9e8518521116042051930628bd2d5cc5cca164f8` |
| Verdict | **gaps-cleared-for-IMV** (not PASS, not CHALLENGE_FILED-as-RETURN) |
| Paper git SHA | (this commit, paper branch — not #650) |
| Paper sha256 | (stamped after write; see PR body) |

Signed: Codex independent challenge · t4668u FULL GRAPH v2 · FREEZE t4670u · tip `9e8518521116042051930628bd2d5cc5cca164f8` · 2026-10-28
END
