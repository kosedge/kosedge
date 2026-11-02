# t5178u W-FIX-B — path-read + isolated-write preflight + consumer inventory

- stamp: WORKER_B_PREFLIGHT_t5178u
- wall: 2026-11-02T12:55Z
- worker: Cursor B (`bc-c411ed1c-a2f5-5244-a637-767dacbaa875`)
- role: W-FIX-B consumer projections (HOLD until M0 contract tip from Worker A)
- repo: kosedge/kosedge
- worker_branch: `cursor/t5178u-wfixb-consumer-a875`
- starting_ref / base SHA: `deploy-vercel` @ **f5e3bb58ccbe5a8892fed2a01f347c2308394a2f**
- product tree: READABLE (local checkout + `git fetch origin deploy-vercel` confirmed tip)
- isolated write: this file + DRAFT PR only on the worker branch (not `deploy-vercel`)
- W-FIX-B implementation: **HELD** until Cos forwards M0 tip and ORDERS W-FIX-B (do not poll-nag A)
- Cos ACCEPT of this inventory tip: **585ee38c** / #706 DRAFT
- mismatch CONFIRMED: `nfl_hhl1_capture` absent on deploy-vercel @ f5e3bb58 — wire only A's published product-lineage contract, never a disconnected demo
- CERT=0 · IMPLEMENTED≠VERIFIED≠ACCEPTED · no merge/deploy · no access flip

Peer Worker A (M0 + W-FIX-A): `bc-7972bd58-1ea0-596f-8dad-4333dbdbc003`. B does not poll A.

## Isolated-write proof

```
git rev-parse --abbrev-ref HEAD
# cursor/t5178u-wfixb-consumer-a875

git rev-parse HEAD
# f5e3bb58ccbe5a8892fed2a01f347c2308394a2f
```

All subsequent W-FIX-B code lands only on this branch.

## Consumer seams (read on f5e3bb58)

