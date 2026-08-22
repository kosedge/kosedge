# Edge Action / Opens + Fantasy Draft-Board UX — 2026-08-22

**Branch:** `cursor/edge-action-opens-fantasy-ux-4b71` → `deploy-vercel`  
**Baseline:** post-#283 (`a0ced26`)  
**Scope:** desk trust only — no sim, no model rewrite, no new products

## Root cause — Action Edge 0.0 · Mkt —

Live fair-lines (Railway) often ship `decision.spread.market_line = null` with
`edge_magnitude = 0` / `action_label = PASS` / `reason = missing_fair_or_market`
because the Odds feed on the worker is degraded (401 → `market_joined_count=0`).

The web Edge Board still paints **Current** from the Vercel Odds overlay
(`row.best`). The Edge column recomputes `KEI − Current` in the client, so users
see e.g. Spread edge 0.7 / Total edge 1.2 while Action stays:

`PASS · Edge 0.0 · Fair KEI −4.2 · Mkt —`

**Tag/action was not using the same market side as the displayed edge.**

### Fix

1. **Single market input** (`resolveMarketLineForEdge`): stake → DK → FD →
   consensus → **Current (best)**. Only missing when none exist.
2. **Ignore server decision** when its market line is empty but a usable
   Current/consensus exists — recompute locally.
3. **`syncEdgeBoardActionsWithCurrent`** after Odds overlay (and again in
   assemble) so Action Edge / Mkt / label track Current.
4. UI: never show Action `Edge 0.0` when Mkt is empty — honest `Edge —`.
5. Footer copy: Action = KEI vs Current (same market as Edge column).

PASS thresholds unchanged (Week 1–2 early bands). A 0.7 spread edge remains
PASS (&lt; 1.25); magnitude must still display 0.7, not 0.0.

## Week 1 open audit (live fair-lines, 2026-08-22)

16 REG Week 1 games. Open = first `odds_snapshots` capture. **Never**
`open = current`.

| Game | Open spread | Open O/U | Join | Notes |
|------|-------------|----------|------|-------|
| ARI@LAC | −10.5 | 46.5 | exact | |
| ATL@PIT | −3.0 | 41.5 | exact | |
| BAL@IND | 3.5 | 48.5 | exact | |
| BUF@HOU | 1.5 | 44.5 | exact | |
| CHI@CAR | 2.5 | 45.5 | exact | |
| CLE@JAX | −7.5 | 40.5 | exact | |
| DAL@NYG | — | — | missing | no snapshot after ±1d alias |
| DEN@KC | — | — | missing | no snapshot after ±1d alias |
| GB@MIN | −1.5 | 45.5 | exact | |
| MIA@LV | −3.5 | 40.5 | exact | |
| NE@SEA | — | — | missing | no snapshot after ±1d alias |
| NO@DET | −7.0 | 49.5 | exact | |
| NYJ@TEN | −2.5 | 38.5 | exact | |
| SF@LAR | — | — | missing | Melbourne date skew class; ±1d join shipped |
| TB@CIN | −3.5 | 52.5 | exact | |
| WAS@PHI | −4.5 | 47.5 | exact | |

**Counts:** exact 12 · alias 0 · missing 4 (spread **and** total — same join path).

**Open join hardening:** alias candidate match now uses `game_date ± 1 day`
(warehouse rematch convention) so Melbourne / timezone skew can resolve when a
parallel Odds UUID exists. Still honest `—` when no snapshot row exists.

**Current / market:** worker Odds feed degraded (401) → all W1 `market_*` /
`best_*` null on fair-lines. Board Current still comes from web Odds overlay
when Vercel keys are healthy. Action now follows that Current.

## Before / after (examples)

### NE@SEA (smell — user’s live case)

| Field | Before | After (with Current +3.5 / o44.5 overlay) |
|-------|--------|---------------------------------------------|
| Open | — / — (`join=missing`) | — / — (honest; no invent) |
| Current | +3.5 / o44.5 (overlay) | unchanged |
| KEI | ≈ −4.2 / 43.3 | unchanged |
| Edge col | 0.7 SEA / 1.2 Under | unchanged |
| Action | PASS · Edge **0.0** · Mkt **—** | PASS · Edge **0.7** / **1.2** · Mkt **−3.5** / **44.5** |

