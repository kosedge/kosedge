# NFL Team Strength Coherence — LAR + wins/SB/production — 2026-08-11

Branch: `feat/nfl-strength-coherence-lar` → `deploy-vercel`  
Also touches model-service publish/finalize path (Railway when re-finalizing).

Locked board: `nfl-preseason-sim-2026-20260809T165350Z`  
Prior join fix: #195 (`4f7ca038`) Power Ratings Off/Def/Record LA↔LAR.

## Root cause (LAR wins vs SB)

Not a missing Rams franchise in the playoff pool. **Two strength paths:**

| Path | Rams id | LAR / LA strength | Used for |
|------|---------|-------------------|----------|
| Hierarchical MC | `LA` in `team_week_win_rates` / win dist | **E[wins] ≈ 11.11** | Truth Layer #171 7-seed playoffs |
| Soft-pile / defense finalize | board `LAR` + production budgets | **E[wins] ≈ 9.69** | Displayed wins, softmax SB, PF/PA, player yards |

Playoffs therefore told an ~11-win story (~84% playoff) while wins + SB softmax told a 9.7-win story on a polarized board → **SB ≈ 0.48%**. Identity LA→LAR (#171 / #195) fixed joins; this PR closes the **strength dual-source** so one board strength drives wins, playoff, SB, and production.

Amplifier: player totals / defense rows still keyed `LA` while outcomes used `LAR`.

## Fix

1. **Rescale** `team_week_win_rates` so each team’s Σ week p matches board `expected_wins` (production / soft-pile path).
2. **Recompute** 7-seed playoffs + **path-record strength bracket** Super Bowl from those aligned rates (SB uses in-path win totals, not fixed E[wins] crush / not softmax-only).
3. **Canonicalize** LA→LAR on week rates, win distributions, defense, and player totals.
4. Wire `finalize_100k_expert_candidate.py` to run the same coherence step after soft-pile writes.
5. Invariant **STRENGTH_ALIGN**: week-rate Σ ≈ board wins (±0.35); no raw `LA` key.

Scripts: `scripts/nfl/apply_nfl_strength_coherence.py`, extensions in `nfl_playoff_from_week_rates.py`.

## Before / after — LAR

| Metric | Before | After |
|--------|-------:|------:|
| Expected wins | 9.6938 | **9.6938** (unchanged — production path) |
| Week-rate Σ wins | 11.1074 (`LA`) | **9.6938** (`LAR`) |
| Playoff % | 84.22% | **83.14%** |
| Division title % | 48.23% | **36.52%** |
| Super Bowl % | **0.48%** | **7.08%** |
| Product team id | split LA/LAR | **LAR** everywhere |

Playoff % stays high because NFC West peers on the **board** win path are weak below SEA (SF/ARI floor); LAR is a frequent wild-card / contender. SB rises because path-hot Rams records can win the bracket instead of softmax crushing every 9.7-win row under ten 12+ win piles.

## Invariant sums (after)

| Check | Value |
|-------|------:|
| Σ expected wins | 272.000 |
| Σ SB | 1.000 |
| Σ AFC playoff | 7.000 |
| Σ NFC playoff | 7.000 |
| Teams (canonical) | 32 (`LAR`, no `LA`) |
| STRENGTH_ALIGN | PASS |

## E[wins] histogram (polarization — report only)

Soft-pile win rewrite; **not** smoothed in this PR:

| Band | Teams |
|------|------:|
| ≤5 | 6 |
| 5–7 | 10 |
| 7–10 | 5 |
| 10–12 | 1 |
| ≥12 | 10 |

Middle of the league is thin; floor + ceiling dominate. No missing-team / double-count bug found as the cause — it is the soft-pile W/L reshape. Power Ratings still track these wins (non-goal: do not redesign Power scale here).

## Other teams flagged after fix

Contradiction scanner (`flag_wins_playoff_sb_contradictions`):

| Team | Wins | Playoff | SB | Reason |
|------|-----:|--------:|---:|--------|
| **DET** | 7.05 | 57.7% | 2.2% | `low_wins_high_playoff` (weak NFC North under CHI’s 12.7 pile) |

No other high-wins/thin-SB flags remain after path-bracket SB.

## Production linkage

- Soft-pile finalize sets team pass/rush budgets, PF/PA, and `expected_wins` together.
- Player yards/TDs for Rams (Stafford ~4540 pass, Nacua ~1353 rec, Kyren ~877 rush) remain on that budget path; team key canonicalized **`LAR`** (no second “LAR lite” production).
- Week rates are **rescaled to those board wins**, so playoff/SB join the same strength story.

Smoke: LAR power columns remain joinable via #195; outcomes/players/defense all `LAR`; Σ SB = 1; 32 teams.

## Tests

`services/model-service/tests/test_nfl_strength_coherence.py` — rescale LA→LAR, alignment, contradiction flags, SB rewrite, histogram.

## Non-goals (held)

- Rebuilding Power Ratings away from wins
- Eye-test win overrides (“make Rams 11”)
- Path A player-yard sculpture
- Tag policy changes
- Clamping polarization
