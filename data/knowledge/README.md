# Kos Edge knowledge ledger

**SoT for institutional memory / graded lessons.** Chat memory may point here; this tree is authoritative.

**Primary SOP:** `docs/writers/INSTITUTIONAL_MEMORY.md`  
**CoS assignment note:** `docs/writers/COS_INSTITUTIONAL_MEMORY.md`  
**Fact gate (publish-time):** `docs/writers/EDITOR_FACT_GATE.md`

## Status (foundation)

- Schema + SOP + empty product folders landed.
- **No invented grades** for past seasons.
- **Forward-only** logging from the 2026-09-03 night lock.
- Backfill of 2024–2026 is a later wave with real sources only.

## Index

| Path | Product | Contents |
| ---- | ------- | -------- |
| `nfl/draft/` | NFL Draft preview / cycle claims | Empty until real cards |
| `nfl/season-preview/` | NFL season preview / guide | Empty until real cards |
| `nfl/week-preview/` | NFL week / matchup previews | Empty until real cards |
| `nfl/futures/` | NFL futures / season-long markets | Empty until real cards |
| `cfb/week-preview/` | CFB week preview | Empty until real cards |
| `_examples/` | Format demos only (`status: EXAMPLE`) | Not history |

## Core files

| File | Role |
| ---- | ---- |
| `claim-card-TEMPLATE.md` | Blank card to copy |
| `GRADE_RUBRIC.md` | right / wrong / mixed / void |
| `claim-card.schema.json` | Optional JSON shape (keep simple) |

## Required-read (writers + CoS)

Before writing a recurring product: read graded lessons in that product folder. If empty → note **`no prior grades`**. Do not hallucinate history. Soft-pedaling this into optional is a process bug.

## Rules (short)

1. File claim cards on material NEW desk claims.
2. Grade only after outcomes with evidence — grades are sacred.
3. Never invent grades.
4. Do not rewrite `content/writers/**` under this ledger.
5. Ignore `status: EXAMPLE` cards when citing institutional history.
