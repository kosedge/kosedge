# NFL True PR Product Surface — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Branch: `feat/nfl-true-pr-product-surface` → `deploy-vercel`.

PR: https://github.com/kosedge/kosedge/pull/147

Depends on merged True PR stack **#140–#146**.

## Goal

Surface key true-PR drivers on the Pro NFL model experience so users see
**why** a team sits where it sits — display + copy only. No new rating math.
Edge Board / KEI / tag policy untouched.

## Locked contract (shown in UI)

| Layer | Meaning |
|-------|---------|
| Model / intrinsic PR | Research fair strength headline |
| KEI | Late reprice (not this surface) |
| Edge | KEI vs market only (Edge Board unchanged) |
| 2026 SOS | Schedule **outlook** — never rewrites intrinsic PR |

## What’s shown

Primary: `/pro/nfl/model` — ranked True PR board with compact driver chips.

Secondary:

- Team intel overview (`/pro/nfl/teams/{TEAM}/overview`) — True PR strip when
  strength is already wired
- Power ratings page — link + note pointing to Season Model drivers (expected
  wins board stays the outlook board)

| Driver | User sees | Source |
|--------|-----------|--------|
| Continuity | High / mid / low + short reason | `drivers.continuity` on strength, else display-only book (labeled approx) |
| QB premium | Elite lift / lift / neutral / drag / context-only + starter | Strength drivers when fidelity real; else starter context, **no invented lift** |
| Past SOS | Soft / average / hard prior slate | `drivers.past_sos` (baked packaged / live) |
| Projected 2026 SOS | Easy / average / hard outlook + “does not change intrinsic PR” | `compute_league_projected_sos` (existing) |
| Blend | Prior-heavy vs blending vs current (games into 8-game ramp) | `drivers.blend` + games_played |

Intrinsic PR headline = `0.5 × (full_strength_off + full_strength_def)` — same
composite used by projected SOS opponent power. Off/Def indices shown under it.

## Copy rules (approximate / missing)

1. If evidence is missing → **hide chip or mark unavailable** — never invent
   “elite continuity” / “elite lift”.
2. Approximate factors get an **approx** badge.
3. Projected SOS always carries **outlook** framing.
4. Preseason blend is **Prior-heavy** with explicit “no current sample”.
5. QB quality sample missing → **Context only** (starter name) — magnitude
   hidden; noisy tenure labels suppressed.

## API / wiring

| Piece | Path |
|-------|------|
| Serializer | `nfl_season_engine/true_pr_product.py` |
| Upstream | `GET /nfl/season-engine/true-pr` |
| BFF | `GET /api/nfl/season-engine/true-pr` |
| Web fetch | `apps/web/lib/nfl-true-pr.ts` |
| Format helpers | `apps/web/lib/nfl-true-pr-format.ts` |
| Board UI | `TruePrDriversBoard` + `TruePrDriverChips` |
| Team strip | `TruePrTeamStrip` |

Display-only continuity / QB overlays may attach when packaged strengths still
stub those drivers — **indices are never mutated**.

## What’s still engine-only

- Full continuity returning-production / roster-churn when DB roster joins are
  thin (packaged cold path stays approximate)
- Measured QB premium EPA process (needs DB/splits; packaged = context only)
- Injury-at-time Past SOS depth, full venue model
- Deep factor drill-down JSON on the board (kept out of the scannable UI)

## Gaps (explicit)

1. Full opponent-tier pages
2. Deep driver drill-down / encyclopedia
3. Public non-Pro teaser
4. Power-ratings expected-wins table does not inline chips (link only)

## Layout choices

- **Cards / compact rows**, not a wide diagnostics table — mobile wraps chips
- Intrinsic PR is the only large number; drivers are secondary chips
- Design tokens match existing Pro NFL desk (gold / black / border) — no purple
  glow redesign
- Projected SOS chip labeled `outlook` so it cannot be misread as PR

## Live examples (packaged 2026 path, local, 2026-08-08)

| Team | Intrinsic PR | Continuity | QB | Past SOS | 2026 SOS | Blend |
|------|-------------:|------------|----|----------|----------|-------|
| **SEA** | ~1.091 (#2) | Mid (OC change, approx) | Context only (Darnold; no invent lift) | Average | Average | Prior-heavy |
| **NYG** | ~0.934 (#27) | **Low** (new staff) | Context only (Dart) | Soft prior slate | Average | Prior-heavy |
| **DET** | ~1.044 (#8) | Mid (thin evidence labeled approx) | Context only (Goff) | Hard prior | **Easy** outlook | Prior-heavy |
| **CLE** | ~0.978 (#21) | **Low** (new staff) | Context only | Average | **Easy** outlook | Prior-heavy |

Smell checks on this path:

1. Contender with stable prior story → mid continuity + prior-heavy (high band
   needs fuller DB returning-production; we do **not** fake high).
2. New-regime / new-QB teams (NYG, ARI, LV) → **low** continuity, QB context
   only — not finished identity.
3. Soft vs hard 2026 slate differs on outlook chips (DET/CLE easy); intrinsic
   PR independent of outlook framing.
4. Preseason blend never shows “current sample”.
5. Chips wrap on narrow widths.
6. Edge Board untouched.

## Tests

- `services/model-service/tests/test_nfl_true_pr_product_surface.py`
- `apps/web/__tests__/lib/nfl-true-pr-format.test.ts`

## Explicit non-goals (honored)

- New rating model
- Fantasy desk / CFB
- KEI / tag policy
- Full team encyclopedia redesign
