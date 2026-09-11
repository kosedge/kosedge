# Line Curve Phase 1 — Implementation Plan

**Status:** research-only · fail-closed · **not** a teaser calculator  
**Scope:** spreads only · single-game + 2-leg · no production publish · no PLAY language  
**Branch target:** `deploy-vercel`  
**Naming:** `line_curve` / `alternate_pricing` / `joint_optimizer` only. Never `teaser`.

The core object is a **line-curve optimizer over alternate spreads/totals**. Phase 1 prices **alternate spreads** as a continuous surface against the model margin distribution.

---

## Existing systems inspected (reuse, do not fork)

| Layer                      | Authoritative files                                                                                                                        | What we reuse                                                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Odds Lake / live warehouse | `services/model-service/src/services/{nfl,cfb}_warehouse/odds_lake.py`, `infra/db/001_init.sql` `odds_snapshots`                           | Event id = Odds API `event.id` → `games.external_id`. Book = `sportsbooks.code`. Vintage = `captured_at` / book `last_update`. **Mainline only today.**          |
| Live Odds client           | `apps/web/lib/odds-api.ts` (`OddsEvent`, `OddsBookmaker`, `ALLOWED_BOOKS`)                                                                 | Outcome `{ name, point, price }`. Do not invent books or prices.                                                                                                 |
| Freshness / identity       | `apps/web/lib/cfb-edge-board-odds.ts`, `apps/web/lib/edge-board-market-identity.ts`                                                        | Fail-closed stale market. `alternate_*` is a distinct period family — never mix into featured FG compare.                                                        |
| American / EV              | `apps/web/lib/american-odds.ts` (`americanImpliedProb`, `isValidAmericanOdds`); `apps/web/lib/nfl-publish-policy.ts` (`americanToDecimal`) | Implied prob + decimal. Line Curve adds **push-aware EV** and **hold tracking**.                                                                                 |
| CFB model                  | `apps/web/lib/cfb-season-engine.ts` (`CfbProjectGameResponse`), `apps/web/lib/cfb-kei-artifacts.ts` (`CfbKeiGame`, `findCfbKeiGame`)       | Fair spread = `model_spread_home` (research). Uncertainty = `kei.model_sigma` / `margin_sd`. IDs = `game_id` + `engine_version` / `kei_version`.                 |
| NFL model                  | `apps/web/lib/nfl-fair-lines.ts`, `nfl_simulator.py`, `nfl-lineage.ts`                                                                     | Fair spread = `modelSpreadHome` (research) vs KEI `handicapSpreadHome`. Bind via `gameId` + `model_version` + `active_run_id`. **No exported margin PMF today.** |
| Edge Board service         | `apps/web/lib/build-edge-board-rows.ts`, `packages/contracts/src/edge-board.ts`                                                            | Sport / event / side / book identity. Line Curve does **not** write Edge Board tags.                                                                             |
| Research UI                | `SportHubShell`, `NflFairLinesClient`, `CfbProjectGameClient`, `sport-pro-nav.ts`                                                          | Dark KosEdge desk chrome. SSR shell + client fetch.                                                                                                              |

**Gap (do not paper over):** alternate spreads are listed in NFL `PERIOD_MARKETS` but **never exported, persisted, or fetched**. `odds_snapshots` is one row per `(game, book, market, captured_at)` with a single `spread_home` — it cannot store an alt surface. NFL sim margins stay in-process; CFB is Gaussian WP on `margin_sd`. Key numbers today are **tag geometry only**, not distribution mass.

---

## Files to add

### Engine (pure; no UI)

- `apps/web/lib/line-curve/types.ts` — `LineCurvePoint`, snapshot / model provenance, research labels
- `apps/web/lib/line-curve/american.ts` — implied prob, fair American, hold, push-aware EV per $1
- `apps/web/lib/line-curve/margin-pmf.ts` — integer football score lattice → margin PMF → win / cover / push / loss
- `apps/web/lib/line-curve/alternate-pricing.ts` — one-leg curve + incremental / marginal cost
- `apps/web/lib/line-curve/guardrails.ts` — stale / missing / duplicate / inconsistent / unbound model
- `apps/web/lib/line-curve/joint-optimizer.ts` — 2-leg cartesian optimizer; **correlation interface reserved**
- `apps/web/lib/line-curve/labels.ts` — `BEST VALUE` \| `FAIR` \| `OVERPRICED` \| `INSUFFICIENT` only
- `apps/web/lib/line-curve/service.ts` — `getLineCurve` / `evaluateAltLine` / `optimizeTwoLegLineCurve`
- `apps/web/lib/line-curve/odds-adapter.ts` — parse Odds API `spreads` + `alternate_spreads`; optional live fetch
- `apps/web/lib/line-curve/model-adapter.ts` — bind CFB KEI / project-game and NFL fair-lines to `ModelMarginInput`
- `apps/web/lib/line-curve/fixtures/missouri-oklahoma.ts` — research fixture (prices + model inputs; **no hardcoded winner**)
- `apps/web/lib/line-curve/index.ts`

