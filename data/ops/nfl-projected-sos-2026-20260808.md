# NFL 2026 Projected Schedule Difficulty (Future SOS) — 2026-08-08

North star: [`nfl-model-vision.md`](nfl-model-vision.md).

Builds on merged **#140–#144** (true PR blend, player finite, past SOS,
continuity, QB premium). Past SOS (#142) remains the prior-performance
corrector; this layer is **outlook only**.

Branch: `feat/nfl-projected-sos-2026` → `deploy-vercel`.

PR: https://github.com/kosedge/kosedge/pull/145

## Goal

Ship per-team **2026 projected schedule difficulty** so season expectation
surfaces (expected wins, playoff / survivor path grades) reflect easier vs
harder paths — without moving Week 1 / intrinsic PR.

## HARD RULE

**Intrinsic PR at g=0 is unchanged by this layer.**

| Surface | Moves? |
|---------|--------|
| Intrinsic / full-strength PR | No |
| Prior blend (#140), Past SOS (#142), continuity (#143), QB premium (#144) | No |
| Expected wins / analytic outlook | Yes (via schedule matchups + SOS annotate) |
| Survivor path difficulty grade | Yes |
| Edge Board game-level lines | No (matchup-driven; no season SOS blob) |

## Formula

For each team's 2026 REG slate game:

1. **Opponent package** = opponent **full-strength** offense/defense indices
   (post QB premium / continuity / past-SOS prior on the true-PR stack).
   Prefer full-strength so early-season injury noise does not distort season SOS.
2. **Opponent power** = `0.5 × (full_off + full_def)`.
3. **HFA** on effective power (`HOME_FIELD_POINTS / LEAGUE_TEAM_PPG`):
   - Home → subtract HFA power (easier)
   - Away → add HFA power (harder)
4. **`projected_sos_2026`** = mean effective opponent power across the slate
   (higher = harder).
5. Optional bands when schedule supports:
   - `early_sos` = mean W1–6
   - `late_sos` = mean W12–18

Drivers (inspectable, not a dashboard UI):

- Toughest / easiest opponents (top 3 by effective power)
- Home / away balance (road-heavy flagged)
- Status + thin-opponent label when PR book is sparse

Analytic expected wins (outlook helper):

```
Σ game WP(full-strength self vs full-strength opp, with HFA)
```

Season-sim Monte Carlo already walks the real slate game-by-game; Future SOS
**annotates** that outlook and does **not** rewrite Layer-1 indices.

## Wiring

| Step | Path |
|------|------|
| Pure math | `nfl_season_engine/projected_sos.py` |
| Season sim outlook | `simulate_full_season` → `team_wins[*].projected_sos_2026` + diagnostics |
| Survivor path grades | `score_team_survivor` → `path_difficulty_grade` / `schedule_difficulty` |
| API | `GET /nfl/season-engine/status` capability; `POST …/simulate` summary |
| Engine version | `nfl-season-engine-v1.14-projected-sos` |

## Real vs approximate

**Real**

- 2026 REG schedule (DB or packaged wall-chart)
- Full-strength opponent indices from the live/packaged true-PR book
- HFA from season-engine calibration (`HOME_FIELD_POINTS`)

**Approximate / partial**

- Missing opponent strength → league-average fill, status
  `approximate_thin_opponent_book` / `applied_partial_full_strength`
  (still better than crude opponent W%)
- One-pass mean power (not iterative re-rank / market-implied SOS)

**Stub / deferred**

- In-season SOS updates after upsets (recompute from evolving current PR)
- Bye-clustering product UI
- Opponent-tiers dashboard UI

## Example easy / hard slate effect (expected wins, not PR)

Synthetic equal-PR smell (tests):

| Team | Intrinsic PR | Slate | `projected_sos_2026` | Analytic E[wins] |
|------|--------------|-------|---------------------:|-----------------:|
| SOFT | 1.05 / 1.05 | Home-heavy vs weak | lower (easier) | **higher** |
| HARD | 1.05 / 1.05 | Road-heavy vs elite | higher (harder) | **lower** |

Intrinsic composites identical; only outlook moves. On packaged/demo
universes, SOS attaches to `team_wins` without reshuffling PR rank order.

## Smell tests (automated)

File: `services/model-service/tests/test_nfl_projected_sos_2026.py`

| # | Check | Result |
|---|-------|--------|
| 1 | Soft 2026 slate → higher E[wins] than equal-PR brutal slate | PASS |
| 2 | Intrinsic PR ranking does not reshuffle solely from schedule | PASS |
| 3 | Past SOS polarity on prior still intact | PASS |
| 4 | Continuity + QB premium still visible on strength | PASS |
| 5 | Survivor / path grades rank easier vs harder coherently | PASS |
| 6 | Edge Board game lines not driven by season SOS blob | PASS |

## Explicit non-goals

- Changing Week 1 / intrinsic PR via schedule
- Opponent tiers dashboard UI
- Continuity or QB redesign
- Fantasy draft desk work
- KEI / tag policy changes

## Remaining gaps

1. In-season SOS updates after upsets (refresh opponent book mid-year)
2. Bye clustering product UI
3. Richer venue / travel beyond HFA power scalar
4. Optional playoff-odds surface that consumes SOS-annotated win totals
   (when a playoff model path is wired)

## Progress line

2026 projected SOS ships as an outlook tool: mean full-strength opponent
power + HFA annotates expected wins and survivor path difficulty; intrinsic
PR and Edge Board game matchups stay off the season SOS dial.
