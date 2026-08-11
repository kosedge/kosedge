# NFL Truth Layer + Invariants — 2026-08-10

Branch: `feat/nfl-truth-layer` → `deploy-vercel`  
Doctrine: earn the numbers that already exist; failed invariants **block publish**.

## Playoff root cause (investigation order)

| Layer | Finding |
|-------|---------|
| **1. Per-sim path selects 7 AFC + 7 NFC?** | **Broken (lowest).** Hierarchical season engine / launch publish never ran conference seeding. |
| 2. Stored aggregates | Wrote `P(wins≥9)` from win histograms (`publish_launch_research_to_web._playoff_prob`). |
| 3. API payload sums | Mirrored stored CSV (no rescale). |
| 4. UI table sums | Displayed stored %; **no UI normalize-to-700%**. |
| 5. Conference map / LA–LAR | Amplifier: engine `LA` vs web `LAR` could drop Rams on joins; not the sum≈13.5 cause. |

**Root cause layer: 1 (stored as proxy at publish).**

## Before / after (locked board `nfl-preseason-sim-2026-20260809T165350Z`)

| Metric | Before | After |
|--------|-------:|------:|
| Σ playoff league | 13.502 | **14.000** |
| Σ AFC playoff | 7.888 | **7.000** |
| Σ NFC playoff | 5.614 | **7.000** |
| Σ SB | 1.000 | 1.000 |
| Σ expected wins | 272.000 | 272.000 |
| Teams | 32 (`LA`) | 32 (**`LAR`**) |
| Playoff method | `P(wins≥9)` | `7seed_mc_from_week_win_rates_wall_chart` (N=20k) |

## Lineage table (active-run surfaces)

| Surface | Kind | `active_run_id` / lineage |
|---------|------|---------------------------|
| Pointer `data/ops/nfl-web-launch-bundle.json` | Model | `active_run_id` = bundle id |
| Standings / Power / Futures / Projections | Model | Bundle loader stamps `lineage` |
| Fantasy season projections | Model | Same preseason bundle |
| Survivor / Game Boxes default | Model / Scenario | Season-engine APIs; align to pointer when serving locked boards |
| Edge Board KEI path | KEI | `/nfl/fair-lines` returns `lineage.kind=KEI` + `active_run_id` |
| KEI Lines / Weekly Slate kickoff | KEI / Market | Shared `games.start_time` via `resolveNflKickoffIso` |
| Team previews (editorial) | Editorial | Date + “editorial snapshot — not active run.” |

Kinds: **Model | KEI | Market | Editorial | Scenario**.

## Invariants (I1–I8)

Script: `scripts/nfl/check_nfl_invariants.py` (exit non-zero on fail).

| ID | Rule | Notes |
|----|------|-------|
| I1 | Σ wins ≈ 272 (±0.51) | Ties **not** modeled — wins only |
| I2 | Σ SB ≈ 1.0 (±0.01) | Softmax proxy still honest-labeled |
| I3 | Σ AFC playoff ≈ 7.0 (±0.05) | 7-seed MC |
| I4 | Σ NFC playoff ≈ 7.0 (±0.05) | 7-seed MC |
| I5 | American MLs valid | Reject `0 < \|price\| < 100` (e.g. −66) |
| I6 | Edge arithmetic sample | `edge = kei − market` |
| I7 | 32 canonical teams | Product Rams = **LAR** |
| I8 | Active-run surfaces share `active_run_id` | Pointer ↔ bundle |

Gate wiring:

- `publish_launch_research_to_web.py` runs the suite before accepting publish (unless `--skip-gate`).
- CI / PR Checks: `python scripts/nfl/check_nfl_invariants.py` + deliberate `--deliberate-break I3` must fail.
- pytest: `services/model-service/tests/test_nfl_truth_layer_invariants.py`

## Edge Board semantics (code-backed)

- PLAY / desk tags = **KEI vs market** (`nfl-publish-policy`); Decision action labels are Model fair vs market (labeled separately).
- Model vs KEI both visible when they diverge (sub-label under KEI).
- Default confidence **0.72** is a **tier constant** → UI shows band only (`Conf MEDIUM`), not fake “72%”.
- Stats ▾ control **disabled** until wired.

## Kickoff smoke

Wall-chart schedule pack: 272 unique games including NE–SEA + KC–LAC, PHI–DAL, BUF–MIA, SF–LAR. Edge / KEI / Slate prefer fair-lines `start_time`.

## Remaining gaps

1. **Super Bowl** on the locked board is now a **path-record strength bracket** on week rates aligned to board wins (`7seed_mc_plus_strength_bracket_sb`) — still not the full hierarchical joint archive, but no longer softmax-only.
2. Playoff probs remain **7-seed MC from (aligned) week win rates**, not exact hierarchical joint paths. Next earn: persist path records or couple hierarchical sim to `seed_conference`.
3. **Polarization** of board E[wins] (soft-pile W/L) is reported in strength-coherence ops notes; not smoothed here.
4. Survivor / Game Boxes live API may still use request-path engine runs — stamp or label archive when ≠ `active_run_id`.
5. Odds as-of is capture-time on fair-lines response; book-level snapshot stamps can be richer.
6. Nav prune / matchup overview / props / Path A3 / mock CPU / sim depth — **out of scope** for this PR.
