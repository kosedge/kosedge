# Edge Board population + honesty — final (2026-08-02)

PR #66 merged + Railway. This pass closes NHL/CFB honesty and removes remaining “Coming soon” on Edge Board UI.

## Final per-sport status

| Sport | Markets | KEI | Notes |
|-------|---------|-----|-------|
| **MLB** | Yes | Yes | Real Model vs KEI; board shows KEI handicap; ML + O/U |
| **NFL** | Yes | Yes | Fair-lines + Odds; KEI = published (model identity) |
| **NBA** | When live | When projected | Fair-lines unhung; Aug offseason → clean empty / `offseason_empty` |
| **WNBA** | Yes | Yes | Fair-lines + fallback; KEI identity |
| **NCAAM** | When Odds live | Yes | `kei_lines_ncaam.json` + skeleton fallback (no invented books) |
| **NHL** | Yes | **No** | Markets-only UI banner; KEI/Edge/Tag blank until model |
| **CFB** | Yes | **No** | Markets-only UI banner; KEI/Edge/Tag blank until model |

## Honesty rules locked

- Edge Board never invents KEI or book prices.
- No “Coming soon” on Edge Board product UI (empty cells use “—”).
- NHL/CFB: `resolveKeiGames` → `[]`; `sportIsMarketsOnlyEdgeBoard` drives copy + banner.
- MLB alone has real `model_*` vs `handicap_*`; other KEI sports use identity until pre_blend.

## Key files

- `apps/web/lib/edge-board-kei-availability.ts`
- `apps/web/components/EdgeBoard.tsx`
- `apps/web/app/edge-board/[sport]/page.tsx`
- `apps/web/lib/resolve-kei-lines.ts`
- `apps/web/lib/build-edge-board-rows.ts`
