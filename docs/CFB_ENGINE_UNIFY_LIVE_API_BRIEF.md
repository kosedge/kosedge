# CFB Engine — Unify live API v0.9 onto frozen SoT publisher

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` @ `cfb-week0-close-2026-08-31` (`bfe5b0b5` / tag `cfb-week0-close-2026-08-31`)  
**Why this pass exists:** Week 0 close unified _artifacts_ to `as_of=2026-08-31`. The live season-engine API is still stamped `cfb-season-engine-v0.9-inseason` and can compose a different universe than the frozen publisher `cfb-season-engine-v0.15-power-sot`. That is two clocks. This pass kills the fork. It does not retune power, WP, shock, Utah, or KEI.

---

## PASTE THIS INTO CURSOR AGENT

```
You are working in kosedge/kosedge on a branch off deploy-vercel.

Follow docs/CFB_ENGINE_UNIFY_LIVE_API_BRIEF.md exactly.
If that path does not exist, copy the operator-pasted brief there, then follow it.

Phase 0 = READ ONLY. Map live API vs frozen publisher. Write the audit.
Phase 1 = point the live API at the frozen SoT publisher. One engine stamp. One as_of.

Do not retune power.
Do not edit the WP curve.
Do not change year-shock / SCORE_NOISE_SD / STRENGTH_NOISE.
Do not touch Utah title %, playoff logistic 2.1, or WIN_PROB_MARGIN_SD.
Do not reopen docs/CFB_ENGINE_BLOCKER.md except to add a "not this pass" line.
Do not invent cfb_v2/.
Do not touch NFL, CBB, or MLB trees.
Do not hand-edit preview prose; regenerate from dump/artifact if copy must move.

