# NFL efficiency backbone v1.1 — ops note (2026-08-08)

Product north star: [`nfl-model-vision.md`](nfl-model-vision.md).

Sprint 2 v1: [`nfl-efficiency-backbone-v1-20260807.md`](nfl-efficiency-backbone-v1-20260807.md).

Overnight progress: [`nfl-overnight-progress.md`](nfl-overnight-progress.md).

## Scope

**Is:** Deepen the same `TeamEfficiencyPackage` → `TeamStrengthState` slot Edge Board / season engine already consume — real ST + true pass/run/early-down EPA drivers.

**Is not:** Season-engine rewrite, survivor/fantasy UI, KEI/Tag contract changes, live injury feeds.

## What changed (v1 → v1.1)

| Area | v1 | v1.1 |
|------|----|------|
| Version tag | `v1` | `v1.1` |
| Special teams | Neutral `st_index=1.0` unless ST EPA present | Real ST from `nfl_dp_team_st_kav_weekly` (`raw_st_epa_per_play`); modest weight `_W_ST=0.065` |
| Pass / run EPA | Reserved fields = overall EPA | True splits from `nfl_dp_play_by_play` (`play_type` pass/run) |
| Early-down EPA | Reserved | Downs 1–2 EPA from PBP when supported |
| Drivers | Implicit | Visible `drivers` dict (sample labels: `ok` / `thin` / `missing` / `neutral_hook`) |
| Thin samples | N/A | Split weights shrink when plays below floors; no invented certainty |

Soft additives remain subordinate to EPA+pressure base. Hierarchy smell tests must hold.

## Materialize (Railway) — Phase A carry-forward

| Table | Rows |
|-------|-----:|
| `nfl_dp_team_situational_weekly` | 2286 |
| `nfl_dp_team_rolling_features_weekly` | 2286 (32 teams × seasons 2023–2026) |
| `nfl_dp_team_rolling_features_latest` | 32 |
| `nfl_dp_team_st_kav_weekly` | 7124 (built on Railway from PBP) |

Path: sync situational from verified local → Railway (was empty after Hobby wipe) → `materialize_team_rolling_features.py --seasons 2023,2024,2025,2026` → `build_st_kav_weekly.py`.

## Before / after (packaged 2026 ← 2025 prior)

Sprint 2 v1 composites (from v1 ops note): SEA **2.150**, ARI **1.865**, NE **2.144**.

| Team | v1.1 o / d (comp) | st_index | Rank | Notes |
|------|-------------------|----------|------|-------|
| SEA | 1.026 / 1.144 (**2.170**) | **1.037** | **2** | Pass EPA +0.11; good ST |
| ARI | 0.946 / 0.898 (**1.844**) | 0.912 | 27 | Flat pass EPA; poor ST |
| NE | 1.068 / 1.094 (**2.162**) | 0.912 | **3** | Top tier intact despite weaker ST |

SEA−ARI composite gap: **~0.326** (wider than v1 ~0.285 — still clearly not a coin flip).

**Top 8 (v1.1):** LA, SEA, NE, HOU, DEN, BUF, JAX, PHI  
**Bottom 5:** CIN, WAS, LV, TEN, NYJ  

**ST extremes:** PIT best (~1.064); NO/SF/TB clamped at floor 0.85 (bad ST visible in drivers without dominating Off/Def).

## Rebuild

```bash
# ST table (local or Railway DATABASE_URL)
python scripts/nfl/build_st_kav_weekly.py

# Packaged cold-start artifact
python scripts/nfl/build_packaged_efficiency_backbone.py --season 2026 --prior-season 2025

# Rolling (after situational present)
python scripts/nfl/materialize_team_rolling_features.py --seasons 2023,2024,2025,2026
```

## Validation

```bash
cd services/model-service && PYTHONPATH=src python3 -m pytest \
  tests/test_nfl_efficiency_backbone.py \
  tests/test_nfl_season_engine_packaged_epa.py -q
```

Expected: SEA ≫ ARI; NE ≤ rank 10; ST moves indices modestly; thin splits labeled; demo bumps demo-only.

## Remaining gaps

1. Rolling path still lacks week-aligned pass/run/early-down EPA (packaged cold-start has true splits; live rolling uses overall 5g EPA + ST join).
2. ST play counts are approximated (~8/game × games) for sample labeling — not exact play counts from PBP join.
3. QB premium hook still 0.0.
4. Defense-allowed RZ still soft / partial vs offense RZ.
5. Optional: refresh 50k/100k launch research on v1.1 indices (not required to ship).

## Bar check

Hierarchy still football-plausible. One strength slot. Model ≠ KEI; Edge/Tag remain KEI vs market only.