### Tests

- `apps/web/__tests__/lib/line-curve/american.test.ts`
- `apps/web/__tests__/lib/line-curve/margin-pmf.test.ts`
- `apps/web/__tests__/lib/line-curve/alternate-pricing.test.ts`
- `apps/web/__tests__/lib/line-curve/joint-optimizer.test.ts`
- `apps/web/__tests__/lib/line-curve/guardrails.test.ts`
- `apps/web/__tests__/lib/line-curve/missouri-oklahoma.test.ts`

### API / UI

- `apps/web/app/api/line-curve/route.ts` — GET/POST one-leg (Pro-gated)
- `apps/web/app/api/line-curve/optimize/route.ts` — POST 2-leg
- `apps/web/app/(pro)/pro/cfb/line-curve/page.tsx`
- `apps/web/app/(pro)/pro/nfl/line-curve/page.tsx`
- `apps/web/components/pro/line-curve/LineCurveResearchPanel.tsx`
- `apps/web/components/pro/line-curve/LineCurveChart.tsx` — SVG only (no new chart dependency)

---

## Files to change

- `apps/web/lib/sport-pro-nav.ts` — CFB + NFL tools: **Line Curve**
- `apps/web/lib/pro-sport-desk.ts` — research desk card (CFB + NFL)
- `apps/web/lib/pro-sport-ia.ts` — overview link (research, not decision CTA)
- `packages/contracts/src/line-curve.ts` + export from `packages/contracts/src/index.ts` — shared point / label types

**Do not change:** `odds_snapshots` persist path, Edge Board assemble, tag/PLAY policy, Odds Lake export filters, featured market identity.

---

## Existing services reused

- `americanImpliedProb` / `isValidAmericanOdds` (`american-odds.ts`)
- `americanToDecimal` (`nfl-publish-policy.ts`)
- `ALLOWED_BOOKS`, `OddsEvent` (`odds-api.ts`)
- `getOddsApiKeys()` for optional live `alternate_spreads` pull
- `findCfbKeiGame` + KEI pack `model_spread_home` / `model_total` / `kei.model_sigma` / versions
- `fetchCfbProjectGame` when team codes are present and KEI is incomplete
- NFL: `fetchNflFairLines` row by `gameId` + `modelVersion` / `active_run_id`
- `getProAccessState`, `pageDataJsonResponse`, `SportHubShell`
- CFB 6h freshness pattern → Line Curve uses a **stricter research max-age** (2h) documented in guardrails

---

## Schema additions

**None in production Postgres for Phase 1.**

Reason: `odds_snapshots` cannot hold multiple spread points per `(game, book, market, captured_at)` without breaking beat dedup and Edge Board mainline identity. Alternate prices stay on the Odds API event payload (or an injected research snapshot).

Provenance on every row (in-memory / response, not a new table):

- `oddsSnapshotId` = `{eventId}:{book}:{capturedAt}` (book/market `last_update`; never `Date.now()`)
- `modelRunId` = CFB `engine_version` + `kei_version` + `game_id`, or NFL `model_version` + `active_run_id` + `gameId`
- `timestamp` = book vintage

A future `line_curve_alt_snapshots` warehouse (point + price + vintage per row) is deferred until we decide to persist alts. Do not overload `odds_snapshots`.

---

## Probability + pricing design

1. **Margin PMF** from expected home/away scores (derived from model spread + total) via an integer football scoring lattice (TD / FG / PAT / safety). Key numbers **3 / 7 / 10 / 14 emerge from scoring**, not from a hardcoded teaser table.
2. Location/scale the lattice so mean margin and `margin_sd` match the bound model run. Extra variance is smooth integer noise — not spiked onto 3/7.
3. For each **posted** alt: cover / push / loss from the PMF. No linear point-value. No interpolation of missing book prices.
4. Fair American from model cover (push excluded from the win/loss price; push mass carried separately).
5. EV per $1 risked: `p_cover * (decimal-1) + p_push * 0 + p_loss * (-1)`.
6. Hold tracked separately when both sides of a line exist; single-side implied ≠ true market probability.
7. Incremental vs **base mainline** (not vs an invented teaser start): Δ implied, Δ model cover, marginal cost per probability point.