| Seam | Path | Observed contract (do not change in this preflight) |
|---|---|---|
| NFL page-data API | `apps/web/app/api/nfl/fair-lines/route.ts` | `getProAccessState` 401 unauthorized; `isNflFairLinesCustomerSurfaceClosed()` → **HTTP 503** + `nflEdgeBoardAssembleUnavailablePayload()`; subscriber fetch `persistOdds: false` + `throwOnTransportError: true`; transport → `pageDataUpstreamErrorResponse` **503/504**; success → `pageDataPrivateJsonResponse` |
| NFL client / normalize | `apps/web/lib/nfl-fair-lines.ts` | `fetchNflFairLines` (server-only), `normalizeFairLine`, persist default `persist=0`; soft-empty only when `throwOnTransportError` is false; ledgerHealth `history_lagging` is **ops-only** (no FRESH/AGING/STALE product windows invented) |
| Client view types | `apps/web/lib/nfl-fair-lines-view-types.ts` | Client-safe subset (no server-only). UI must not invent missing as-of / lines |
| Closed-surface flags | `apps/web/lib/cfb-edge-board-public.ts` | `NFL_EDGE_BOARD_PUBLIC_ENABLED=false`; cert slot unbound; `isNflFairLinesCustomerSurfaceClosed()` true unless INTERNAL override + certified public paint |
| Honesty helper (non-NFL) | `apps/web/lib/fair-lines-api-board.ts` | `FAIR_LINES_HONESTY_SPORTS` = cfb/mlb/nba/nhl/wnba/ncaaf. **NFL excluded.** Do **not** copy `FAIR_LINES_HONEST_EMPTY_STATUSES` onto NFL |
| Page-data cache | `apps/web/lib/page-data-cache.ts` | Pro NFL fair-lines uses `pageDataPrivateJsonResponse` → `private,no-store` (Cache-Control + CDN-Cache-Control). Never cache 503/504 / empty / unauthorized |
| Upstream errors | `apps/web/lib/page-data-upstream.ts` | Timeout → 504; other transport → 503; both `cacheable: false` |
| Export | `apps/web/scripts/export_kei_lines_nfl.py` | @ f5e3bb58: `URLError` / `TimeoutError` / `JSONDecodeError` → **return 1** before OUT write. Blank home/away **silently skipped**; empty `lines` **exit 0**; non-numeric spread **uncaught ValueError**. Those three are W-FIX-B export-policy rows (DECIDED this package) |
| Export #697 tip | `0aad8d751ebec621c8f2fd06ad09e6e5357dddd9` | Transport refusal tests **RETAIN**. Script bytes unchanged on that tip. W-FIX-B must keep C10 refuse + add decided policy (non-actionable / nonzero; preserve prior valid OUT; atomic replace on fully valid) |
| UI page | `apps/web/app/(pro)/pro/nfl/fair-lines/page.tsx` | Closed → Coming soon + `FootballNumbersUnavailable`. Open path only renders `NflFairLinesClient` |
| UI client | `apps/web/components/pro/nfl/NflFairLinesClient.tsx` | Client-fetch `/api/nfl/fair-lines` (`cache: "no-store"`). `!res.ok` → error state. 503 with empty reasons must stay **unavailable**, never empty-success / honest-empty banner |
| View-model (board) | `apps/web/lib/nfl-edge-board-from-fair-lines.ts` | Fair-lines rows → Edge Board shape |
| View-model (KEI) | `apps/web/lib/resolve-kei-lines.ts` | `keiGamesFromNflFairLines` + `fetchNflFairLines` |
| Freshness (age fields only) | `apps/web/lib/nfl-data-freshness.ts` | Fixture age / probe only. 503 with empty blockers still non-ok. **Unknown age / history_lagging → UNKNOWN/refused — do not invent thresholds** |
| Eligibility pattern (do not widen) | `apps/web/lib/nfl-props-eligibility.ts` | Shape reference only. ALLOW_FIXTURE must stay fixture-channel (`fixture:true`). Do not widen to subscriber/betting |
| #664 validate attach | `services/model-service/src/services/nfl_hhl1_capture/*` | **ABSENT on deploy-vercel @ f5e3bb58.** Lives on #664 tip `7abf65a2`. M0/W-FIX-A must publish the shared contract onto product lineage; B wires that same tip, not a local demo copy |

## Additional actual consumers of `fetchNflFairLines` (must agree with API/UI/export/cache)

- `apps/web/lib/build-edge-board-rows.ts`
- `apps/web/lib/nfl-edges.ts`
- `apps/web/lib/nfl-slate.ts`
- `apps/web/lib/nfl-season-engine.ts` (dynamic import)
- `apps/web/app/api/nfl/season-engine/survivor/route.ts`
- `apps/web/app/api/nfl/season-engine/survivor/plan/route.ts`
- `apps/web/app/(pro)/pro/nfl/fantasy/pickem/page.tsx`
- `apps/web/app/(pro)/pro/prediction-market/page.tsx`
- `apps/web/app/(pro)/pro/[sport]/execution/page.tsx`

W-FIX-B scope is **fair-lines API / view-model / UI / export / cache**. Sibling `fetchNflFairLines` callers stay closed-gate + persistOdds=false; do not flip access or invent lines for them.

## Existing tests to reuse as patterns (not to copy HONESTY enum)

- `apps/web/__tests__/lib/nfl-fair-lines-persist.test.ts` — persist=0 / persistOdds:false source-lock
- `apps/web/__tests__/lib/nfl-fair-lines-production-cert.test.ts` — closed surface + Coming soon ON
- `apps/web/__tests__/lib/nfl-page-data-cache.test.ts` — private,no-store on NFL fair-lines
- `apps/web/__tests__/lib/nfl-page-data-timeout.test.ts` — throwOnTransportError
- `apps/web/__tests__/api/fair-lines-honesty.test.ts` — **non-NFL** honesty (pattern only)
- `apps/web/__tests__/lib/fair-lines-api-board.test.ts` — honesty helper (NFL excluded)
- `#697` `apps/web/tests_pipeline/test_export_kei_lines_nfl_c10_refuse.py` — transport refuse RETAIN

