# NFL Season-Ready Closeout — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Branch: `feat/nfl-season-ready-closeout` → `deploy-vercel`.

Depends on merged True PR stack **#140–#147** (blend, player finite, past SOS,
continuity, QB premium, Future SOS, harden, product surface).

## Goal

Ship a coherent, **preseason-complete** NFL product: wire what we built, make
outlook surfaces honest about schedule difficulty, document how PR updates when
games start, and refuse false degraded / fake in-season sample before Week 1.

**Preseason-complete** means honest, usable, and stable when Week 1 hits — not
“every future feature done.”

## Locked contract (unchanged)

| Layer | Meaning |
|-------|---------|
| Model / intrinsic PR | Research fair strength |
| KEI | Late reprice |
| Edge | KEI vs market only |
| Future SOS (#145) | Schedule **outlook** only — never intrinsic PR |

## A. Outlook surfaces use projected SOS

### Confirmed already live (engine)

| Surface | Behavior | Module |
|---------|----------|--------|
| Season sim `team_wins` | Annotates `projected_sos_2026`, `schedule_difficulty`, analytic E[wins] | `projected_sos.attach_projected_sos_to_team_wins` |
| Survivor evaluate / plan / suggest | Per-team `path_difficulty_grade` + `schedule_difficulty` | `survivor.score_team_survivor` |
| True PR product surface | 2026 SOS chip framed as outlook | `true_pr_product` + `#147` UI |

Intrinsic PR / Week-1 blend / Edge Board game lines are **not** rewritten by SOS.

### Closeout wiring (this PR)

- Survivor weekly ranker + planner UI show **Path SOS** (easy/avg/hard + letter)
- Copy: **harder schedule ≠ weaker team**
- Power ratings / True PR board notes clarify E[wins] moves with slate, PR does not

### Smell proof

`services/model-service/tests/test_nfl_season_ready_closeout.py` + existing
`test_nfl_projected_sos_2026.py`:

1. Soft-SOS team → higher analytic E[wins] than equal-PR hard-SOS team
2. Intrinsic PR ranking unchanged by SOS annotate
3. Survivor rows expose SOS fields + “Harder schedule ≠ weaker team” notes

## B. In-season update rules (source of truth for September)

Ops note = source of truth for how PR updates after kickoff. Blend curve is
**already shipped** (`games/8`); this closeout documents + lightly guards it.

| Games played | Weight on current (`w_current`) | Product posture |
|-------------:|--------------------------------:|-----------------|
| 0 | 0.00 | Prior only — no current sample |
| 1 | 0.125 | **Prior-heavy** (no Week-1 cliff) |
| 2 | 0.250 | **Prior-heavy** early season |
| 3–7 | `g/8` | Blending ramp |
| ≥8 | 1.00 | Current-dominated |

Rules:

1. **Games 0–2:** prior-heavy, wide uncertainty; continuity + QB still matter.
2. **Games 3–8:** existing `games/8` blend ramp (do not redesign).
3. **Do not** fully replace prior after one noisy week.
4. **Injury / QB inactive:** `apply_strength_shock` moves **current**
   (`offense_index` / `defense_index`) while locking **full-strength** indices.
   Live boards / matchups consume **current**. Full-strength remains the
   intrinsic / SOS opponent package.
5. Early-season uncertainty widen (W1–W4) remains in `calibration.py` /
   [`nfl-early-season-uncertainty.md`](nfl-early-season-uncertainty.md).

### Light implementation

- `assert_no_early_season_blend_cliff` inside `blend_packages`
- True PR blend chip: games 0–2 labeled **Prior-heavy** (weights still `games/8`)
- Tests refuse `w_current ≈ 1` after 1 game

## C. Close-out honesty

| Check | Standard |
|-------|----------|
| Preseason banners | Packaged schedule/depth = healthy notice, not “degraded” |
| Freshness banner | Only real `degraded` / `failed` — not transport timeout |
| Thin drivers | Hide or mark approx / context-only (same as `#147`) |
| Blend before Week 1 | Prior-heavy; **no fake in-season sample** |
| Continuity + QB | Still visible on Season Model True PR surface |

## Preseason-complete vs waits for real games

### Preseason-complete (this phase)

- True PR stack + product surface (#140–#147)
- Future SOS on survivor / season outlook (+ UI path SOS)
- In-season blend rules documented + guarded
- Full-strength vs current injury contract confirmed
- Model / Game Boxes / Survivor / Fantasy load paths honest

### Waits for real games / post-kickoff

1. **CLV logging cadence** — weekly close capture + grading once REG books settle
2. **Weekly depth refresh** — roster/injury depth as of each slate
3. **In-season SOS refresh** — recompute opponent book after upsets (still outlook-only)
4. **Measured QB premium EPA** — when live splits thicken beyond packaged context
5. **Continuity returning-production joins** — when DB roster joins leave stub path
6. **Playoff-odds surface** consuming SOS-annotated win totals (if product wants it)

## Smoke checklist

| # | Check | Result |
|---|-------|--------|
| 1 | Soft-SOS better path / E[wins] than equal-PR hard-SOS | PASS (closeout + #145 tests) |
| 2 | Intrinsic PR unchanged by SOS wiring | PASS |
| 3 | After 1 game: `w_current = 1/8`, prior not cliffed | PASS |
| 4 | Model / survivor / true-PR surface load; blend preseason prior-heavy | PASS |
| 5 | Continuity + QB drivers present on product surface | PASS |
| 6 | Injury shock moves current; full-strength locked | PASS |

Commands:

```bash
cd services/model-service && python -m pytest \
  tests/test_nfl_season_ready_closeout.py \
  tests/test_nfl_projected_sos_2026.py \
  tests/test_nfl_true_pr_product_surface.py -q

cd apps/web && pnpm exec vitest run \
  __tests__/lib/nfl-true-pr-format.test.ts \
  __tests__/lib/nfl-season-engine-format.test.ts
```

## Explicit non-goals (still)

- New rating layers (OL premium, full defensive EPA rebuild, …)
- Fantasy Phase 3 / CFB / mobile app
- KEI / tag policy redesign

## Progress line

NFL is **preseason-complete** for this phase: SOS-aware outlook surfaces,
documented in-season update rules, honest banners/drivers, and stable Week-1
posture. Remaining work is post-kickoff ops — not a blocker to call the phase done.
