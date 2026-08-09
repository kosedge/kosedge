# NFL Phase 2 — General Features Ops Note (2026-08-09)

**Engine:** `nfl-season-engine-v1.25-phase2-features`  
**Snapshot:** `nfl-depth-2026-w1-20260809T190000Z`  
**Phase 1 gate:** **PASS** (validators green; SoT exclusivity unchanged)  
**PR target:** `deploy-vercel`  
**Not done (by design):** Phase 3 historical replay; Decision Engine PASS/LEAN/PLAY unlock; baseline freeze

## Conversions shipped

1. **QB rushing profile** (`qb_rushing_profile.py`) — SoT `player_id` tier → scramble/designed shares → pass/rush volume mults + script tilt + rush-TD GL mult. Wired into role `rush_share` and season budgets.
2. **OL protection** (`ol_protection.py`) — `ol_roles` → transparent `protection_index` → YPA mult + offense_index delta + RB bump. Replaces OL→EPA stub and named `RB_OL_PROXY_BUMP`.
3. **Coaching play-mix** — ARI (LaFleur), SEA (new OC), WAS (Quinn) added to curated tendencies; scheme TD / run-rate hardcodes removed.
4. **Returning-QB prior travel** — player_id prior map (Darnold) + continuity travel; generalizes SEA 70/30.
5. **Low-continuity high-tail shrink** — new HC/OC regimes compress pass residuals above league mean.
6. **League pass soft taper** — all-32 tanh band (2900–4400) replaces ARI/BAL/SEA soft floor/ceiling piles.
7. **Personnel continuity** — curated staff + travel wired into volume feature context (not label-only).

## Removed / emptied

- `TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS` → `{}`
- `SCHEME_TD_MULT` → `{}`
- `RB_OL_PROXY_BUMP` → `{}`
- `LOCKED_PASS_SCHEME_TEAMS` → `()`
- Named BAL/ARI/SEA run_rate and rush-TD `gl` branches

## Proof metrics (2026-08-09)

Universe: packaged real 2026 + active depth pack. Small sim: `n_sims=25`, seed `20260809`.

| Metric | Value |
|--------|------:|
| Phase 1 gate | **PASS** |
| League pass pool | **126,000.0** |
| League rush pool | **60,000.0** |
| Σ mean wins | **272.0** |
| QB1 ≥4k count | **7** |
| QB1 ≥4.5k count | **3** |
| Median QB1 pass yards | **3,615.7** |
| QB1 p10 / p90 | 3,123 / 4,450 |

### Before/after focus teams (season pass/rush **budgets** after features + pool)

| Team | Pass budget | Rush budget | Feature notes |
|------|------------:|------------:|---------------|
| **WAS** | 3,105 | 2,275 | dual_threat Daniels; **ol_pi=0.893** (Tunsil/Allegretti) |
| **BAL** | 3,021 | 2,447 | designed_run_heavy Lamar; coaching run_scheme |
| **ARI** | 4,919 | 1,220 | pocket Brissett; low-cont high-tail + league taper (no soft_ceiling_ARI) |
| **SEA** | 3,803 | 2,175 | pocket Darnold; returning_qb_prior (player_id) |
| **PHI** | 3,161 | 2,439 | designed_run_heavy Hurts |

Budget pass band (32): min **3,021** / median **3,874** / max **5,167** (post-pool).

### WAS coherence under SoT

- QB1: Jayden Daniels, `rush_share=0.155` (dual_threat tier from GSIS)
- OL protection applied on strength drivers: `protection_index=0.893`, YPA mult & offense delta documented
- Skill usage still SoT depth roles only; OL does not invent pass/rush pool hardcodes

## Audit disposition

See `data/ops/nfl-phase2-special-case-audit-20260809.md`:

- **Convert:** 11  
- **Remove:** 6  
- **Keep (policy):** 8  

## Retained overrides (expiry)

| Item | Revisit |
|------|---------|
| QB rush tiers by player_id | 2026-10-01 |
| Darnold pass prior by player_id | 2026-10-01 |
| Curated 2026 staff continuity | 2026-10-01 |
| Prior-year alpha volume map | 2026-10-01 |
| League pass soft taper rails | Week-5 recalibration |

## Tests

```bash
cd services/model-service
PYTHONPATH=src python3 -m pytest \
  tests/test_nfl_phase2_general_features.py \
  tests/test_nfl_season_coherence.py \
  tests/test_nfl_data_integrity_gate.py -q
```

## Phase 3 gate

Phase 3 historical replay was blocked pending green deploy of this PR. See **Phase 2 CLOSED** below — deploy + smoke are green; Phase 3 is **unblocked**. Do not freeze Decision Engine ladders in this closeout.

## Phase 2 CLOSED (2026-08-09)

| Field | Value |
|-------|-------|
| **PR** | [#163](https://github.com/kosedge/kosedge/pull/163) squash → `deploy-vercel` |
| **Merge SHA** | `80294aae374643a69ab8d3cbfa92419b900563ca` |
| **Vercel Production** | success (`Production – kosedge` deployment on merge SHA) |
| **Railway** | success (`Railway up` check + live `engine_version=nfl-season-engine-v1.25-phase2-features`) |

### Post-merge smoke

1. **snapshot_id present** — Live game-box `GET …/nfl/season-engine/game-boxes?home_team=ATL&away_team=TB&season=2026&week=1&n_replicates=50` (Railway + BFF www.kosedge.com): `notes.snapshot_id=nfl-depth-2026-w1-20260809T190000Z`, `notes.lineage.engine_version=nfl-season-engine-v1.25-phase2-features` (+ `pack_sha256`).
2. **Σ wins = 272** — Live `POST …/nfl/season-engine/simulate?n_team_sims=25&n_player_sims=25&seed=20260809`: `diagnostics.mean_wins_sum=272.0` (locked conservation path).
3. **QB1 ≥4k band** — Same live sim `top_players`: **7** QBs with `pass_yards_mean ≥ 4000` (3 ≥4.5k); next is Herbert ~3999 — Phase 2 proof neighborhood, not absurd.

### Keep-skim verdict (audit 8 policy Keeps)

All **8** summary Keep rows are real documented policy (SoT hygiene / general rail / conservation / time-limited staff book) — **no silent named-team sculpture leftovers**.

| # | Keep lever | Verdict |
|---|------------|---------|
| 1 | `CANONICAL_SKILL_TEAM` (Mike Evans→TB) | **PASS** — SoT identity hygiene only; not a volume lever |
| 2 | `PRIOR_YEAR_ALPHA_VOLUME` | **PASS** — stats-keyed general prior; revisit 2026-10-01 |
| 3 | League rush soft floor/ceiling + tanh | **PASS** — all-32 general rail |
| 4 | High-volume pass TD floor | **PASS** — general volume↔TD coherence |
| 5 | Soft RB alpha prior band | **PASS** — general prior + rank span |
| 6 | PF/PA/win tapered stretch | **PASS** — general league taper (v1.24) |
| 7 | Usage other-bucket floor 8% | **PASS** — general conservation |
| 8 | `CURATED_STAFF_BY_SEASON[2026]` | **PASS** — explicit time-limited staff book; revisit 2026-10-01 |

Note: audit table also labels `QB_RUSH_TIER_BY_PLAYER_ID` **Keep** (player_id trait; revisit 2026-10-01) — likewise documented policy, not a named-team hack.

### Phase 3

**Unblocked** for historical replay kickoff on this green deploy. Decision Engine polish and Phase 1 gate re-break remain out of scope for this closeout.
