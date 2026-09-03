# NFL KEI Lines stub → live fair-lines (2026-09-03)

## Problem

`/pro/kei-lines/nfl` on the live Pro path rendered a **pipeline stub**:

> No KEI lines for NFL yet. Run the pipeline export to generate data/processed/kei_lines_*.json.

Paying subscribers must not land there. The live KEI board is `/pro/nfl/fair-lines`.

## Fix (this PR)

- Redirect `/pro/kei-lines/nfl` → `/pro/nfl/fair-lines` (page `redirect()` + `next.config` redirect).
- Compare Odds “KEI Lines” uses `getKeiLinesBoardHref(sport)` (NFL → fair-lines).
- KEI Lines hub card for NFL points at fair-lines.
- Insights desk-note NFL KEI link updated.
- Tests lock nav + route away from the stub invent string.

## Explicit non-goals

- Do **not** run the pipeline / mint `kei_lines_nfl.json`.
- Do **not** hide `/pro/nfl/fair-lines`.
- Paywall stays off. No remat.

## Verify

```bash
# After deploy: stub path redirects; board stays live
curl -sSI https://www.kosedge.com/pro/kei-lines/nfl | head -n 20
# Expect Location: /pro/nfl/fair-lines (or 307/308)

curl -sS https://www.kosedge.com/odds/nfl | rg -o 'href="[^"]*fair-lines[^"]*"'
# Expect /pro/nfl/fair-lines on the KEI Lines control
```

## CoS

Draft PR only — **Do not merge — CoS merges.**
