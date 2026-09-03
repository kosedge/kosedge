# NFL honesty stamps — Awards vs Futures + Depth vs Camp — 2026-09-03

**Status:** Copy/stamp only. Tiles stay visible. Paywall off. No KEI mint. No remat. No new products. Draft PR — CoS merges.

## Bugs (paying-subscriber honesty)

1. **Awards vs Futures** — `/pro/nfl/awards` (model award-score snapshot) and `/pro/nfl/projections` (Futures) can disagree on the same player / different vintages.
2. **Depth Charts vs Camp** — `/pro/nfl/depth-charts` (and team hub depth) can name a different QB1 than Camp Desk notes (IR / claims).

## Fix

| Surface | Subscriber-facing stamp |
|---------|-------------------------|
| Awards | Model award-score snapshot from last materialize. Separate from Futures (different ranking / vintage). Player award odds not joined. |
| Futures | Season sim / player-production spine. Separate from Awards. Leader odds not joined. |
| Depth Charts | Packaged model depth chart — not live Camp Desk. Named QB1, IR, and claims live on Camp Desk. |

Shared constants: `apps/web/lib/nfl-surface-honesty.ts` (page strings = subscriber English; engineering doctrine stays in file comments / ops note only).

## Live audit quotes (2026-09-03) — why the stamps matter

Do **not** put these as engineering notes on the page. They are the proof cases the stamps must keep honest.

### Depth vs Camp / fair-lines (ATL crown disagreement)

| Surface | What a subscriber sees |
|---------|------------------------|
| `/pro/nfl/depth-charts` | **ATL QB1 = Tua Tagovailoa**, QB2 = Penix |
| `/pro/nfl/fair-lines` | ATL: `open_competition Tua Tagovailoa, Michael Penix Jr. — no crown` |
| Camp Desk `2026-09-02` | Does **not** crown ATL QB1 |
| Contrast | **LV Cousins** on depth **does** match camp |

Stamp job: make that class of disagreement obvious (packaged model depth ≠ live Camp Desk) without merging names or rewriting camp.

### Awards vs Futures (different vintage)

| Surface | As-of / source the page already shows |
|---------|----------------------------------------|
| `/pro/nfl/awards` | Date **August 11, 2026** · `nfl-player-v1` **as of Jul 19, 2026** |
| `/pro/nfl/projections` | **Generated 8/22/2026** |
| Awards MVP board | e.g. **J.Hurts** ~**3324** pass yds (award-score vintage) |
| Futures yards leaders | e.g. **D.Prescott** ~**4445** (spine / sim vintage) |

Same product family, different boards — keep each page’s own as-of visible. Do **not** reconcile numbers or mint a combined ranking.

## Explicit non-goals

- Do **not** silently reconcile Awards ↔ Futures numbers or mint a combined ranking (engineering rule — not on-page copy)
- Do **not** join player award odds (still not joined — PR #414 Overview copy kept)
- Do **not** rewrite Camp Desk notes
- Do **not** hide Depth Charts / Awards / Futures tiles
- No Overview catalog rewrite beyond keeping #414 honest labels
- No paywall, KEI, remat, ATD, Bijan, Mock, DFS, Guillotine, CLV

## Tests

```bash
pnpm --filter @kosedge/web exec vitest run \
  __tests__/lib/nfl-surface-honesty.test.ts \
  __tests__/components/pro/NflIntelTablePage.test.tsx
```
