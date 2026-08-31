# CFB Edge Board — show the book (join + display)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after home-sign (#342)  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah / KEI / −42.2 / band 12 / tag thresholds:** do not change.

This is a **desk display + event-join** pass. Not a ratings pass.

---

## Why this exists (production, 2026-08-31)

| Game            | DraftKings     | KosEdge Edge Board                                       |
| --------------- | -------------- | -------------------------------------------------------- |
| UMass @ Rutgers | RU **−29.5**   | KEI RU **−27.4** · Open **—** · Current **`no book`**    |
| Akron @ Wake    | Wake **−24.5** | Open **−24.5** · Current **`untrusted`** · KEI **−11.9** |

**Bug A — join miss.** Odds event present; name keys do not intersect.  
**Bug B — trust deletes the line.** `applyCfbTrustedMarketToRows` sets `best: ""` when untrusted.

---

## Laws

1. One engine. One `as_of=2026-08-31`. No KEI rebuild.
2. Never invent Open / Current / Best.
3. If the feed has a point, paint it. Trust may not blank Open or Current.
4. Edge / Tag still require trusted Best + existing cuts (LEAN ≥ 2.5 · PLAY ≥ 4.0 · band 12 · single-book 8).
5. No team-id branches. Aliases are a name map.
6. No second CFB stack.
7. NFL/CBB/MLB untouched unless shared odds alias table is the right place.
8. Utah blocker stays.
9. Do not stretch WP / playoff / −42.2.
10. Preview prose is not this pass.

---

## Phase 0 — Discovery (READ ONLY)

Write `docs/CFB_EDGEBOARD_MARKET_VISIBLE_AUDIT.md` before any edit.

Stop if you cannot name (1) the matcher that failed Rutgers and (2) the assignment that sets `best` to null.

---

## Phase 1 — Implementation

1. Paint the book even when untrusted — do not clear `row.open` / display Best; Edge/Tag from `trustedBest` only.
2. Name aliases so Rutgers joins (`UMass` → Massachusetts family) — data-driven; Miami OH ≠ Miami FL must-test.
3. FCS / no-KEI rows: show Open/Current when feed has a line; KEI `—`; no Edge/Tag.
4. Dump + tests + scorecard.

### Forbidden

`apply_cfb_kei` · power · WP · shock · Utah · band/threshold changes · inventing DK into KEI JSON · scraping · auto-PLAY on Wake.
