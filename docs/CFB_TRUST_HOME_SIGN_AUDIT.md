# CFB trustCfbMarket — home-sign audit

**Phase:** 0 (READ ONLY)  
**Branch:** `cursor/cfb-trust-home-sign-3ca1` (off book-audit tip; #341 still open)  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah / KEI / −42.2 / band 12:** untouched this phase.

Book-audit fact reused (not rediscovered): 35 `absurd_vs_kei` · **27** sign-mismatch · BALL@OSU `raw_gap` 92.7 / `ss_gap` 8.3.

---

## Function path + signature

| Layer | Path | Signature |
|---|---|---|
| **Web SoT** | `apps/web/lib/cfb-trusted-market.ts` | `trustCfbMarket({ kei?, best?, open?, bookCount? }) → { trusted, market, reason }` |
| Apply | same file `applyCfbTrustedMarketToRows` | Spread rows only; clears `best` when untrusted |
| Dump twin | `scripts/cfb/cfb_dump_edgeboard.py` `trust_cfb_market` | Verbatim port; same raw compare |
| Model-service twin | `services/model-service/src/services/book_ledger/cfb_trusted_market.py` | `trust_cfb_market(*, kei, best, open_line, book_count)` |

---

## What KEI sign is (home)

- Bundled pack field: `kei.kei_spread_home` (BALL@OSU = **−42.2**).
- Board merge: `mergeKeiIntoEdgeBoardRows` sets `row.kei = formatSpread(proj.projSpreadHome)` — comment at `edge-board-kei.ts:245`: *“Spread → row.kei = projected home spread”*.
- EdgeBoard display flips KEI for the Away row only (`flipSpread(lineKei)`); bottom / trust input stays **home**.

---

## What Open/Best sign is on the row today

**Away-signed.** Proven in the odds client:

```354:379:apps/web/lib/odds-api.ts
        const awayOutcome = m.outcomes?.find((o) => o.name === ev.away_team);
        const homeOutcome = m.outcomes?.find((o) => o.name === ev.home_team);
        if (!awayOutcome || awayOutcome.point == null) return [];
        const pt = awayOutcome.point;
        // ...
      // Best Line = best away number across all configured books (juice tiebreak).
      const bestSpreadEntry = pickBestSpreadEntry(selectedSpreadData);
```

- `row.open` / `row.best` = **away** point string (e.g. BALL@OSU Open **+50.5**).
- UI Current column shows Away on top / Home on bottom via `flipSpread(lineRow.best)` (`EdgeBoard.tsx` ~818–826) — display is home-aware; **stored row fields are not**.

**Not a blocker:** side is labeled at the Odds API outcome (`ev.away_team`). Home = `−away` is defined, not guessed.

---

## Exact compare (file:line) that produces raw_gap 92.7 on BALL@OSU

```65:71:apps/web/lib/cfb-trusted-market.ts
  const gap = Math.abs(candidate - kei);
  if (gap >= CFB_ABSURD_VS_KEI_PTS) {
    return {
      trusted: false,
      market: null,
      reason: "absurd_vs_kei",
    };
  }
```

Call into that compare with **mismatched signs**:

```96:100:apps/web/lib/cfb-trusted-market.ts
    const verdict = trustCfbMarket({
      kei: row.kei,       // home  −42.2
      best: row.best,     // away  +50.5
      open: row.open,     // away  +50.5
    });
```

BALL@OSU arithmetic:

| quantity | value |
|---|---:|
| `kei` (home) | −42.2 |
| `candidate` (away Open/Best) | +50.5 |
| **`gap` = \|−42.2 − (+50.5)\|** | **92.7** → `absurd_vs_kei` |
| same-side \|−42.2 − (−50.5)\| | **8.3** &lt; 12 → should **keep** |

EdgeBoard re-checks trust with the same mismatch (still passes raw `lineRow.best`):

```961:965:apps/web/components/EdgeBoard.tsx
        trustCfbMarket({
          kei: lineRow?.kei ?? keiSpreadNum,
          best: lineRow?.best ?? bestSpreadNum,
          open: lineRow?.open,
        }).trusted;
```

Note: once trusted, edge uses `keiLine.bottom − bestLine.bottom` (both home). Trust fails first, so edge never runs for the 27 sign-mismatch clears.

Dump script mirrors the bug on purpose (`cfb_dump_edgeboard.py` ~368–375): `kei=kei_home`, `best=best_away`.

---

## Band constant (quote)

```13:16:apps/web/lib/cfb-trusted-market.ts
/** |market − KEI| at/above this → wrong game / junk. No Edge. */
export const CFB_ABSURD_VS_KEI_PTS = 12;
/** Single-book (open missing or same as best) + |market − KEI| ≥ this → untrusted. */
export const CFB_SINGLE_BOOK_ABSURD_PTS = 8;
```

Also: `CFB_OUTLIER_VS_OPEN_PTS = 3.5` · `CFB_LEAN_EDGE_PTS = 2.5` · `CFB_PLAY_EDGE_PTS = 4.0`.  
**Phase 1 must not change these numbers** — only the sign of `candidate` / `open` / `best` at the compare boundary.

---

## Call sites (Edge Board, dump script, any API)

| Site | Role |
|---|---|
| `build-edge-board-rows.ts:216` | `sport === "cfb" ? applyCfbTrustedMarketToRows(merged)` — clears Best before UI |
| `EdgeBoard.tsx:961` | Second trust gate on edge; same away vs home inputs |
| `scripts/cfb/cfb_dump_edgeboard.py` | Measure twin (book-audit) |
| `book_ledger/cfb_snapshot.py:204` | Calls Python twin with `best=raw_spread` from **`spread_home`** |

---

## Shared with NFL/CBB?

**No shared web helper.** `trustCfbMarket` is CFB-only (`cfb-trusted-market.ts`). NFL/CBB/MLB do not import it.

**Python twin caveat:** `cfb_snapshot.py` already feeds **home** market (`spread_home`). Do **not** flip that path again. Phase 1 = web row boundary (+ dump script mirror). Leave model-service alone unless a test proves it also receives away-signed numbers.

---

## Phase 1 allowlist (named files)

1. `apps/web/lib/cfb-trusted-market.ts` — normalize Open/Best → home **inside** `trustCfbMarket` and/or `applyCfbTrustedMarketToRows` (single helper; no team-name branches). Prefer: convert at trust boundary; do **not** rewrite odds-api cache.
2. `apps/web/components/EdgeBoard.tsx` — pass home-normalized book into `trustCfbMarket` (or rely on fixed helper); edge already home vs home once Best survives.
3. `scripts/cfb/cfb_dump_edgeboard.py` — same normalize before trust; re-dump `data/ops/cfb-week1-book-dump-homesign-YYYYMMDD.json`.
4. `apps/web/__tests__/lib/cfb-subscription-lock.test.ts` — BALL@OSU keep Best at ss≈8.3; KEI still −42.2; UCLA sign-artifact PLAY gone.
5. Docs: `docs/CFB_TRUST_HOME_SIGN_SCORECARD.md` (+ this audit already).

### Explicitly out of allowlist

`apply_cfb_kei` · power · WP/shock · Utah · band constants · inventing books · NFL/CBB trust · odds-api storage rewrite · PLAY card.

---

## Phase 0 gate

- Compare pointed at **`cfb-trusted-market.ts:65`** with inputs from **`:96–99`**.
- Away storage proven at **`odds-api.ts:354–379`**.
- Band quoted: **`CFB_ABSURD_VS_KEI_PTS = 12`**.
- Side is labeled → **no blocker file**.

Ready for Phase 1 sign-normalize only.
