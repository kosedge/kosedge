# Inventory scope

In scope (Ryan requirement 2): season-level roster / depth / starter
assignment in the injury residual builder, replacement-quality
calculation, historical fit, and any precompute that feeds them.

Out of residual-fit feed (documented so IMV can see we looked):

- Production `injury_paths.py` — no `load_rosters` / `STARTER_SLOTS` /
  `_structural_index`. Overlays remain disabled.
- Production `nfl_roster_continuity.py` — human-curated offseason
  multipliers, not the residual-fit `x_continuity`.
- Production `load_packaged_depth_chart` — season pack for the live
  season engine, not a fit input.
- `materialize_depth_chart_weekly` reads season-level `nfl_dp_rosters`
  then stamps a week from usage. Adjacent leakage class; not a feeder
  of `run_injury_residual_fit.py`.

Holdout years 2024 / 2025 / 2026 were not read.
`ops/nfl_injury_audit_t4274u/holdout-once.lock` was not written.
