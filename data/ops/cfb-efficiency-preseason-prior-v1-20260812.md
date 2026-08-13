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
| UGA | 2 | +16.69 | 4.27† | incumbent† | **open / high uncertainty** — do not trust σ |
| ND | 3 | +16.10 | 4.28 | incumbent | |
| ALA | 4 | +16.07 | 4.26 | incumbent | |
| TEX | 5 | +15.21 | 4.26 | incumbent | |
| MICH | 7 | +14.13 | 4.27† | incumbent† | **open / high uncertainty** — Underwood missing from pack |
| ORE | 8 | +13.86 | **6.17** | portal | portal QB → wider σ (directionally correct) |
| LSU | 10 | +13.23 | 4.26† | incumbent† | **open / high uncertainty** — pack QB1 ≠ public starter |
| FSU | 25 | +10.42 | 4.26† | incumbent† | **open / high uncertainty** — FCS-attempt heuristic vs named starter |
| COLO | 46 | +7.66 | 4.26 | incumbent | |
| RICE | 144 | −1.86 | **8.03** | true_freshman | rebuild + new QB |
| MASS | 146 | −2.18 | 4.28 | incumbent | weak program, returning QB |
| BALL | 147 | −3.62 | **7.65** | open_competition | G5 rebuild, widest among full-history G5 |

UGA/OSU-type **>>** rebuild G5 on mean. High-churn / new QB **>** returning-starter powerhouse on σ **when the classifier is honest**. 2026 prior does **not** use 2026 game results.

σ floor ~4.3 even for “stable” programs is a bit tight for preseason; fine for v1 **if** we widen when QB situation ≠ clean incumbent. † rows below are **not** clean incumbents — treat as open / high uncertainty until a SoT override (news → expert note → pack → prior recomputed).

### Do not trust Week 0 σ — camp QB flags (audit 2026-08-12)

Pack heuristic = ESPN 2026 roster QB1 by 2025 attempts. That is **not** a named starter lock. Same class of bug as the roster-refresh conflict table.

| Team | Pack label | Pack QB1 | Reality / expert note | Prior σ (wrong) | Ops label until override |
| --- | --- | --- | --- | ---: | --- |
| **UGA** | incumbent | Ryan Puglisi (27 att) | Gunner Stockton is the 2026 starter; **absent** from ESPN roster | 4.27 | **open / high uncertainty** |
| **MICH** | incumbent | Brayden Fowler-Nicolosi (82 att, CSU) | Bryce Underwood “clear No. 1”; **absent** from ESPN roster | 4.27 | **open / high uncertainty** |
| **FSU** | incumbent | Dean DeNobile (347 att, Lafayette) | Ashton Daniels named starter 2026-04-21; both on roster, heuristic ranked FCS attempts | 4.26 | **open / high uncertainty** |
| **LSU** | incumbent | Landen Clark (277 att, Elon) | Sam Leavitt is the public QB1; both on roster, heuristic ranked FCS attempts | 4.26 | **open / high uncertainty** |

Do **not** treat 4.3σ as real confidence for these four. Mean ranks can stay as program research; uncertainty must be read as **open competition** (~7σ class) until overrides land. Do not wire this prior into published spreads until (1) camp QB overrides and (2) walk-forward vs closes.

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

- **Camp QB SoT overrides not applied.** UGA / MICH / FSU / LSU are labeled `incumbent` with σ≈4.3; ops treats them as **open / high uncertainty**. Doctrine: news → expert note → pack override → prior recomputed. Until then, do not trust Week 0 σ for those teams.
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
- Prior is **research only** (`used_in_spread: false`); do not publish from it until camp QB overrides + walk-forward

## Next (not this PR)

1. Optional: QB situation honesty patch (UGA / FSU / LSU / MICH SoT overrides) **before** backtest  
2. Walk-forward vs lake closes (Week 0–4 emphasis) — MAE / ATS / CLV stub; still no KEI  
3. KEI only when pure fairs are trustworthy