---

## Two-leg optimizer + independence (mandatory)

**Do not estimate joint probability by silently multiplying two cover percentages.**

Phase 1 default is independence, but it must be **named in code and on every optimizer row**:

```ts
correlation: {
  assumption: "independent",
  documented: true,
  adjustment: null,
  note: "Phase 1 joint = independent cover/push/loss product. Correlation reserved."
}
```

Interface now (implement independent only):

```ts
type JointCorrelationModel = {
  assumption: "independent" | "adjusted";
  adjustment: { rho?: number; source?: string } | null;
  joint(legA: OutcomeMass, legB: OutcomeMass): JointMass;
};
```

Parlay settlement: loss on either leg loses; one cover + one push **reduces to the covering straight**; double push pushes. Book parlay price is either fixture-quoted or `multiplicative_from_posted_legs` — never a fabricated alt. Rank by EV. Asymmetric lines allowed (`+1.5` / `+3.5`).

---

## Guardrails

Fail closed (no curve, `INSUFFICIENT`, no invented numbers) when:

- Odds vintage missing or older than `LINE_CURVE_MAX_AGE_MS` (2h)
- Duplicate `(book, side, alt_line)` prices that disagree
- Internally inconsistent (both sides same sign, invalid American `|price| < 100`)
- Model run/version cannot be tied to the exact event
- Requested alt has no posted book price (no interpolation)
- Missing snapshot id or model run id

Research labels only: `BEST VALUE` / `FAIR` / `OVERPRICED` / `INSUFFICIENT`. No PLAY / LEAN / stake chrome.

---

## Unresolved assumptions

1. **Live alt pull is optional.** Odds API `alternate_spreads` is not in current pulls (credit cost). UI ships a Missouri/Oklahoma research fixture plus POST-injected snapshots. Live event fetch is best-effort and fail-closed.
2. **NFL sim replicates are not exported.** Phase 1 NFL uses the same football lattice from fair-lines expected/total + decision uncertainty. Wiring `nfl_simulator` margin histograms is a later upgrade of the **same** `ModelMarginInput` interface.
3. **Same-game correlation is out of Phase 1.** Two legs are distinct events. The correlation interface is reserved so we do not have to rewrite the optimizer.
4. **Totals / 3+ legs / SGP** are out of Phase 1.
5. **Default book** for research display = request book, else DK → FD (same stake preference as NFL fair-lines). Never best-of-books shopping.
6. **CFB FCS / missing KEI** → fail closed (Missouri W1 FCS opener is not a valid model bind; the fixture uses constructed research games, not that KEI row).

---

## Test plan

| Case                         | Assertion                                                                                                |
| ---------------------------- | -------------------------------------------------------------------------------------------------------- | --- | -------------- |
| American conversion          | +100 → 0.5; -110 → 0.5238; invalid `                                                                     | p   | <100` rejected |
| EV math                      | -110 @ 0.55 cover / 0 push > 0; push mass does not count as a loss                                       |
| Push handling                | Integer line has `P(push)>0`; half-point `P(push)=0`                                                     |
| Integer margin PMF           | Mass only on integers; P(win)+P(push)+P(loss)=1; extra mass near 3/7/10/14 vs a flat Gaussian            |
| Alt-line probability         | Buying points (more favorable line) **raises** cover, **does not** raise linearly per half-point         |
| Asymmetric 2-leg             | Optimizer may pick `+1.5` / `+3.5` (or other) — not forced symmetric                                     |
| Mizzou +1.5 / OU +1.5 @ -103 | Fixture compares that combo against **all** posted alt pairs; test does **not** hardcode whether it wins |
| Independence metadata        | Every joint row has `correlation.assumption === "independent"` and `documented === true`                 |
| Stale odds                   | Vintage > 2h → reject                                                                                    |
| Missing model run            | No `modelRunId` / event mismatch → reject                                                                |
| Duplicate odds               | Same alt, two prices → reject                                                                            |
| No PLAY strings              | Labels ∪ copy never include PLAY / LEAN / teaser                                                         |

---

## Out of scope (explicit)

Production Edge Board publish, stake tags, Odds Lake rematerialize, Railway beat `alternate_spreads` ingest, totals curve, same-game parlays.
