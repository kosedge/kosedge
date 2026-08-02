# Edge Board population status — 2026-08-02

Goal: every `/edge-board/[sport]` populated and working; KEI labeling honest; no fake model/handicap splits outside MLB.

## Sports audited (`SPORTS` in `apps/web/lib/sports.ts`)

| Sport | Route | Market source | KEI source | Model vs KEI | Board status |
|-------|-------|---------------|------------|--------------|--------------|
| **MLB** | `/edge-board/mlb` | Odds `h2h,totals` + fallback | `/mlb/fair-lines` handicap | **Real split** | Working (ML + O/U) |
| **NFL** | `/edge-board/nfl` | Fair-lines seed + Odds overlay | NFL fair-lines → handicap | Identity (published = KEI) | Working (week / odds slate) |
| **NBA** | `/edge-board/nba` | Odds + empty fallback | `/nba/fair-lines` | Identity | **Fixed hang** on fair-lines; **offseason empty** is honest until projections exist |
| **WNBA** | `/edge-board/wnba` | Odds + fallback (10) | `/wnba/fair-lines` | Identity | Working when fair-lines/odds present |
| **NHL** | `/edge-board/nhl` | Odds + fallback (62) | *none* (no fair-lines / kei_lines) | n/a | Markets from fallback; **KEI not available** until NHL model ships |
| **NCAAM** | `/edge-board/ncaam` | Odds + **new** KEI skeleton fallback (76) | `kei_lines_ncaam.json` (38) | Identity (file proj*) | Working — KEI from file; books when Odds live |
| **CFB** | `/edge-board/cfb` | Odds + fallback (252) | *none* | n/a | Markets from fallback; **KEI not available** until CFB model ships |

## What changed this pass

1. **NBA `/nba/fair-lines` hang** — lock/statement timeout, drop orphan `game_date IS NULL` scan, remove N+1 projection lookups, `LIMIT 80` (`services/model-service/src/routes/nba.py`). Requires Railway deploy.
2. **NCAAM fallback** — skeleton rows from `kei_lines_ncaam.json` (no invented book prices).
3. **Honesty comments** — NFL/NBA/WNBA mappers + `resolve-kei-lines.ts`: model_* identity until pre_blend.
4. **UX** — Edge Board empty state no longer “Coming soon” / ODDS-only; copy says KEI vs Market; MLB ML edge wording = handicap.

## Still cannot fully populate KEI

| Sport | Why |
|-------|-----|
| **NHL** | No `kei_lines_nhl.json`, no `/nhl/fair-lines` in assemble path |
| **CFB** | No `kei_lines_cfb.json`, no CFB fair-lines resolver |
| **NBA (Aug)** | Offseason — fair-lines may return `count=0` honestly after hang fix |

## Shared component contract

- Edgeboard columns always show **KEI handicap** (`row.kei` via `resolveHandicapFields`).
- MLB may attach `modelKei*` for Fair Lines; tags/edge use handicap only.
- Sports with only published KEI: `applyHandicapIdentity` → model = handicap.
