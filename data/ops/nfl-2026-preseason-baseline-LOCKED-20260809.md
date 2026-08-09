# NFL 2026 Pre-Season Baseline — LOCKED

**Status: LOCKED** — official 2026 pre-season baseline for player yard/TD futures and fantasy.

| Field | Value |
|-------|-------|
| Engine | `nfl-season-engine-v1.24-soft-piles-cleanup` |
| Bundle id | `nfl-preseason-sim-2026-20260809T165350Z` |
| Bundle path | `data/ops/nfl-preseason-sim-2026-20260809T165350Z` |
| Engine commit | `ab16a4e7218632b31eb186caf51800ea3f31a872` (`feat/nfl-team-variance-lift`) |
| Git tag | `nfl-2026-preseason-baseline-v1.24` |
| Web pointer | `data/ops/nfl-web-launch-bundle.json` (`locked_snapshot: true`) |
| Locked at (UTC) | 2026-08-09 |
| N team / player | 100,000 / 1,000 |

## Provenance (honest)

- The **100k Monte Carlo** team/player sim ran on **v1.23** (`nfl-season-engine-v1.23-soft-flags-enterprise`), source research dir  
  `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.23-soft-flags-enterprise-Nteam100000-Nplayer1000-20260809T153419Z`.
- **v1.24** is a **post-board tapered rebuild** (soft-pile cleanup): rush/PF/win ceiling–floor stacks cleared with tapered fall-off + residual micro-spread; Mike Evans label → TB. Confirmation board is a packaged rebuild of that 100k candidate — **not** a second 100k MC.
- User accepted pile cleanup and gave explicit clearance to lock the cleaned v1.24 board.

Ops trail:

- Soft-pile cleanup: `data/ops/nfl-soft-piles-cleanup-20260809.md`
- Prior candidate report: `data/ops/nfl-100k-expert-sim-candidate-20260809.md`

## Conservation summary

| Check | Value |
|------:|------:|
| Pass pool | 125996.4 |
| Rush pool | 64000.0 |
| Rec ≈ pass max gap | 0.0% |
| ARI / BAL / SEA pass | 4350.4 / 3578.6 / 4258.5 |
| League PF / PA | 11859.2 / 11859.2 |
| Wins Σ / min / max / range | 272.0 / 4.3957 / 12.8297 / 8.434 |

All gates **PASS** (pass pool, rush 64k, scheme zones, PF=PA, wins Σ, CIN not bottom-tier, JSN top-tier, offense/defense smoke, QB labels, piles cleared).

## CIN / JSN / pile-cleanup confirmation

| Spot | Value |
|------|------:|
| CIN pass / PF / wins | 5118.9 / 432.89 / 8.8991 |
| Burrow pass yds / TDs | 4812.9 / 39.3 |
| JSN rank / yds / team | 3 / 1428.8 / SEA |
| Chase rank / yds | 1 / 1699.7 |
| Soft piles after cleanup | rush ceil 1 · rush floor 1 · PF floor 2 · win ceil 1 |
| Mike Evans team | TB |

## Soft flags

**None remaining** (material). `soft_flags: []` on confirmation board.

## Statement

This board is the **official 2026 pre-season baseline** for Kos Edge NFL player yard/TD futures and fantasy projections. Guest and Pro surfaces that read `data/ops/nfl-web-launch-bundle.json` should serve bundle `nfl-preseason-sim-2026-20260809T165350Z` with `locked_snapshot: true`.