Start Phase 0 now. First reply: audit outline + the greps you will run, then run them.
```

Copy this file into the repo as `docs/CFB_ENGINE_UNIFY_LIVE_API_BRIEF.md`.

Suggested branch: `cfb/unify-live-api-onto-power-sot`

---

## 0. Laws (automatic fail)

Inherited from the Week 0 close pass. Still binding.

1. One CFB engine. One `as_of`. After this pass the live API stamp and the frozen artifact stamp are the **same string**.
2. Do not reshuffle top-7 power.
3. Do not train on Week 0. Do not refit power.
4. Do not blend market into research-fair numbers.
5. No team-id branches.
6. No second stack.
7. Do not touch NFL / CBB / MLB. Existing path-based DepthSot skip stays as-is (`NFL_TRUTH=0` only when `CFB_MS=1` and `NFL_MS=0` and no `nfl_ops`).
8. KEI stays a game line. Do not promote E[wins] / natty % into KEI.
9. Blocker stands: Utah `natty_pct` 6.2 is not in scope.
10. Do not stretch WP / playoff scale.
11. Preview sentences are generated from artifacts, not authored.
12. Canary dump after the pass must match the closed Week 0 dump within noise: OSU power 1.6168, USF 1.2601, Utah 1.4841, OSU E[wins] ≈ 9.54, USF ≈ 8.38, Utah ≈ 9.63.

If live API numbers cannot match the frozen dump without retuning WP/shock/power, **write a blocker** and stop.

---

## 1. What “unify” means

Before:

| Surface                                                                                              | Stamp                               | Universe                                                  |
| ---------------------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------- |
| Frozen publisher / web artifacts                                                                     | `cfb-season-engine-v0.15-power-sot` | official slate + power SoT JSON, `as_of=2026-08-31`       |
| Live API (`/cfb/season-engine/*`, `compose_team_projection`, `project_game`, `simulate_full_season`) | `cfb-season-engine-v0.9-inseason`   | densified / packaged universe, different `ENGINE_VERSION` |

After:

- Every CFB compose, project-game, season-sim, KEI attach, and publisher path reads **the same power SoT + official schedule + closed Week 0 results**.
- `ENGINE_VERSION` (or equivalent) on live responses equals the frozen artifact `engine_version`.
- `as_of` / `power_as_of` on live responses equals `2026-08-31` unless a later close has shipped — then both move together.
- Densified synthetic slate is not the default research universe.
- In-season evolution hooks may remain in code but must not be the default for research-fair reads.

This is a routing / default / stamp pass. Not a ratings pass.

---

## 2. Allowed work (this order)

1. Phase 0 audit with real opened paths.
2. Make live loaders default to frozen `power_sot` + official schedule + Week 0 finals.
3. Single engine version string, written in one place, read by API + artifacts + dump.
4. Gate: live `project_game` WP for the Week 0/1 cupcakes matches the published KEI/dump 90s within a stated epsilon.
5. Gate: live canary dump equals frozen dump (power flat; E[wins] within a stated epsilon, default 0.05).
6. Docs: audit, scorecard, gates addendum. Update `docs/CFB_ENGINE_GATES.md` with a “live == frozen” assertion. Do not rewrite the Week 0 scorecard numbers.
7. If a preview field would go stale, regenerate from the dump script — do not hand-type 9.54.

Forbidden: WP mapper edits, shock edits, futures logistic, field-constructor redesign, Utah clamps, preview essays, NFL workflow mute changes.

---

## 3. Phase 0 — Discovery (READ ONLY)

Write `docs/CFB_ENGINE_AUDIT_UNIFY_LIVE_API.md` before any code edit.

### Commands

```bash
rg -n "ENGINE_VERSION|engine_version|v0\.9-inseason|v0\.15-power-sot|official_schedule|densify_schedule|build_packaged_universe|power_sot" \
  services/model-service/src/services/cfb_season_engine \
  services/model-service/src/routes \
  scripts/cfb \
  | head -400

rg -n "simulate_full_season|compose_team_projection|project_game|resolve_season_universe" \
  services/model-service \
  | head -200
```

### Required headings

```markdown
# CFB Engine Audit — unify live API onto frozen SoT

## Two-clock table

| Surface | Path | Version stamp | as_of | Universe (official vs densified) | Power source |

## Live API entrypoints

## Frozen publisher entrypoints

## Where ENGINE_VERSION is set (must become one symbol)

## Default universe today vs required default

## In-season evolution: what it does, whether it is default

## Canary: live project_game vs frozen dump (before)

## Shared NFL/CBB risk

## Phase 1 allowlist

## Blockers already visible
```

Phase 1 may touch only the allowlist + the new docs.

---

## 4. Phase 1 — Implementation

### 4.1 One universe

Live `resolve_season_universe` / equivalent must default to:

- `cfb_power_sot_2026.json` (closed)
- `cfb_official_schedule_2026.json` with Week 0 scores locked
- same FBS universe as the publisher

Densify / sample schedule may stay behind an explicit flag for tests. Default off for research routes.

### 4.2 One stamp

One constant, e.g. `priors.ENGINE_VERSION = "cfb-season-engine-v0.15-power-sot"` (use the real single symbol the audit names).

Live JSON, frozen JSON, dump script, and preview `modelNote` engine string all read it.

Do not leave `v0.9-inseason` as a shipped default. If something still needs that label for a debug route, it is opt-in and not mounted on `/pro/cfb` or Edge Board.

### 4.3 Do not silently re-sim a new truth

If pointing live at frozen SoT would rebuild projections: run the **existing** close/package scripts so artifacts stay the Week 0 close numbers. Do not produce a second 10k board with new E[wins] for OSU/USF/Utah.

Acceptance: dump after unify equals dump from tag `cfb-week0-close-2026-08-31` within epsilon.

### 4.4 Tests

Add or extend `test_cfb_enterprise_gates.py` (or a sibling) with:

- live engine version == frozen artifact engine version
- live `as_of` == frozen `as_of`
- live cupcake WP ≥ 0.90 on the same BALL/FRES/MASS set
- no `v0.9-inseason` on default research responses

Do not skip NFL tests unless the diff is CFB-path-only under the existing workflow rule.

---

## 5. Scorecard

Write `docs/CFB_ENGINE_UNIFY_LIVE_API_SCORECARD.md`.

| Metric                   | Week 0 close (tag)       | After unify           | Allowed              |
| ------------------------ | ------------------------ | --------------------- | -------------------- |
| Frozen engine stamp      | `v0.15-power-sot`        | same                  | same                 |
| Live engine stamp        | `v0.9-inseason`          | **`v0.15-power-sot`** | must match frozen    |
| `as_of` live vs frozen   | disagree / missing       | **both 2026-08-31**   | unique               |
| OSU / USF / Utah power   | 1.6168 / 1.2601 / 1.4841 | same                  | flat                 |
| OSU / USF / Utah E[wins] | 9.54 / 8.38 / 9.63       | same ±0.05            | no new board         |
| Utah natty %             | 6.2 + blocker            | 6.2 + blocker         | untouched            |
| Cupcake WP               | 90s                      | 90s                   | untouched mapper     |
| KEI definition           | game line                | game line             | untouched            |
| Preview modelNote as_of  | 2026-08-31               | 2026-08-31            | only regen from dump |

---

## 6. Done / blocker

### Done

- Audit exists
- Live default universe = frozen SoT + official closed slate
- One engine stamp everywhere research is served
- Canary dump matches the Week 0 tag
- Gates include live == frozen
- Blocker file still present, Utah untouched
- NFL/CBB/MLB untouched
- No WP / shock / power retune

### Blocker (stop, do not unify by retuning)

- Live E[wins] cannot match frozen without changing shock/WP/power
- Official slate cannot feed `simulate_full_season` without a new sim stack
- Research routes still require densify to return numbers
- `v0.9-inseason` remains the default stamp

A blocker is acceptable. A quiet second board is not.

---

## 7. PR shape

Branch: `cfb/unify-live-api-onto-power-sot`  
Title: `CFB: serve live API from frozen power SoT (one stamp)`

PR body must include: allowlist, scorecard, dump before/after, confirmation blocker untouched, confirmation no WP/shock/power hunks.

Operator review is this list only. Not Vegas. Not Utah.
