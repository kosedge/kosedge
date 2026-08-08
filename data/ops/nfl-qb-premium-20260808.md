# NFL Real QB Premium — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Builds on merged **#140** (true PR blend), **#141** (player regression),
**#142** (past SOS), **#143** (continuity travel).

Branch: `feat/nfl-qb-premium` → `deploy-vercel`.

PR: https://github.com/kosedge/kosedge/pull/144

## Goal

Ship a **measured QB premium / penalty** on the team-strength path:

- Elite starter → clear positive offense-index lift
- Below-average / replacement → clear drag
- New / uncertain starter → smaller mean + wider uncertainty (no fake precision)
- Drivers visible and honest

Continuity (#143) remains **prior travel only** (“same QB vs new?”). This layer
answers **how good the projected starter is**.

## Signal used (process over counting)

Preference order from `nfl_dp_qb_situational_splits` (overall bucket):

| Rank | Metric | Role |
|-----:|--------|------|
| 1 | EPA / play | Primary process quality |
| 2 | Success rate | Supporting process |
| 3 | CPOE | Supporting process |
| 4 | Pressure-bucket EPA | Soft tilt when sample ≥ 40 dropbacks |
| 5 | YPA / completion % | **Weak counting fallback** — labeled `approximate` |

Quality is z-scored vs league anchors, then blended:

```
quality_z ≈ 0.55·epa_z + 0.25·success_z + 0.20·cpoe_z  (+ optional pressure)
```

Player-level prior→current blend follows the same `games/8` spirit as true PR
(does not invent a second team curve).

## Mapping to PR delta

```
premium = clamp(
  tanh(quality_z / 1.75) × 0.058 × sample_shrink × identity_weight
        × (0.75 if approximate else 1.0),
  ±0.070
)
```

| Knob | Value | Purpose |
|------|------:|---------|
| `PREMIUM_SCALE` | 0.058 | Typical elite/weak magnitude before caps |
| `PREMIUM_CAP` | ±0.070 | One QB cannot dominate reconstruction |
| Same-QB `identity_weight` | 0.40 | Residual tilt — team EPA already embeds him |
| New-QB `identity_weight` | 0.90 | Fuller identity after continuity shrinks prior |
| Uncertain (rookie / open) | 0.55 | Smaller mean + wider variance |
| `sample_shrink` | dropbacks / 280 (floors) | Thin sample → smaller delta |

Applied to **offense_index only** (defense untouched).

## Interaction with continuity

| Layer | Job |
|-------|-----|
| Continuity | Scales **prior travel** when QB/staff/roster churn |
| QB premium | Adjusts **current projected starter quality** |

Anti-double-count / anti-double-punish:

- **New + good** — low travel shrinks old-QB prior toward league mean; premium
  restores good-starter identity (not erased by continuity alone)
- **New + bad** — low travel + negative premium → harsh but coherent
- **Same + elite** — dampened residual only (avoid Mahomes-in-EPA + full premium)

## Full-strength vs current

| Field | QB assumption |
|-------|----------------|
| `full_strength_*` | Projected healthy starter premium |
| `current` / `offense_index` | Starter if available; else backup quality or approx replacement |
| `injury_delta_offense` | Includes `premium_current − premium_full` when starter unavailable |

Inactive/injury feeds (`nfl_dp_injuries` / `nfl_dp_inactives`) are best-effort;
missing feed → starter treated available (no invented outs). Season-sim injury
paths (`apply_strength_shock`) remain the primary availability overlay.

## Uncertainty

| Tenure | Extra variance boost |
|--------|---------------------:|
| Rookie | +0.14 (+ thin-sample term) |
| First-year | +0.10 |
| New team | +0.07 |
| Open competition | +0.12 |
| Incumbent elite | ~0 (games curve only) |

## Real vs approximate

| Source | Quality |
|--------|---------|
| `nfl_dp_qb_situational_splits` EPA/success/CPOE | **Real** |
| Pressure bucket | **Real** when present; else skipped |
| Depth chart QB1/QB2 | **Real** (packaged depth fallback) |
| Counting YPA/comp | **Approximate** |
| Replacement when backup missing + starter out | **Approximate** |
| Missing splits for starter | **Stub** (`stub_not_applied`, delta 0) |

## Wiring

| Step | Path |
|------|------|
| Pure math + loaders | `nfl_season_engine/qb_premium.py` |
| Live apply | `_load_team_strength_priors` after continuity/blend |
| Payload mutate | `apply_qb_premium_to_payload` |
| Drivers | `drivers.qb_premium` + `stubs.qb_premium=applied\|applied_approximate\|stub_not_applied` |
| Strength state | `initialize_strengths` now passes through `qb_premium` |

## Example teams (synthetic process signals; illustrative deltas)

| Band | Team archetype | Tenure | Approx premium (O-index) | Notes |
|------|----------------|--------|-------------------------:|-------|
| Elite same-QB | KC-type (Mahomes) | incumbent | ~+0.02–0.03 | Dampened residual |
| Average | league-starter | incumbent | ~0 | Near-neutral |
| Weak same-QB | replacement-ish | incumbent | ~−0.015 | Clear drag vs average |
| New + good | veteran upgrade | new_team | ~+0.04–0.06 | Fuller identity weight |
| Thin rookie | flashy small sample | rookie | &lt; +0.025 | Small mean + wide variance |

Exact live numbers depend on DB situational splits + depth charts.

## Smell tests (automated)

File: `services/model-service/tests/test_nfl_qb_premium.py`
(+ true PR / continuity / SOS / player-regression suites)

| # | Check | Result |
|---|-------|--------|
| 1 | Elite QB → clear positive vs average | PASS |
| 2 | Weak QB → clear penalty vs average | PASS |
| 3 | New/thin starter does not invent finished elite | PASS |
| 4 | Hierarchy not chaos-reordered by one QB flip | PASS |
| 5 | Past SOS + games/8 + continuity still healthy | PASS |
| 6 | Full-strength ≠ current when starter out | PASS |
| 7 | Drivers show QB; counting fallback labeled | PASS |
| — | Live loader wires premium onto indices | PASS |

## Remaining gaps

1. **Backup model depth** — QB2 quality is thin; replacement fallback is approximate
2. **Playoff-only / tiny samples** — shrink + variance help, but no separate playoff prior
3. **Pressure-adjusted holes** — pressure bucket skipped when &lt;40 dropbacks
4. **Opponent-adjusted QB EPA** — uses league-centered process z’s; not full opponent-adjusted EPA grid
5. **Open competition detection** — heuristic only; camp battles need better feed
6. **Injury feed coverage** — inactive/out tables not always populated preseason
7. **Packaged offline universe** — still stubbed unless live loader path runs with DB
8. **2026 projected SOS** — shipped separately as outlook-only
   (`nfl-projected-sos-2026-20260808.md`)

## Explicit non-goals (this pass)

- Full OL premium model
- Continuity redesign
- 2026 projected SOS product (deferred → shipped in follow-on)
- Fantasy UI
- KEI / tag policy changes

## Progress line

QB premium ships as a capped, process-first offense-index adjustment on the
true-PR strength path; continuity travel, games/8 blend, Past SOS, and player
finite production remain intact.
