# t5178u M0 — citation manifest (SMALL)

- worker: Cursor A
- branch: `cursor/t5178u-wfix-a-fixture-assembly-c003`
- base: `deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f`
- wall: 2026-11-02
- CERT=0 · DRAFT only · no merge/deploy

## Path-read + isolated-write preflight

| Check | Result |
|---|---|
| Product tree readable | YES — `apps/web` + `services/model-service` present |
| Write isolated to new branch | YES — branch created off `f5e3bb58`; no writes on `deploy-vercel` |
| PR posture | DRAFT (not production) |
| `#664` validate on base tip | **ABSENT** — `services/model-service/src/services/nfl_hhl1_capture/` empty on `f5e3bb58` |
| `#664` validate on DRAFT tip | PRESENT at `7abf65a2` (`validate_l1_candidate` / `validate_l1_batch` / `reject_market_fields`) |

Research-branch absence ≠ missing product code. `deploy-vercel` has `nfl_simulator.py`; this package does **not** import it.

## Classification (Git commit / artifact digest / CoS receipt)

| Pin | Class | Status | Evidence |
|---|---|---|---|
| `#664` tip `7abf65a2` | **Git commit** | VALID (OPEN DRAFT) | `7abf65a2c85708cc6d4a1cd2b4d9643a4612084a` — H-HL-1 plumbing |
| `#688` sign-out | **Git PR** | OPEN DRAFT | head `6f29b4a25368756be6b7b459198955d160c5d457` — layout-only; not imported here |
| `#695` API refusal | **Git PR** | OPEN DRAFT | head `bff7c7340c271df70ac810dfed09266e567924a3` — consumer-refuse pattern |
| `#697` tip `0aad8d75` | **Git commit** | VALID (OPEN DRAFT) | `0aad8d751ebec621c8f2fd06ad09e6e5357dddd9` — export refuse |
| `#700` quality | **Git PR** | OPEN DRAFT | head `9d436eb1cebc29fc1f91bdb3306dbe3dd393805d` — reference |
| `#701` tip `455a8e43` | **Git commit** | REFERENCE ONLY | `455a8e43eccc1ed2c39e91821790cce968ffdadb` — **do not reopen R5** |
| `#703` history | **Git PR** | OPEN DRAFT | head `8a7895b9982c155e04298a34fe66e4e59da19fad` — identity/history |
| `4eef5d1f` | ONE_RUN **bind** | **CONSUMED** | `git cat-file` miss — not a git object |
| `9a72c55b` | ONE_RUN **receipt** | **PRESERVE** | `git cat-file` miss — not a git object |
| `4fa6d856` | pre-machine CoS **token** | CONSUMED once; **never reset** | `git cat-file` miss — not a git object |
| `c7775dae` | CoS/PE **receipt** | VALID as receipt, **not git** | `git cat-file` miss |
| `d359ce54` | filed-packet **SHA256 digest** | VALID as packet digest, **not a git tip** | `#664` `PASS_PROTOCOL_SHA256` starts `d359ce54…` |
| `10ca67fe` `89dcd61d` `4223362c` `23b34ef3` `1ee90fac` | artifact/receipt until custodian | not git-critical-path | Cos amend 9b2e5e19 |

`c7775dae` and peer PE stamps are **RECEIPTS**, not git. `d359ce54` is a **packet digest**.

## Exact file seams (this lineage)

| Seam | Path | Bind note |
|---|---|---|
| HL validate | `services/model-service/src/services/nfl_hhl1_capture/validate.py` | reuse `#664` tip `7abf65a2` (checked out onto this DRAFT only) |
| HL schema | `…/nfl_hhl1_capture/schema.py` | same |
| NFL closed surface | `apps/web/app/api/nfl/fair-lines/route.ts` | 503 + `persistOdds:false` — W-FIX-B consumer |
| Board flags | `apps/web/lib/cfb-edge-board-public.ts` | `NFL_EDGE_BOARD_PUBLIC_ENABLED=false`; INTERNAL override exists — **ALLOW_FIXTURE must not honor it** |
| Honesty helper | `apps/web/lib/fair-lines-api-board.ts` | `FAIR_LINES_HONESTY_SPORTS` = cfb/mlb/nba/nhl/wnba/ncaaf — **NFL excluded; do not copy** |
| Page-data cache | `apps/web/lib/page-data-cache.ts` | private,no-store for Pro; fixture cacheable=true → refuse |
| Fair-lines VM | `apps/web/lib/nfl-fair-lines.ts` | W-FIX-B projection target |
| Export | `apps/web/scripts/export_kei_lines_nfl.py` | `#697` tip; W-FIX-B |
| Props eligibility pattern | `apps/web/lib/nfl-props-eligibility.ts` + `nfl_props_eligibility.py` | shape reference — **do not widen to betting** |

## Prerequisite mismatches (real)

1. **`nfl_hhl1_capture` missing on `f5e3bb58`.** Product lineage does not yet contain `validate_l1_candidate`. Bound by checking out **only** the `#664` capture package + its synthetic plumbing tests (not celery/odds/auth from that PR).
2. **`isNflFairLinesCustomerSurfaceClosed()` can open under `NFL_EDGE_BOARD_INTERNAL=1`.** Fixture `ALLOW_FIXTURE` is a different channel and must not use that env bypass.
3. **Export on this tip still silent-skips blank teams and can exit 0.** W-FIX-B scope; not repaired here.
4. **`#701` / R5 is reference only.** No scoring, no reopen.

Independent W-FIX-A continues on the bound contract + `#664` validate attachment.

## How B wires validate on `deploy-vercel` @ `f5e3bb58`

See `data/ops/t5178u-m0-attach-path-for-b.md`.

- `7abf65a2` = **Git commit** `7abf65a2c85708cc6d4a1cd2b4d9643a4612084a` (OPEN DRAFT `#664`).
- Attach is a **path-checkout of that Git commit** onto the product-lineage branch — same six `nfl_hhl1_capture/*` blobs + synthetic plumbing test. Verified byte-identical on this branch.
- B repeats the same `git checkout 7abf65a2 -- services/model-service/src/services/nfl_hhl1_capture …` on `cursor/t5178u-wfixb-consumer-a875`, **or** path-checkouts those files from this M0 tip.
- Import `src.services.nfl_hhl1_capture.validate` (`validate_l1_candidate` / `validate_l1_batch` / `reject_market_fields`). Do **not** write a disconnected demo helper. Do **not** pull a sparse research tree. Do **not** merge the rest of `#664`.
