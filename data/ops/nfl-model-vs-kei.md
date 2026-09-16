# NFL Model vs KEI (product contract)

**As of:** 2026-08 (first real NFL split)

## Definitions

| Layer | Meaning for NFL **now** | Source |
|-------|-------------------------|--------|
| **Model** | Pre-market-blend Monte Carlo research fair (spread + total) | `diagnostics.market_blend.pre_blend_margin_mean` → `model_spread_home = -pre_blend_margin`; `pre_blend_total_mean` → `model_total_mean` when `*_applied` |
| **KEI (handicap)** | Published product line used by Edge Board + PLAY/LEAN/PASS | Denormalized `spread_home` / `total_mean` (post-blend + totals calibration + overlays) |
| **Edge / tags** | KEI vs market only | Never Model vs market |
| **Action layer** (Decision Engine) | Model fair vs market | Edge Board Action Labels + Play-To (see `nfl-decision-engine-edge-board-20260809.md`); coexists with KEI publish tags |

## What is honest today

- When market blend was applied for a market, Model ≠ KEI for that market (spread and/or total).
- When blend was **not** applied, Model = KEI (identity). We do **not** invent cosmetic deltas.
- Fair ML / win probs are computed **after** blend today → Model ML = KEI (identity). No dual ML columns on Fair Lines yet.
- Injury nowcast / weather remain **inputs** to full research sims (`line_role=model`).
- **Kickoff Injury → KEI cadence** (2026-08-11) can reprice KEI only via `line_role=handicap`, freezing stamped `model_markets`. Library-only — not wired. See `data/ops/nfl-injury-kei-cadence-20260811.md`.
- **Week 1 Gate B desk reprice** (2026-08-13) is library / ops-table only. Publish fair/edge is fail-closed (2026-09-16): `apply_week1_kei_reprice` must not write handicap columns that drive published fair/edge. See `data/ops/nfl-v1-handicap-overlay-week1-kei-fail-closed-20260916.md`. Mutate-fair V1.0: injury/rest/weather bake into B0 at remat; stamped `model_*` already carries overlay-class factors — overlay is not an independent layer on frozen fair.
- Legacy projection rows without stamped `model_markets` still resolve Model from `diagnostics.market_blend` on `/nfl/fair-lines` read.

## Pipeline stamp

On each `run_nfl_market_simulations` insert (and ad-hoc `/nfl/simulations/{game_id}`), projection JSON is annotated with:

- `model_markets` / `handicap_markets`
- top-level `model_*` / `handicap_*` aliases
- `line_role` (`model` for full research re-sims; `handicap` for injury→KEI product-only reprice)

No new DB columns required — JSON projection + fair-lines payload fields.

## Surfaces

- **Fair Lines desk** (`/pro/nfl/fair-lines`): Model spread/total + KEI spread/total columns.
- **Edge Board**: KEI columns + tags; `modelKei` attached when available but not used for edges/tags.
- **`GET /nfl/fair-lines`**: emits `model_*`, `handicap_*`, `model_equals_kei`; top-level `spread_home` / `total_mean` remain KEI.

## Remaining limitations

1. No separate Model ML / win-prob distribution (would need pre-blend win rates).
2. Injury→KEI handicap path (`run_injury_kei_window`) stays library-only / not wired. See `data/ops/nfl-v1-handicap-overlay-week1-kei-fail-closed-20260916.md`.
3. Supervised overlay / slate totals cal after blend move KEI further from Model; that is intentional (product line) and documented.
4. Rows with empty/missing `market_blend` stay identity until the next sim stamps or diagnostics carry pre_blend.
