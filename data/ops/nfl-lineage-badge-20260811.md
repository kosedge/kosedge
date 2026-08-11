# NFL Lineage Badge UI — 2026-08-11

**Status: DONE**
**Branch:** `feat/nfl-lineage-badge-ui` → `deploy-vercel`
**Closes WAIVE:** C6 from `data/ops/nfl-preseason-complete-20260811.md` (`active_run_id` / lineage visible where projections show)

---

## Surfaces covered

| Surface | Path | Lineage source |
|---------|------|----------------|
| Edge Board (NFL) | `/edge-board/nfl` | Web launch pointer (`active_run_id`, engine, generated) |
| Season Model | `/pro/nfl/model` | Pointer run_id + live `engine_version` overlay when status/True PR available |
| Power Ratings | `/pro/power-ratings/nfl` | Bundle `lineage` (fallback pointer) |
| Game Boxes | `/pro/nfl/game-boxes` | Pointer run_id + live engine overlay |
| Survivor (planner hub) | `/pro/nfl/survivor` | Pointer run_id + live engine overlay |
| Team previews (editorial) | `/pro/nfl/previews/[team]` | **Editorial** + published date — not active_run |

Badge content (compact chip): truncated `run_id` (full on hover), short `engine_version`, optional as-of date.

---

## WAIVE closed

Preseason-complete lock C6 is closed: users can answer “which engine/run is this?” from primary projection UIs.

---

## Deferred / not in this PR

| Surface | Reason |
|---------|--------|
| Fantasy desks (mock / builder / rankings) | Not a season-engine projection card surface for this gate |
| Props / DFS / Awards | Intentionally non-primary; activate at kickoff |
| KEI Lines / Edges list pages | No dedicated lineage field wired here; Edge Board covers KEI-vs-market board |
| CFB | Out of scope |

---

## Smoke notes (local / preview)

1. **Edge Board** — `/edge-board/nfl`: quiet chip under title with Model run id + engine.
2. **Season Model** — `/pro/nfl/model`: badge above True PR board; live engine may read v1.27 while pointer metadata still cites v1.24 (known thin spot; badge overlays live engine when status returns).
3. **Game Boxes or Survivor** — badge in the link row under the hub header.
4. **Team preview** — Editorial chip + date; does not claim active_run.

```bash
# Unit
cd apps/web && npx vitest run __tests__/lib/nfl-truth-layer.test.ts
```

---

*Closed by: agent · 2026-08-11*
*Depends on: #185 preseason-complete lock, #171 truth-layer lineage fields*
