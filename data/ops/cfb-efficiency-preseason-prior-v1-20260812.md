# CFB Opponent-Adj Efficiency + Preseason Prior v1

**Date:** 2026-08-12  
**Branch:** `feat/cfb-efficiency-preseason-prior-v1` → `deploy-vercel`  
**Depends on:** warehouse #215 (PBP 2014–2025, games spine, leakage contract)  
**Doctrine:** `available_at` strictly_before_kickoff. Model = research fair. No KEI. No UI rewrite.

Phase A (opponent-adj + garbage-time) then Phase B (preseason prior) in one PR.

Inventory / smell snapshots (committed, small):

- `data/ops/cfb-efficiency-preseason-prior-v1-20260812-inventory.json`
- `data/ops/cfb-efficiency-preseason-prior-v1-20260812-smell.json`

Bulk parquet stays on HD. Packaged 2026 prior JSON is in-image so project-game can *read* it without live-querying HD.

## Smoke (2026-08-12 / 13 build)

| | Count |
| --- | ---: |
| PBP seasons | 2014–2025 (all ok) |
| Team-game rows | **20,591** (FCS plays kept, not deleted) |
| Week snapshots | **25,741** (FBS only; week W uses week `< W`) |
| Season finals | **1,568** (max season **2025**) |
| NaN adj after fix | **0** |
| Week leakage rows (`max_week_included ≥ as_of_week`) | **0** |
| 2026 priors | **147** teams, `as_of=2026-08-12` |

### Smell tests (2026 prior, seasons `< 2026` only)

| Team | Rank | Mean pts | σ | QB class | Notes |
| --- | ---: | ---: | ---: | --- | --- |
| OSU | 1 | +19.07 | 4.27 | incumbent | blue-blood, tight σ |
| UGA | 2 | +16.69 | 4.27 | incumbent* | *classifier; camp battle is human review |
| ND | 3 | +16.10 | 4.28 | incumbent | |
| ALA | 4 | +16.07 | 4.26 | incumbent | |
| TEX | 5 | +15.21 | 4.26 | incumbent | |
| ORE | 8 | +13.86 | **6.17** | portal | portal QB → wider σ |
| FSU | 25 | +10.42 | 4.26 | incumbent | |
| COLO | 46 | +7.66 | 4.26 | incumbent | |
| RICE | 144 | −1.86 | **8.03** | true_freshman | rebuild + new QB |
| MASS | 146 | −2.18 | 4.28 | incumbent | weak program, returning QB |
| BALL | 147 | −3.62 | **7.65** | open_competition | G5 rebuild, widest among full-history G5 |

UGA/OSU-type **>>** rebuild G5 on mean. High-churn / new QB **>** returning-starter powerhouse on σ. 2026 prior does **not** use 2026 game results.

\* UGA QB1 in the 2026-08-12 pack is Ryan Puglisi (1 start / 27 attempts). The engine labels `incumbent`; open camp (Puglisi vs Stockton) remains **human review** — σ is too tight for that battle.

## Phase A — garbage-time + opponent-adj

### Garbage-time defaults (backtestable knobs)

`start.TimeSecsRem` is **seconds remaining in the current half** (0–1800), not game clock. Pass `half` (1/2).

| Knob | Default | Meaning |
| --- | ---: | --- |
| `competitive_margin` | 16 | \|score diff\| below this → weight 1.0 |
| `deep_margin` | 24 | blowout threshold |
| `late_secs` | 720 | 2nd-half 12:00 starts the taper |
| `deep_secs` | 300 | 2nd-half 5:00 deep-garbage floor 0.15 |
| `under_two_margin` / `mult` | 8 / 0.40 | extra cut if under-two and \|diff\|≥8 |
| `min_weight` | 0.10 | never delete plays |
| `first_half_blowout_weight` | 0.85 | 1st-half blowouts still mostly count |

FCS plays are **flagged** (`fcs_opponent`), not dropped. Thin FCS sample → high shrinkage / uncertainty.

Explosive proxy: EPA ≥ 1.0 **or** yards ≥ 15. Stuff rate / RZ EPA when `stuffed_run` / `rz_play` are present.

### Opponent adjustment

- Team-game: weighted EPA/play, success, pass EPA, rush EPA, explosive, stuff, RZ.
- Iterative (4 iters): `adjusted = observed − opponent expected`, then center league mean 0.
- Shrinkage: `n / (n + 80)` plays toward 0. Cold start (week 1 snapshot) = league mean + high uncertainty.
- **Leakage:** entering-week `as_of_week=W` uses only same-season games with `week < W`. `feature_week` = last included week (0 if none) so warehouse fallback `feature_week < game_week` holds.
- Team-game `available_at` = kickoff + 4h when kickoff is known.

