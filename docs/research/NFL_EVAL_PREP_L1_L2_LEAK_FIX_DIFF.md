# L-1 / L-2 leak-fix diff (prep only)

**Authority:** IMV plan `53e7aba3` (t4175u) · contamination memo `78f5ee7e`  
**Production rewritten:** **No.** Live remat / ingest still contain the leaky contracts.  
**Eval seasons run:** **No.**

Machine twin: `src.services.nfl_eval_prep.leaks.leak_fix_diff()`.

## L-1 same-week join (TEMPORAL)

Rolling features are built with `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` in
`services/model-service/data_platform_nfl/ingest.py`
(`materialize_matchup_features_from_usage`). The week-W row therefore includes
game W. Matchup packs and the 2013–2025 market backtest then join at
`h.week = s.week`.

Live remat (`tasks._load_team_strength_priors`) caps rolling rows at
`as_of_week = matchup_pack.week` (the **game** week), so the same-week row is
eligible.

### Current (leaky)

```sql
LEFT JOIN nfl_dp_team_rolling_features_weekly h
  ON h.season = s.season AND h.week = s.week AND h.team = s.home_team
LEFT JOIN nfl_dp_team_rolling_features_weekly a
  ON a.season = s.season AND a.week = s.week AND a.team = s.away_team
```

Window: `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`

### Rebuild (fixed)

```sql
LEFT JOIN LATERAL (
  SELECT * FROM nfl_dp_team_rolling_features_weekly h
  WHERE h.season = s.season AND h.team = s.home_team AND h.week < s.week
  ORDER BY h.week DESC
  LIMIT 1
) h ON TRUE
LEFT JOIN LATERAL (
  SELECT * FROM nfl_dp_team_rolling_features_weekly a
  WHERE a.season = s.season AND a.team = s.away_team AND a.week < s.week
  ORDER BY a.week DESC
  LIMIT 1
) a ON TRUE
```

Window if a same-week grain is kept: `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING`.
KAV already joins `week - 1` (`data_platform_nfl/kav.py`); rolling EPA does not.

## L-2 uncapped week (TEMPORAL)

`tasks._week_cap_nullable_predicate` is:

```sql
(CAST(:week_cap AS int) IS NULL OR week <= CAST(:week_cap AS int))
```

When `as_of_week` is missing (no matchup pack / null week), the remat prior
lookup takes the **latest** week of the season — future weeks relative to the
game.

### Rebuild (fixed)

```sql
week <= CAST(:week_cap AS int)
```

`require_week_cap` refuses `None` and refuses `week_cap >= game_week`.

## L-3 defaulted rest / injury (flag only)

Production fills `rest_days_*` with `7.0` and injury impact with `0.0` when
missing (`tasks.run_nfl_market_simulations`, `_fetch_nfl_supervised_training_rows`,
`NflGameInputs` defaults). Rebuild path **flags** unmarked 7.0 / 0.0. It does
not invent an observed value.

## Sites left unchanged (intentional)

- `services/model-service/data_platform_nfl/ingest.py`
- `services/model-service/src/tasks.py`
- `scripts/nfl/historical_market_backtest.py`
- `scripts/nfl/imv/` (absent in this repo; not created)
- Any W4–W6 plumbing bundle or evidence
