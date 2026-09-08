# INC-2026-09-08 — NFL Edge Board customer-truth

**Status:** FIX IN PR — CoS merge authority FAILED until Ryan ACCEPT after Riley + Product verify.  
**Surfaces:** `/pro/nfl/edges` (primary defects), `/edge-board/{sport}` (shared contract harden), MLB/other desks.  
**Constraint:** No model / KEI / PLAY-LEAN-PASS threshold changes. Shared contract only.

## Customer symptoms

1. **Display contradiction** — Rows (BAL @ IND, NYJ @ TEN, …) show selected side **Home** with a **green negative** edge (`-1.7 pts`). Customers read negative as bad while Lean says Home.
2. **Arithmetic mismatch** — ARI @ LAC showed Fair `-8.31`, Book `-9.50`, Edge `+1.7`. Visible `|−8.31 − (−9.50)| = 1.19` → should round to `+1.2`, not `+1.7`.

## Read-only trace (before code)

### SoT fields (fair-lines live, 2026-09-08 ~16:11Z)

| Game | fair (home) | consensus market | stake/DK | FD | best | `spread_edge` | decision.market_line | decision.edge_mag |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ARI @ LAC | −8.31 | −9.5 | −10.0 | −9.5 | −10.0 | **+1.69** | −10.0 | 1.69 |
| BAL @ IND | +1.76 | +3.5 | +3.5 | +3.5 | +3.5 | **−1.74** | +3.5 | 1.74 |
| NYJ @ TEN | −2.97 | −1.5 | −1.5 | −1.5 | −1.5 | **−1.47** | −1.5 | 1.47 |

### Desk paint path (`deskEdgesFromFairLine`)

- **Book column** painted `marketSpreadHome` / `marketTotal` (**consensus**).
- **Edge** taken from `spreadEdge` / `totalEdge` (computed vs **stake close**: DK → FD → consensus → best).
- **Side** derived from signed edge (`spreadEdge < 0` → Home).
- **edgeDisplay** kept the **signed** number; UI always applied `text-edge-green`.

→ ARI @ LAC desk: Fair −8.31 · Book **−9.50** · Edge **+1.7** (vs stake −10) · Away.  
→ BAL / NYJ desk: Side **Home** · Edge **−1.7 / −1.5 pts** (green).

### Edge Board assemble (`/api/edge-board/nfl/assemble`)

- Action Fair / Mkt / Edge already use magnitude + `decisionMarketLine`.
- Live assemble ARI row was internally consistent at Fair −8.31 / Mkt −9.5 / Edge 1.19 (PASS), but **CDN/as-of lagged** fair-lines stake (−10 / 1.69 LEAN). Dual paint: Current/best can show a different shop line than Action Mkt.
- Cross-sport assemble at trace time: NFL 32 rows arith OK; other sports often omit `fairLine`/`decisionMarketLine` on flat rows (edge via abs in `flatRowsToLegacy`).

### Root cause (verified)

Not matchup-specific. Shared **customer display contract** broke two ways:

1. **Sign:** selected-side advantage was shown as home-perspective **signed** delta on desks.
2. **Line identity:** painted Book ≠ line used to compute edge (consensus vs stake close).

## Before counts (live slate at trace)

| Surface | Metric | Count |
| --- | --- | ---: |
| NFL Edges desk | Spread rows (min 1.0) | 12 |
| NFL Edges desk | Negative selected-side spread display | **7** |
| NFL Edges desk | Spread Fair/Book vs edge arith mismatch | **2–5** (consensus vs stake; desk API showed 5 at first trace) |
| NFL Edges desk | Totals negative display / arith mismatch | **13** / **4** |
| NFL Edge Board assemble | Spread+total arith mismatch | 0 |
| All Edge Board sports | Negative `edgeMagnitude` | 0 |

## After counts (same live fair-lines, fixed contract)

| Surface | Metric | Count |
| --- | --- | ---: |
| NFL desk spreads painted | 12 |
| NFL desk spreads neg sign / arith | **0 / 0** |
| NFL desk totals neg sign / arith | **0 / 0** |
| Fail-closed omissions (unreconcilable) | **0** (all reconcile once Book = stake) |
| Unresolved customer-truth defects | **0** |

## Fix (shared contract — see code)

Module: `apps/web/lib/edge-board-customer-truth.ts`

- **Handicap** (spread / puck-line / run-line): selected-side advantage = `abs(fair − displayed_market)`; side from sign of `(fair − market)`; display positive magnitude; market painted = calc market.
- **Totals:** own formula — advantage = `abs(fair − market)`; Over if signed > 0 else Under; display positive.
- **Moneyline:** own formula — advantage = `abs(model_prob − market_prob)` (pp); Home if signed ≥ 0 else Away; display positive pp.
- **Fail closed:** any disagreement between calculated and displayed → no edge chrome (`DATA GAP` / omit row edge), never paint a wrong edge.

## Stage-2 detection gap

Caught by **human/customer review** before Academy / P14 automated system. Gap belongs in Stage-2 evidence: no full-slate customer-truth scanner for Fair↔Market↔Edge identity + selected-side sign on desk **and** Edge Board across sports.

## Verification checklist

See `VERIFICATION_CHECKLIST.md` (Product Engineer + Riley Nash, independent).