A handful of NaN-EPA / missing-`pos_team` plays (7 team-games in v0) used to poison whole seasons via the adj graph. Builder now drops non-finite EPA and empty identities.

### HD outputs

| File | Grain |
| --- | --- |
| `clean/cfb/historical/efficiency/team_game_efficiency.parquet` | offense team-game |
| `clean/cfb/historical/efficiency/team_week_efficiency.parquet` | entering-week Off/Def indices |
| `clean/cfb/historical/efficiency/team_season_efficiency.parquet` | last snapshot per team-season (prior input only) |
| `clean/cfb/historical/efficiency/inventory.json` | counts + knobs |

Season-engine does **not** live-query these at request time.

## Phase B — preseason prior v1

For year Y, **only seasons `< Y`**. Roster pack `as_of=2026-08-12` (pre-Week 0).

### Formula

```
program_net_epa = Σ w_s * (off_epa_adj_s − def_epa_adj_s) / Σ w_s
w_s = era_mult(s) * 0.70^(Y − s − 1)     # 0 if s ≥ Y
era_mult: 2010–17=0.45, 2018–21=0.75, 2022+=1.20   # portal-era overweight
program_points = program_net_epa * 28

roster_points = (roster_strength − 50) * 0.12
qb_points / qb_σ:
  incumbent +1.2 / 3.4
  portal    −0.4 / 5.6
  open      −1.8 / 7.2
  freshman  −2.2 / 7.6
coach: new HC −0.8 mean, +1.4 σ
churn_σ from low returning production + high portal-out

mean = program + roster + qb + coach     # neutral-field pts vs avg FBS
σ    = hypot(program_σ, qb_σ, churn_σ, coach_σ) clipped to [3.2, 9.5]
```

Returning production is **team-level** (ESPN class-year / portal proxies), not unit-level SNAP%. Honesty label: approximate.

### Wiring

- HD: `clean/cfb/historical/priors/team_preseason_prior_2026.parquet`
- Packaged: `services/model-service/src/services/cfb_season_engine/data/cfb_preseason_prior_2026.json`
- `POST /cfb/season-engine/project-game` attaches `research_prior` with `used_in_spread: false`. **Spread / WP / KEI unchanged.**
- `GET /cfb/season-engine/status` exposes `preseason_prior` examples.

Engine version stays `cfb-season-engine-v0.9-inseason`.

## Leakage proof

1. Unit tests: week W features exclude week ≥ W plays; 2026 prior rejects season ≥ 2026; `season_weight(2026, 2026)==0`.
2. HD: 0 / 25,741 week rows with `max_week_included ≥ as_of_week`; `feature_week < as_of_week` for all rows; season-final max year 2025.
3. Prior builder filters `season < prior_year` then `assert_prior_season_boundary`.

## Remaining gaps

- **Open camp QB battles** (UGA Puglisi vs Stockton, others) still human review — classifier can call a 27-attempt QB1 `incumbent` and understate σ.
- **Returning production** is team-level class-year proxy, not measured SNAP% by unit.
- **Portal-out** incomplete; no player-value translation matrix (v2).
- Some packaged codes (IDHO, ACU, CHAT, …) have little/no FBS PBP history → program 0, σ clipped to 9.5.
- Garbage-time thresholds are defaults, not yet walk-forward tuned.
- Project-game still uses packaged 2025 SP+ for the *fair line*; PBP adj / prior are research sidecar.
- Walk-forward vs closes (Week 0–4) is **next**, not this PR.
- No CFB KEI / Edge tags. No PFF. No 50k possession-sim polish.

## Rebuild

```bash
python scripts/cfb/build_efficiency_preseason_prior.py
python scripts/cfb/build_efficiency_preseason_prior.py --skip-prior
python scripts/cfb/build_efficiency_preseason_prior.py --pbp-seasons 2022-2025

cd services/model-service
DATABASE_URL=postgresql://test:test@localhost:5432/test \
  pytest tests/test_cfb_efficiency_preseason_prior.py \
        tests/test_cfb_season_engine.py::test_status_and_project_game_http -q
```

HD must be mounted (`/Volumes/KosEdgeData`). Production model-service does not import the parquet.

## Honesty / non-goals

- No CFB KEI / Edge Board tags
- No matchup interaction matrix
- No wholesale season-engine replacement
- PRESEASON + MODEL labels stay on product

## Next (not this PR)

1. Walk-forward vs lake closes (Week 0–4 emphasis)  
2. Tighten QB-battle σ when the pack is an open camp  
3. KEI only when pure fairs are trustworthy
