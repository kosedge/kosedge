# The Book — abandon old tracker (2026-08-29)

## Abandoned

- Workstream **Enterprise pick/unit tracker** (`bc-6441239a-7c15-5d9f-8aad-5566182578cb`) — IDLE, **no branch / no PR**.
- Do **not** merge any tracker UI. Do **not** continue plays/leans scoreboard chrome.

## Active

- Workstream **The Book** — multi-sport ledger, CFB first.
- Branch: `cursor/the-book-ledger-b053`
- Schema: `infra/db/053_book_ledger.sql`
- Store: `services/model-service/src/services/book_ledger/`
- Ops: `/ops/book/*` (auth = DepthSot `x-kosedge-secret`)
- Snapshot: `scripts/cfb/book_snapshot.py`

## Desk OS

Out of scope. No remat / depth pack / injury rewrite in this PR.
