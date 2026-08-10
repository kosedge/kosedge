# NFL Phase 3 Path A2 — Re-diagnose player season yards (2026-08-09)

**Depends on:** #166 merged (`bd63dc53…` / tip `526bc2b3…` on `deploy-vercel`)  
**Engine under test:** `nfl-season-engine-v1.25-phase2-features` (Path A blend reverted)  
**Scorecard protocol:** `nfl-historical-replay-v1-20260809` (2019–2025, no look-ahead)  
**Prior Path A:** diagnosis retained; 60% path-end yard blend **reverted** (pass 785→848 worse)

## Code path traced (usage → production → season aggregate)

```
build_historical_replay_universe
  depth pack (W1 identity + depth_order only)
  → _role_from_depth_row          # archetype snap/target/rush by depth_order
  → apply_depth_chart_roster_book # committee / murky WR tables may overwrite
  → annotate_usage_roles
  → apply_process_priors          # efficiency / TD regression only — not volume
simulate_full_season (per path)
  → weekly depth volatility       # share drift / role shuffle
  → allocate_game_usage           # script × personnel × Dirichlet on shares
  → produce_box_scores            # yards from usage × efficiency
  → accumulate player season totals
  → audit_season_finite_production
  → compute_universe_season_budgets + enforce_team_season_budgets_on_path
```

Sticky prior-year alpha shares exist in `offensive_production_stack.py` (fantasy board path) — **not** on this hierarchical season-sim path.

## 1. Team pools first

**No.** In the historical-replay / season-sim path, `factors_from_universe` never sets `pass_yards_prior` / `rush_yards_prior`, so `VOLUME_PRIOR_BLEND` (team-level) does not fire. Budgets are structural strength/coach/slate pools + mild league shrink, then league-pool renorm. Team pass/rush MAE stays low-biased (~373 / −92, ~273 / −102). Pools are imperfect, but they are not where prior-year *player* volume is supposed to enter — and player rec bias is **high** while team pass is **low**, so allocation (not pool level alone) invents named receiving volume.

## 2. Allocation — where prior-year player volume enters

**It does not.** `_role_from_depth_row` assigns fixed depth-order archetype shares (e.g. WR1 `target_share=0.22`, RB1 `rush_share=0.52`) with **zero** join to Y−1 targets/carries/attempts. Depth structure tables can rewrite RB/WR shares for committee/murky books. Game usage then applies script/personnel multipliers and Dirichlet noise; production converts attempts → yards; season totals sum games; team budgets rescale named sums into team pools.

Prior-year player volume appears only in the **scorecard baseline** (`0.5 * Y−1 + 0.5 * position_mean`), never as a usage or production input on the model path.

## 3. No-history vs returning

| Cohort | What the path does today |
|--------|---------------------------|
| Returning veterans (matched Y−1 volume) | Same depth-order archetype shares as anyone at that slot; Y−1 role destroyed |
| Rookies / unmatched / zero prior | Depth archetype + efficiency mean-shrink (`ROOKIE_MEAN_SHRINK`); no draft-capital *volume* prior beyond mild efficiency nudge |
| Committee / murky structures | Generic split tables overwrite even sticky real-world hierarchies |

So returning players are treated like blank depth slots. That is the destroy point.

## 4. Scorecard universe

Confirmed dilution from #164:

- **Model** `player_pool.pass_yards`: filters to `pos == "QB"` (n≈472 / 7 seasons).
- **Prior+reg** `baselines…player_pass_yards`: all matched skill players with a prior row (n≈1735) — many near-zero non-QB `pass_yards`.

On QB-matched players, prior pass MAE is ~1200 (worse than hierarchical ~785). Rush/rec comparisons are closer to same-universe. **Metric fix required:** apply the same position filters to prior+reg player scoring so model and baseline share one universe (document in A2 rerun note). This is scorecard hygiene, not the engine lever.

## 5. Why Path A blend failed

Path A blended **final season yards** (all of pass/rush/rec) 60% toward `0.5*Y−1 + 0.5*pos_mean`, then re-enforced still-low team budgets. That is path-end cosmetic shrinkage after hierarchical rebuild. It modestly helped rec (−21 MAE) but **hurt QB pass** (+63): on the honest QB universe the hierarchical model already beat prior (~800 vs ~1200), so pulling pass totals toward prior then rescaling into a low team pool raised pass MAE and flipped bias. Wrong layer (output yards) and wrong cohort (including QBs who did not need prior yard shrink).

## Single primary failure mode

**At usage construction, returning players’ season target/carry (and related) shares are stamped from depth-order archetype / structure tables and then script–Dirichlet noise, with prior-year player volume never applied as a usage input — so production and season aggregates rebuild roles without Y−1 volume shrinkage (while team budgets only conserve the pool, and the published pass 785 vs 228 gap was further inflated by QB-only vs all-skill scorecard dilution).**

## Chosen Path A2 lever (one)

Strong prior-year **usage-share** anchor for returning players with material Y−1 volume: blend depth archetype `target_share` / `rush_share` toward prior-season share of team targets / rush attempts **before** weekly sim (after depth structure, before process priors). No-history players keep depth/position defaults. No path-end yard blend. Scorecard universe aligned as hygiene.
