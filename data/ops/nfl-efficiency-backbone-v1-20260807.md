# NFL efficiency backbone v1 — Sprint 2 ops note (2026-08-07)

Product north star: [`nfl-model-vision.md`](nfl-model-vision.md).

Sprint 1 after-action: [`nfl-team-strength-fix-after-action-20260807.md`](nfl-team-strength-fix-after-action-20260807.md).

## Scope (what this is / is not)

**Is:** Upstream replacement of the **team-strength source** with an in-house NFL efficiency package, wired into the **existing** `TeamStrengthState` / Edge Board O/D index slot.

**Is not:** A greenfield rewrite of the season engine, survivor, Edge Board, Model vs KEI, or fantasy desk.

## Architecture

```
nflverse PBP
  → nfl_dp_team_situational_weekly   (unit rates: EPA, success, explosive, RZ, pace…)
  → materialize_matchup_features     (3g/5g rolling → nfl_dp_team_rolling_features_weekly)
  → efficiency_backbone v1           (TeamEfficiencyPackage + opponent center + prior/current blend)
  → package_to_strength_indices      (same O/D contract as Edge Board)
  → TeamStrengthState                (Layer 1 — everything downstream unchanged)
```

Cold-start (empty Railway rolling): packaged
`nfl_team_efficiency_backbone_2026.json` (legacy mirror: `nfl_team_epa_priors_2026.json`).

Demo bumps remain **demo-only** forever (`build_demo_universe`).

## Team efficiency package (definitions)

For each team:

| Field | Definition (v1) |
|-------|------------------|
| Off EPA / play | Play-weighted `epa_per_play_offense` from situational weekly; opponent-centered vs league mean |
| Def EPA allowed / play | Play-weighted `epa_per_play_defense_allowed`; opponent-centered |
| Success rate | Play-weighted success (off / def allowed) |
| Explosive rate | Explosive pass plays / plays (off / def allowed); rush explosive not yet split |
| Negative / failure rate | `1 - success_rate` |
| Pass vs run | Pass rate + EPA proxies (pass/run EPA fields reserved; v1 uses overall EPA) |
| Early / late down | Early-down pass rate + third-down conversion (late-down proxy) |
| Red zone | `red_zone_td_rate` as its own unit (soft additive into indices) |
| Pace | Team offensive plays / game ÷ league ~62 |
| Special teams | `st_index` from ST EPA when `nfl_dp_team_st_kav_weekly` present; else **1.0** neutral hook |
| Variance | `uncertainty_from_games` — wider early (1.35 @ 0 GP), tightens toward ~0.55 by week 16 |
| QB premium | Hook field (0.0 until QB identity layer wires in) |
| as_of / version / source | ISO date, `v1`, `packaged_efficiency_backbone` or `efficiency_backbone` |

### Strength mapping (existing slot)

Base = Sprint 1 contract (`epa_to_strength_indices` = Edge Board EPA + pressure).

Soft additives (shrunk when variance high):

- success vs league (~0.44)
- explosive vs league (~0.085)
- RZ TD rate vs league (~0.55)
- tiny ST bleed via `st_index`

Outputs: `offense_index`, `defense_index`, `pace_factor`, `pass_rate_bias`, plus metadata on `TeamStrengthState`.

### Prior → current blend

`prior_current_blend_weight = clamp(games_played / 8, 0, 1)`. One-game spikes do not rewrite the book.

## Materialization path (Railway empty → fixed)

1. Ensure situational weekly populated (`source=nflverse`).
2. Rematerialize rolling + matchup:

```bash
python scripts/nfl/materialize_team_rolling_features.py --seasons 2023,2024,2025,2026
# or dry-run inventory only:
python scripts/nfl/materialize_team_rolling_features.py --seasons 2025 --dry-run
```

Uses existing `data_platform_nfl.cli --materialize-matchup-features --replace-matchup-features`.

3. Rebuild packaged cold-start:

