# NFL Kicker Layer into Model + Boxes (Scoped) — 2026-08-11

## Engine version

`nfl-season-engine-v1.27-kicker-layer`

## Doctrine

Kickers matter for totals, close games, and boxes. Scoped first-class FG/XP path — **not** a full ST research project.

**Status: approximate** (coarse short/mid/long bands + near-constant XP). Not a calibrated per-kicker distance market.

## Formula

### FG attempts (per team-game)

```
fg_att = league_fg_att_per_game (~1.85)
         × pace_factor (plays vs 63.5, sens=0.35, clamp 0.85–1.20)
         × script_mult (lead late ↑ / deficit late ↓)
         × weather.attempt_mult (outdoor adverse 0.95; dome 1.0)
```

Script multipliers (base, then ×1.06 if lead+late):

| script_detail   | mult |
|-----------------|------|
| large_lead      | 1.14 |
| small_lead      | 1.06 |
| neutral         | 1.00 |
| small_deficit   | 0.94 |
| large_deficit   | 0.86 |

### Make by band (coarse)

| band  | yards | share | make% |
|-------|-------|-------|-------|
| short | 0–39  | 0.48  | 0.94  |
| mid   | 40–49 | 0.33  | 0.82  |
| long  | 50+   | 0.19  | 0.68  |

Dome: long make ×1.04, long share ×1.08 (renormalized).  
Outdoor adverse: long make ×0.85, long share ×0.80, attempts ×0.95.

`fg_made = Σ att_band × make_band` · `points_from_fg = fg_made × 3`

### XP

```
xp_att  = offensive_tds × (1 − two_pt_rate)   # two_pt_rate ≈ 0.045
xp_made = xp_att × 0.960
points_from_xp = xp_made × 1
```

Offensive TDs = pass_tds + rush_tds (no rec_td double-count).

### Depth

Team K1 from roster when `position=K` present; else anonymous team profile (`league_prior`). No invented named fantasy stars.

### Layer-2 totals

Tiny FG-environment delta on `expected_team_points`: dome +0.35 / outdoor adverse −0.40. Does **not** re-sculpt Path A calibration or tag policy.

## Integration

| Surface | Change |
|---------|--------|
| `scoring_bridge` | Replaces 22% proportional stub with FG+XP from `kicker_layer` |
| `defensive_production_stack.raw_offensive_points` | Same FG+XP path |
| Game Boxes API / UI | `kicking.home/away` FG att/made, XP, kick pts + skill-TD+FG+XP breakdown |
| Fantasy K desk | Still unavailable on preseason skill board — honest label, no fake ADP |

## Before / after (sample game box shape)

Demo `BUF @ KC` Week 1 (n=60, seed=7, 2026-08-11 smoke):

| Side | FG att / made | XP made | Kick pts | Skill TD pts | TD+FG+XP |
|------|---------------|---------|----------|--------------|----------|
| KC (home) | 1.92 / 1.63 | 1.09 | 5.98 | 6.28 | **12.26** |
| BUF (away) | 1.89 / 1.61 | 1.27 | 6.08 | 7.35 | **13.43** |

Scoring-bridge same-path check (1-game yards/TDs): TD-only **35.8** → with FG+XP **43.0** (FG 4.7 + XP 2.5).

| Component | Before | After |
|-----------|--------|-------|
| FG / extras in boxes | invisible / proportional stub | real FG att/made + XP lines |
| Box UI | skill lines only | **Kicking / scoring** panel |
| Bridge status | `approximate_fg_stub` | `approximate_kicker_layer` |

## League FG volume sanity

| Check | Band | Result |
|-------|------|--------|
| Per team-game FG att | 1.20 – 2.60 | League prior 1.85 → **pass** |
| Zero-FG league | fails | Explicit `zero_fg_fail` → **fail** (tested) |
| Every-drive FG | out of band | Attempt clamp + share model prevents |

Season bridge: 32 × 17 × 1.85 ≈ **1,006** league FG attempts — realistic band.

## Honesty

- Thin distance-band data → coarse short/mid/long + label **approximate**
- Fantasy desk: K stays unavailable until production is wired there — do not hallucinate ADP ranks
- Phase 1 integrity / Week 1 schedule / tag policy / sim-depth defaults **unchanged**

## Out of scope (by design)

- Full ST EPA / return TD model
- Punt / coverage unit ratings
- K prop board / DFS
- Path A calibration sculpture
- Tag policy thresholds
- Sim depth default bump, mock CPU, Edge Board layout

## Smoke

```bash
cd services/model-service
python -m pytest tests/test_nfl_kicker_layer.py -q
```

- [ ] Game Boxes UI shows FG att/made + XP for both teams
- [ ] `engine_version` contains `kicker-layer`
- [ ] Scoring bridge FG+XP &gt; TD-only on same yards/TDs
- [ ] Zero-FG league fails sanity