PASS is correct under Week-1 early bands; the bug was zeroing magnitude / blank Mkt.

### Large edge when Mkt empty + Current present (unit)

KEI −7 vs Current −3 → Action PLAY · Edge 4.0 · Mkt −3 (not stake-only empty → 0.0).

### Stake close still preferred when present (unit)

DK/stake −6.5 with shop best −3 → Action grades vs −6.5 (PASS · 0.5), Current column still shows best.

## Fantasy — draft board UX

| Item | Change |
|------|--------|
| Default tab | `value` (already on page; component default now `value` too) |
| Default filter | `trueValuesOnly = false` — full ADP-matched board, not \|Δ\|≥8 only |
| Tab order | **Value / ADP** → Model rank → Builder |
| Nav chip | “Draft board” (was “Model rank”) |
| Hero / footer | Short Methods link; no essay wall |
| K/DST | Unchanged publish path (#283). Live `kdst-publish-status`: **K=32 / DST=32** |

## Smell checklist

| # | Check | Pass |
|---|--------|------|
| 1 | Current present + KEI≠market → Action Edge ≠ 0.0 unless PASS threshold | ✅ unit + NE@SEA example |
| 2 | No Action 0.0 while Spread/Total edge shown non-zero | ✅ sync + UI guard |
| 3 | Open — / — only where join missing; O/U audited for all 16 | ✅ table above |
| 4 | Fantasy first load sorts by value/ADP | ✅ default tab + sort |
| 5 | Mobile Fantasy reads as draft board | ✅ Value / ADP primary; cards keep Δ |
| 6 | K=32 DST=32 still | ✅ ops status ready |
| 7 | No new sim; Edge still 16 Week 1 games | ✅ |

## PR #284 finish smoke (2026-08-22)

**CI (merge bar = Production Gate on `deploy-vercel`):**

| Check | Status |
|-------|--------|
| Web typecheck | ✅ green (`16ab755`) |
| Web Next build (Vercel-identical) | ✅ green |
| Vercel preview deploy | ✅ green |
| PR Quality Checks (`pnpm format:check` repo-wide) | ❌ red — ~235 pre-existing files (same class as #283); **not** ship bar |

**Edge Action smoke** (`apps/web/__tests__/lib/edge-action-smoke-284.test.ts`):

| Game | Open | Current | Action spread | Action total | Pass |
|------|------|---------|---------------|--------------|------|
| NE@SEA | — / — | +3.5 / 44.5 | PASS · Edge 0.7 · Mkt −3.5 | PASS · Edge 1.2 · Mkt 44.5 | ✅ |
| CLE@JAX | +7.5 / 40.5 | +7.5 / 41.0 | PASS · Edge 0.6 · Mkt −7.5 | PASS · Edge 0.5 · Mkt 41.0 | ✅ |
| BUF@HOU | −1.5 / 44.5 | +1.5 / 44.0 | Action ≠ 0.0 · Mkt −1.5 | Action ≠ 0.0 · Mkt 44.0 | ✅ |
| DAL@NYG (missing open) | — / — | +2.5 / 46.5 | Action ≠ 0.0; open not invented | same | ✅ |

**Opens:** live fair-lines still 12 exact / 4 missing (`NE@SEA`, `SF@LAR`, `DAL@NYG`, `DEN@KC`). No `open = current`.

**Fantasy:** `/pro/nfl/fantasy` → `initialTab="value"`; tab order Value/ADP first; `trueValuesOnly` default off. K/DST publish status **32/32 ready**.

**Merge-ready:** **Yes** for Production Gate + desk smoke. PR Quality format noise is pre-existing debt, not a regression from #284.

## Tests

- `apps/web/__tests__/lib/nfl-edge-board-from-fair-lines.test.ts` — Current-for-Action + overlay sync
- `services/model-service/tests/test_nfl_routes.py` — open alias ±1 day SQL

## Deploy notes

- **Vercel** (web): Action sync + Fantasy UX — ships with this PR.
- **Railway** (model-service): open ±1d join — only helps when orphan snapshots exist; does not invent opens.
- Worker Odds 401 is a **secrets/feed** issue (explicit non-goal deep dive). Web overlay + Action sync is the desk fix.