```bash
python scripts/nfl/build_packaged_efficiency_backbone.py --season 2026 --prior-season 2025
# or:
python scripts/nfl/materialize_team_rolling_features.py --seasons 2025 --rebuild-packaged
```

4. Point `DATABASE_URL` at Railway when loading hot DB (capacity permitting; Hobby still lean).

**Cadence:** Rematerialize after every situational hydrate / weekly PBP ingest. Rebuild packaged backbone at least once per offseason (and after major DP backfills). Version bump (`v1` → `v1.1`) when metric definitions change.

Local inventory (2026-08-07): season 2025 situational **570**, rolling **570**, matchup **285**, 32 teams. Railway was **0** rolling rows at Sprint 1 — run the materialize script against Railway when DB is healthy.

## Before / after hierarchy sample

Sprint 1 AFTER was EPA-only packaged priors. Sprint 2 AFTER = efficiency backbone (EPA base + soft success/explosive/RZ + pace/ST metadata).

| Team | Sprint 1 EPA o/d (comp) | Sprint 2 backbone o/d (comp) | Rank S2 |
|------|-------------------------|------------------------------|---------|
| SEA  | 1.040 / 1.117 (**2.157**) | 1.019 / 1.131 (**2.150**) | **2** |
| ARI  | 0.974 / 0.911 (1.885) | 0.950 / 0.915 (**1.865**) | bottom tier |
| NE   | 1.068 / 1.082 (**2.150**) | 1.050 / 1.094 (**2.144**) | **3** |

SEA−ARI composite gap: ~0.285 (still clearly not a coin flip). NE remains top-tier (not floor).

**Top 8 (S2):** LA, SEA, NE, DEN, HOU, BUF, JAX, PHI  
**Bottom 5:** CIN, WAS, LV, TEN, NYJ  

Smell tests intact: SEA clearly above ARI; NE not artificially crushed; one-game craziness regressed via prior/current blend.

## Files changed

| Path | Role |
|------|------|
| `services/model-service/.../efficiency_backbone.py` | Backbone definitions + mapping |
| `.../types.py` | Additive ST/explosiveness/variance/QB/as_of/version on `TeamStrengthState` |
| `.../team_strength.py` | Init + path-evolution source tags |
| `.../loaders.py` | Packaged backbone load; real-mode wiring |
| `.../tasks.py` | Rolling → backbone strength; packaged fill source tags |
| `.../data/nfl_team_efficiency_backbone_2026.json` | Packaged cold-start artifact |
| `.../data/nfl_team_epa_priors_2026.json` | Legacy compat mirror (refreshed) |
| `scripts/nfl/build_packaged_efficiency_backbone.py` | Rebuild packaged artifacts |
| `scripts/nfl/materialize_team_rolling_features.py` | Rolling materialize + dry-run inventory |
| `tests/test_nfl_efficiency_backbone.py` | Unit + smell tests |
| `tests/test_nfl_season_engine_packaged_epa.py` | Accept packaged_efficiency source |

## Validation

```bash
cd services/model-service && PYTHONPATH=src python3 -m pytest \
  tests/test_nfl_efficiency_backbone.py \
  tests/test_nfl_season_engine_packaged_epa.py -q
```

Expected: all pass (SEA above ARI; NE ≤ rank 10; demo bumps demo-only).

## Remaining gaps

1. **Railway rolling still empty until materialize runs against prod DSN** (script ready; capacity / ops window).
2. **ST module** neutral until `nfl_dp_team_st_kav_weekly` is created + hydrated locally/prod.
3. **Pass vs run EPA / early-down EPA** fields reserved; v1 uses overall EPA + rate proxies.
4. **QB premium** hook only (0.0) — wire when QB identity layer lands.
5. Optional: refresh 50k/100k launch research bundle on backbone indices (not required for v1 ship).

## Bar check

If hierarchy is wrong, the model is wrong. S2 hierarchy matches football EPA reality (LA/SEA/NE/HOU strong; NYJ/TEN/LV weak). No matchup hacks. No demo bumps in real mode.
