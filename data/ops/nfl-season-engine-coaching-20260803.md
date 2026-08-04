# NFL Season Engine v1.8 — Coaching / Tendency Layer

**Date:** 2026-08-03  
**Engine version before:** `nfl-season-engine-v1.7-red-zone`  
**Engine version after:** `nfl-season-engine-v1.8-coaching`  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**New module:** `coaching_tendencies.py`  
**Artifact JSON:** `data/ops/nfl-season-engine-coaching-20260803.json`

## Goal

Give teams distinct coaching identities that modestly influence:

- Baseline pass/run balance
- How aggressively they respond to game script (trailing / protecting leads)
- Red-zone pass preference
- Early-down + two-minute (hurry-up) tendencies

Without breaking depth-chart volatility, injury shocks, game-script play-mix,
red-zone scoring, survivor, or the four-layer hierarchy. Prefer modest,
stable effects over dramatic over-fitting.

## How tendencies are represented

```
team_strength → game_script(+coaching) → player_usage → [red_zone(+rz_pass_bias)] → production
```

Each franchise has a `CoachingProfile`:

| Field | Meaning | Clamp |
| --- | --- | --- |
| `pass_rate_bias` | Baseline pass-rate shift vs league | ±0.035 |
| `script_aggression` | Scales score/time script pass deltas | 0.80–1.20 |
| `rz_pass_bias` | Additive RZ pass preference | ±0.040 |
| `early_down_pass_bias` | Additive early-down pass tilt | ±0.025 |
| `two_minute_aggression` | Scales hurry-up when chasing | 0.80–1.20 |
| `label` / `source` | Short identity + `curated_prior` / `league_default` | — |

**Seed policy:** curated priors for distinctive clubs (KC, BUF, SF, PHI, BAL,
NE, CIN, DET, MIA, PIT, CLE, LAC, GB, DAL, MIN, LA, TEN, CHI); league-average
defaults for the remaining franchises. No fitted coach-year regressions.

Usage still reacts only through the existing script → usage matrix — no
opaque coaching usage multipliers.

## Profile examples

| Team | Label | pass_bias | aggression | rz_pass_bias | early_down | 2-min |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| KC | pass_aggressive | +0.028 | 1.12 | +0.030 | +0.018 | 1.12 |
| BUF | pass_aggressive | +0.018 | 1.10 | +0.015 | +0.010 | 1.10 |
| SF | run_scheme | −0.022 | 0.90 | −0.028 | −0.020 | 0.95 |
| PHI | run_protect | −0.025 | 0.92 | −0.022 | −0.018 | 0.95 |
| BAL | run_scheme | −0.030 | 0.88 | −0.030 | −0.022 | 0.92 |
| NE | conservative | −0.010 | 0.85 | −0.010 | −0.012 | 0.88 |
| DET | script_aggressive | +0.008 | 1.14 | +0.005 | +0.005 | 1.15 |
| MIA | pass_pace | +0.030 | 1.06 | +0.018 | +0.020 | 1.05 |

### How scripts / usage differ

Under **neutral** script (forced 21–21, mid clock), KC baseline pass rate sits
~3–5 pts above SF (coaching pass bias + early-down tilt). Layer 3 then
allocates slightly more targets / pass attempts on the KC side via the
existing script→usage matrix — no separate coaching usage table.

Under **large deficit / late**, a high-`script_aggression` club (DET ≈ 1.14)
gets a larger pass-rate lift and hurry-up than a low-aggression club
(NE ≈ 0.85) from the same unscaled script delta.

Under the **same RZ script inputs**, KC’s `rz_pass_bias` (+0.030) yields a
higher RZ pass rate than SF (−0.028), shifting I10 volume toward WR/TE
targets vs RB GL carries.

## Diagnostics (`include_diagnostics`)

Additive fields on game-boxes:

- `coaching_profile.home` / `.away` — full profile dicts
- `tendency_effects.home` / `.away` — applied biases, mean pass/early/hurry/RZ
- `tendency_effects.sample` — per-side explain block for replicate 0
- RZ team diag also echoes `coaching_profile` + `tendency_effects.rz_pass_bias_applied`

`GET /nfl/season-engine/status` → capability `coaching_tendencies` + docs block.

## Tests

`services/model-service/tests/test_nfl_season_engine_coaching.py`

- Opposite `pass_rate_bias` → different neutral pass rates
- High vs low `script_aggression` trailing → larger pass lift
- High vs low `rz_pass_bias` → different RZ pass rates
- Injury / depth / RZ / survivor still function; BUF@KC sanity holds
- All 32 profiles seed-stable + clamped

## Remaining limitations

1. Profiles are curated priors, not year-by-year coach regressions.
2. Coaching overlays strength `pass_rate_bias` — mild double-count possible
   for demo bumps; clamps keep totals modest.
3. Situational coverage stops at early-down + hurry-up (no 3rd/4th-down or
   drive-level play-calling).
4. No UI surface; HTTP diagnostics only when `include_diagnostics=true`.

## Railway smoke (post-deploy)

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" \
  | jq '{engine_version, capabilities, coaching: .coaching_tendencies.examples.KC}'

curl -sS -X POST "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&n_replicates=80&demo=true&include_diagnostics=true" \
  | jq '{engine_version, coaching_profile: .diagnostics.coaching_profile, tendency: .diagnostics.tendency_effects.home}'
```

Expect `engine_version = nfl-season-engine-v1.8-coaching` and non-empty
`coaching_profile` / `tendency_effects` on the game-boxes response.

## Railway smoke (2026-08-04)

Live on `https://model-service-production-e253.up.railway.app` after PR #84 merge:

- `GET /nfl/season-engine/status` → `nfl-season-engine-v1.8-coaching` +
  capability `coaching_tendencies` (KC example `pass_aggressive`, bias +0.028)
- `GET …/game-boxes?…&include_diagnostics=true` →
  `diagnostics.coaching_profile` (KC/BUF) + `tendency_effects.home`
  (`pass_rate_bias_applied`, `script_aggression`, `rz_pass_bias_applied`)
