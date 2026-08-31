# CFB Edge Board market-visible audit

**Phase:** 0 (READ ONLY)  
**Branch:** `cursor/cfb-edgeboard-market-visible-3ca1`  
**Base:** `deploy-vercel` @ `#342` (`45a767ff`)  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Live Odds probe:** 103 `americanfootball_ncaaf` events (key present). No invented DK numbers.

Home-sign (#342) is landed. This pass is **join + display only**. Do not retune KEI / band 12 / Utah.

---

## How an Odds event becomes an Edge Board row (file:line)

```
pullOddsRows / fetchEdgeBoard (odds-api.ts)
  → row.game = `${away_team} @ ${home_team}`
  → row.open / row.best = awayOutcome.point   (odds-api.ts:354–392)
assembleEdgeBoardRows (build-edge-board-rows.ts:202–216)
  → ensureAllKeiGamesOnBoard (edge-board-kei.ts:194)   // seed missing KEI skeletons
  → mergeKeiIntoEdgeBoardRows (edge-board-kei.ts:250) // match via cfbGameMatchKeys
  → applyCfbTrustedMarketToRows (cfb-trusted-market.ts:103)  // CFB only
page (edge-board/[sport]/page.tsx:88–91)
  → stampCfbEdgeBoardWeek → filter week === 1
```

Match keys for CFB: `cfbGameMatchKeys` in `apps/web/lib/cfb-match-keys.ts` (also used by `stampCfbEdgeBoardWeek`, dump script mirror).

---

## Name matching today (exact string? slug? alias table?)

**Fold + thin alias table + 1-/2-word prefixes.** Not fuzzy.

```7:17:apps/web/lib/cfb-match-keys.ts
const ALIASES: Record<string, string> = {
  hawaii: "hawaii",
  "hawai'i": "hawaii",
  // ... san jose / sjsu only
};
```

```35:48:apps/web/lib/cfb-match-keys.ts
export function cfbGameMatchKeys(game: string): string[] {
  // full side @ full side
  // first 2 words @ first 2 words
  // first 1 word  @ first 1 word
}
```

`aliasToken` only remaps when the **entire** folded side string is an `ALIASES` key (e.g. `"hawaii"`). There is **no** `umass` / `massachusetts` entry.

Futures has a richer map (`cfb-futures-name-match.ts`) — **not** used by Edge Board join.

---

## Why MASS@RUT is `no book` (prove it)

### 1. Odds event **is present** (live 2026-08-31)

| Field     | Value                                           |
| --------- | ----------------------------------------------- |
| Event     | **`UMass Minutemen @ Rutgers Scarlet Knights`** |
| DK spread | Rutgers **−29.5** / UMass **+29.5**             |
| id        | `e564afb0a5ab84ab43befa56bdb90522`              |

### 2. Slate / KEI name

| Field    | Value                                               |
| -------- | --------------------------------------------------- |
| Pack     | `Massachusetts Minutemen @ Rutgers Scarlet Knights` |
| Abbr     | `MASS @ RUT`                                        |
| KEI home | **−27.42**                                          |

### 3. Matcher that failed (keys have **zero** intersection)

| Source | `cfbGameMatchKeys` (1-word) |
| ------ | --------------------------- |
| Odds   | `umass @ rutgers`           |
| Slate  | `massachusetts @ rutgers`   |
| Abbr   | `mass @ rut`                |

**Intersect = ∅.** Proven with the same fold/alias rules as `cfb-match-keys.ts`.

Consequence in assemble:

1. Odds row stays as `UMass Minutemen @ Rutgers…` (has Open/Best).
2. KEI skeleton seeded as `Massachusetts Minutemen @ Rutgers…` (has KEI, **no** books) because `ensureAllKeiGamesOnBoard` does not see the Odds keys as covering it (`edge-board-kei.ts:215–216`).
3. `mergeKei` never attaches KEI onto the Odds row (keys miss).
4. Week-1 desk shows the KEI skeleton → trust `no_market` → UI **`no book`**.

Dump already recorded this: `MASS@RUT` `trusted_reason=no_market`, `open_spread_home=null` (`data/ops/cfb-week1-book-dump-homesign-20260831.json`).

**Not** a missing Odds credit. **Not** a KEI problem. **Join alias hole:** feed `UMass` vs slate `Massachusetts`.

---

## Where trust nulls Best/Current (file:line)

```128:137:apps/web/lib/cfb-trusted-market.ts
    if (verdict.trusted) return row;
    return {
      ...row,
      best: "",   // ← Bug B: blanks display Current/Best
      book: verdict.reason === "no_market" ? "no book" : "untrusted",
      bookKey: "",
    };
```

`row.open` is **not** cleared here. EdgeBoard paints Current from `lineRow.best` only (`EdgeBoard.tsx:820–828`); when `best === ""`, Current becomes `—` and PriceCell shows the `untrusted` / `no book` footnote **instead of** a number (`EdgeBoard.tsx:537–541`).

AKR@WAKE proof (homesign dump + live Odds):

|               | Value                                                        |
| ------------- | ------------------------------------------------------------ |
| Odds          | `Akron Zips @ Wake Forest Demon Deacons` · DK Wake **−24.5** |
| KEI           | **−11.93**                                                   |
| Open home     | **−24.5** (joined — names match)                             |
| same-side gap | **12.57 ≥ 12** → `absurd_vs_kei` (correct trust)             |
| After apply   | `best: ""` → Current LINE gone; Open still −24.5             |

Operator sees Open −24.5 + Current `untrusted`. Untrusted must be a **tag gate**, not a market-column delete.

---

## Whether Open is stored separately from Best

**Yes.** Odds client writes both (`odds-api.ts:391–392`). Trust clears only `best`. Open survives on the row and in the Open column.

Phase 1 needs a **display Best / Current** that keeps the feed point, plus a separate trusted candidate for Edge/Tag (do not reuse cleared `best` as the only Current source).

---

## FCS rows: do we drop the game if kei is null?

**Two layers:**

1. **`getKeiLines("cfb")` drops null-KEI games** (`kei-lines.ts:125`):  
   `.filter((g) => g.kei?.kei_spread_home != null)`  
   → FCS never seeded from KEI pack.

2. **Odds FCS events still enter** via `fetchEdgeBoard`. `stampCfbEdgeBoardWeek` indexes the **full** KEI pack (including null-KEI FCS labels) so week can stamp when names match.

Live Odds has e.g. `West Georgia Wolves @ Kennesaw State Owls` (DK −23.5) and `Merrimack Warriors @ Delaware Blue Hens`. If names match the pack, they can appear as book-only rows; if alias holes exist, they vanish from the Week 1 filter (`week == null` → dropped at `page.tsx:91`).

Phase 1: keep Odds rows with books even when KEI is blank; do not require `kei_spread_home` to show Open/Current.

---

## Shared alias table with other sports?

| Table                                 | Used by Edge Board join?                                        |
| ------------------------------------- | --------------------------------------------------------------- |
| `cfb-match-keys.ts` `ALIASES`         | **Yes** (board + stamp + dump)                                  |
| `cfb-futures-name-match.ts` `ALIASES` | No (futures only; already has some Miami FL / UConn / Ole Miss) |
| NFL alias maps                        | No                                                              |

Phase 1 aliases belong in **`cfb-match-keys.ts`** (and dump mirror). Do not touch NFL/CBB product trees. Optionally keep futures map in sync later — not required to fix Rutgers.

---

## Phase 1 allowlist

1. **`apps/web/lib/cfb-trusted-market.ts`** — stop setting `best: ""` for display; keep feed Best; expose trust reason / trusted flag for Edge only.
2. **`apps/web/components/EdgeBoard.tsx`** — Current paints feed number + `untrusted` footnote alongside (not instead of).
3. **`apps/web/lib/cfb-match-keys.ts`** — expand `ALIASES` (UMass→Massachusetts family; Miami OH ≠ Miami FL tested; brief list + Phase 0 misses).
4. **`scripts/cfb/cfb_dump_edgeboard.py`** — same aliases; columns `open_h`, `current_h`, `trusted`, `reason`, `painted_without_trust`; artifact `data/ops/cfb-week1-market-visible-YYYYMMDD.json`.
5. Tests + `docs/CFB_EDGEBOARD_MARKET_VISIBLE_SCORECARD.md`.

### Out of allowlist

`apply_cfb_kei` · power · WP · shock · Utah · band 12 · PLAY/LEAN cuts · inventing books · odds-api home rewrite · auto-PLAY on Wake.

---

## Phase 0 gate

| Required                        | Named                                                                                              |
| ------------------------------- | -------------------------------------------------------------------------------------------------- |
| (1) Matcher that failed Rutgers | `cfbGameMatchKeys` / `aliasToken` in `cfb-match-keys.ts` — `umass` vs `massachusetts`, intersect ∅ |
| (2) Assignment that nulls Best  | `applyCfbTrustedMarketToRows` **`best: ""`** at `cfb-trusted-market.ts:134`                        |
| Odds event present?             | **Yes** — `UMass Minutemen @ Rutgers Scarlet Knights`                                              |
| Wake Open vs trust              | Open joined −24.5; Best wiped by absurd (ss 12.57 ≥ 12) — correct trust, wrong display             |

Ready for Phase 1: paint feed + alias map. No KEI / band edits.
