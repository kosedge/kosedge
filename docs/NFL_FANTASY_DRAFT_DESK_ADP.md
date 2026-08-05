# Fantasy Draft Desk — Real ADP Integration

Replaces the Phase 1 KosEdge ADP **proxy** with FantasyPros consensus market ADP
so **Model vs ADP** is a real draft-market edge signal.

## Source

| Item | Detail |
| --- | --- |
| Provider | FantasyPros partners consensus rankings API |
| Endpoint | `https://partners.fantasypros.com/api/v1/consensus-rankings.php` |
| Sport / type | `NFL`, `type=ADP`, `week=0` (season-long) |
| Format map | Standard → `STD`, Half-PPR → `HALF`, PPR → `PPR` |
| ADP field | `rank_ave` (average draft position) |
| Freshness | `last_updated` / `last_updated_ts` from the feed |
| Attribution | ADP data from FantasyPros |

Live fetch revalidates about hourly (`next.revalidate = 3600`). If the live
call fails, the desk falls back to checked-in snapshots under
`apps/web/data/fantasy/adp-fantasypros-2026-{standard,half_ppr,ppr}.json`.

Refresh snapshots:

```bash
node scripts/nfl/refresh-fantasypros-adp.mjs 2026
```

## Matching method (deterministic)

Priority order — **no fuzzy edit-distance**:

1. SportsData id (when present on both sides)
2. Full / core name + team + pos (Jr/Sr/II/III stripped; St. Brown compounds)
3. Short name / compact short (`J.Taylor` ↔ `J. Taylor`) + team + pos
4. First initial + last + team + pos
5. Unique last + team + pos
6. Team-agnostic unique variants of 2–4 (roster moves / stale team codes)
7. Same rules against **sibling scoring panels** → `confidence: cross_format`

| Confidence | ADP column | Value Δ / value board |
| --- | --- | --- |
| `high` (same format) | shown | shown |
| `cross_format` (sibling panel) | shown | blank (`—`) |
| unmatched | `—` | `—` |

Unmatched rows are logged server-side (`[fantasy-adp] unmatched …`) and sampled
in the desk Methods panel.

## Coverage (top-200 preseason skill board, Half-PPR)

Measured against packaged preseason totals + checked-in FantasyPros snapshots
(HALF primary, STD/PPR siblings):

| Stage | Linked ADP | High-confidence (Value Δ) | Notes |
| --- | ---: | ---: | --- |
| Before polish (HALF only, team-bound) | **184 / 200** | 184 | 16 unmatched |
| After polish (rules + cross-format) | **191 / 200** | **184** | +7 ADP display; Value Δ stays same-format clean |

### Newly matched (examples)

Previously unmatched on HALF-only matching; now linked via PPR sibling panel
(`cross_format` — ADP shown, Value Δ blank):

| Board name | Team | Pos | Market name | ADP source |
| --- | --- | --- | --- | --- |
| Q.Ewers | MIA | QB | Quinn Ewers | PPR panel |
| B.Cook | NYJ | QB | Brady Cook | PPR panel |
| X.Legette | CAR | WR | Xavier Legette | PPR panel |
| Odell Beckham Jr. | NYG | WR | Odell Beckham Jr. | PPR panel |
| Pierre Strong | GB | RB | Pierre Strong Jr. | PPR / core-name |
| Israel Abanikanda | DAL | RB | Israel Abanikanda | PPR panel |
| Max Bredeson | MIN | RB | Max Bredeson | PPR panel |

### Remaining unmatched (known gaps)

Not in any FantasyPros STD/HALF/PPR ADP snapshot (or ambiguous):

- A.O'Connell (LV QB)
- Laquon Treadwell (IND WR)
- Phillip Dorsett (LV WR)
- Jalen Reagor (MIA WR)
- M.Carter (TEN RB)
- Z.Knight (ARI RB)
- O.Zaccheaus (ATL WR)
- Michael Burton (CLE RB)
- A.Thielen (MIN WR) — absent from current FP ADP panels

These stay `—` until the market feed lists them. We do not invent ADP.

## Transparency on the desk

Hero line shows:

- ADP source label (FantasyPros consensus ADP)
- Freshness (`updated M/D` · live cache | snapshot)
- Match coverage (`matched N/total (H high for Value Δ · C cross-format)`)

Methods panel lists feed limitations, matching rules, and an unmatched sample.

## Limitations (honest)

- FantasyPros aggregates multiple platforms/experts — not a single draft room.
- HALF/STD panels are shorter than PPR (~339 vs ~593); deep board ADP may be
  cross-format only.
- Name matching can still miss obscure / non-drafted depth; unmatched → —.
- Official FantasyPros commercial API (v2 + API key) is not wired.
- K/DST appear when present in the ADP feed; preseason fallback boards omit them.

## Before / after value signal

**Proxy era:** ADP hugged model rank → value was model-vs-model.

**Market ADP + polish:** same-format Value Δ only; cross-format fills ADP gaps
without polluting the value board.

## Key files

- `apps/web/lib/fantasy/adp-fantasypros.ts` — fetch, snapshot, scoring bundle
- `apps/web/lib/fantasy/adp-match.ts` — deterministic matcher + confidence
- `apps/web/lib/fantasy/enrich.ts` — attach ADP / value Δ
- `apps/web/lib/fantasy/load-desk.ts` — desk loader + unmatched logging
- `apps/web/data/fantasy/adp-fantasypros-2026-*.json` — offline snapshots
- `scripts/nfl/refresh-fantasypros-adp.mjs` — snapshot refresh

## Out of scope

- Switching ADP providers
- Phase 2 mock draft room
- Major UI redesign / new columns