## Export policy DECIDED (implement after M0 tip; not in this preflight)

| Case | Required outcome | Must NOT |
|---|---|---|
| Closed / uncertified NFL surface | 503 + unavailable payload | 200 + empty games as "no slate" |
| Upstream transport fail | 503/504 (API) / exit 1 (export) | invent lines |
| Unexpected empty payload / empty `lines` | explicit non-actionable refusal / nonzero | silent exit 0 success |
| Blank required identity | reject row / fail batch | silent skip → partial success |
| Malformed / nonfinite numeric | fail with code | crash or silent drop |
| Inconsistent counts / partial-row drop | refuse; preserve prior valid OUT | partial write |
| Fully valid output | atomic replace | in-place mutate of pinned artifact |
| Honest empty | versioned **NFL** status contract (not `FAIR_LINES_HONESTY_SPORTS`) | copy common-sports enum |
| 503 with empty reasons | unavailable (Alex X2: reason fields non-actionable, never exit-0) | treat as empty-success |
| Unknown age / history_lagging | UNKNOWN / refused | invent FRESH/AGING/STALE thresholds |

## Increment after Cos ACCEPT (no M0 types)

Export policy implemented on `export_kei_lines_nfl.py` + tests. Does **not** wire M0 / #664 types.

- Transport refusals RETAIN (#697 `0aad8d75` behavior: URLError/Timeout/JSONDecode → exit 1, no OUT write)
- Empty lines / missing payload / honesty-enum empty → `unexpected_empty_payload` (NFL∉HONESTY)
- Blank `game_id` / home / away → `blank_required_identity` (no silent skip)
- Nonfinite / non-numeric spread or total → `malformed_numeric`
- `count` ≠ `len(lines)` → `inconsistent_counts`
- Error-bearing / 503-shaped body → `upstream_unavailable` (never exit-0)
- Refuse: stderr JSON `{ok:false, actionable:false, statusContract:nfl-export-status-v1}`; prior OUT preserved
- Fully valid: atomic `os.replace`; leftover tmp cleaned
- TS stubs: NFL∉HONESTY source-lock; authorized closed GET = 503 unavailable, `fetchNflFairLines` not called; UI `!res.ok` ≠ ready empty

## W-FIX-B (Cos ORDER after M0 `d76c550d` / seal `4de08ebf`)

Attached `#664` validate @ `7abf65a2` (blob `a8cd6054…` match) + A's shared contract
(`nfl_fixture_assembly/contract.py` + `apps/web/lib/nfl-fixture-assembly-contract.ts`).

Wired the SAME contract into actual consumers:

| Consumer | Function |
|---|---|
| API | `projectFixtureFairLinesApiResponse` + `nflFairLinesCustomerUnavailableResponse` in `lib/nfl-fair-lines-fixture-api.ts`; customer GET still 503 helper + `persistOdds: false` |
| Board | `projectFixtureFairLinesBoard` in `nfl-fair-lines.ts` |
| UI | `assertCustomerFairLinesViewModel` + `projectFixtureFairLinesViewModel`; client refuses ALLOW_FIXTURE as subscriber |
| View-model | `keiGamesFromFixtureFairLines` in `resolve-kei-lines.ts` |
| Export | `project_fixture_assembly_to_export` / `consume_fixture_eligibility`; customer `assemble_games` refuses fixture payloads |
| Cache | `pageDataCacheHeadersForFixture` + generation cache; invalidate ⇒ `REFUSE_CACHE` |

ALLOW_FIXTURE is fixture-channel-only. Totals/ML/prob channels absent on point-margin.

## Holds (this worker)

- No merge / deploy / CERT
- No OPEN_ACCESS / access flip / paid probe
- No R5 reopen · no Odds/E1/Stage C · no credentials
- No disconnected demonstration helper as the W-FIX-B deliverable
- No W-FIX-B wiring until M0 contract tip from A / Cos
- Then implement immediately without another Ryan ack
