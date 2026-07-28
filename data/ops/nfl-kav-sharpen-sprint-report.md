# NFL KAV Sharpening Sprint Report (2026-07-28)

## Verdict
KAV (owned opponent-adjusted efficiency) is implemented, tested, materialized for 2013–2025, and wired into matchup packs / handicapping / supervised schema v3. DB-first odds grading shows the model beating market MAE with positive CLV on owned open/close pairs. Blend/totals retune does **not** clear the holdout promotion gate — keep `NFL_MARKET_BLEND_*=0.30`.

## Odds grading (before → after using owned inventory)

Inventory on restore warehouse (`kosedge_nfl_restore` from DR dump + restore in progress):
- games 4195 · odds_snapshots 60183 · schedules 3834 · projections 20619 · outcomes 3562 · history 42763

| Metric | Market close | Model |
| --- | ---: | ---: |
| Spread MAE | 9.778 | **9.613** |
| Total MAE | 10.300 | **10.123** |
| ML Brier | 0.224 | **0.200** |
| ATS hit | — | 0.493 |
| CLV spread avg (n=159) | — | **+2.02** (66.0% +) |
| CLV total avg (n=117) | — | **+1.29** (63.3% +) |

Owned Odds API open/close dense mainly 2024–2025 (229 / 235 games); earlier seasons use nflverse closes as fallback. Artifact: `data/ops/nfl-odds-open-close-grading.json`.

## Calibration retune

Walkforward with KAV features (tune 2023–24 n=538, holdout 2025 n=269; all with KAV):

| Config | Tune spread/total MAE | Holdout 2025 spread/total MAE |
| --- | --- | --- |
| Before 0.30/0.30 uncal | 9.585 / 9.852 | **9.499 / 9.881** |
| Best tune 0.30/0.35 + level cal | 9.585 / 9.849 | 9.499 / 9.896 |

**Recommendation:** keep blend **0.30 / 0.30**. Totals calibrator fit is near-identity (level_shift intercept ≈ −0.03). Do not promote 0.35 total weight — holdout total MAE regresses. Artifact: `data/ops/nfl-calibration-retune-20260728.json`.

## KAV

- Spec: `docs/NFL_KAV.md`
- Tables: `nfl_dp_team_kav_game` (6,640 team-games), `nfl_dp_team_kav_weekly` (8,734)
- Seasons: 2013–2025
- Matchup packs updated with week−1 lag: 3,140 rows
- 2024 W18 net leaders (sanity): BAL 1.80, DET 1.62, BUF 1.22, PHI 1.21, GB 1.12
- Handicapping factor `kav_efficiency`; `external_dvoa` placeholder disabled
- Supervised `MODEL_SCHEMA_VERSION = 3`

## Code / PR

- Branch: `nfl-kav-sharpen` @ `d63c6ed1` (+ grading script fix pending)
- Remote: `origin/nfl-kav-sharpen`
- PR: open via https://github.com/kosedge/kosedge/pull/new/nfl-kav-sharpen (gh CLI unauthenticated in this environment)

## Remaining gaps

1. Point live `kosedge` DB at restored warehouse (or rename `kosedge_nfl_restore` → `kosedge`) — main `kosedge` was wiped; work used restore DB.
2. Enterprise prop open/close from Jul 25–28 pull not fully recovered in dump (pre-pull); check DB before any re-pull.
3. Re-train supervised overlay on schema v3 with KAV keys; re-sim boards under KAV factor.
4. Attach/materialize KAV on production after migrate `041`.
5. Props PLAY stake gates left unchanged (still research-only until densified MAE gate).
6. Parallel agents repeatedly switched git branch mid-sprint — keep `nfl-kav-sharpen` pinned when continuing.
