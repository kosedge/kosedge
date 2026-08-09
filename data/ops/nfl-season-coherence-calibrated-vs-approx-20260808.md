# NFL Season Coherence — Calibrated vs Approximate (Phase 1)

Date: 2026-08-08  
Engine: `nfl-season-engine-v1.16-season-coherence`

## Calibrated (this pass)

| Surface | Status |
|---------|--------|
| Team season pass/rush **budgets** + league pool renorm | Calibrated knobs vs recent NFL pools (~120k / ~56k) |
| Per-team pace + pass-rate identity (strength + coaching) | Calibrated magnitudes; still priors, not coach-year regressions |
| Attempt share of pass plays (sack haircut) | Anchored to recent attempt/pass-play ratios |
| Offense-coupled YPA ladder | Anchored; DB baselines still preferred when present |
| W/L zero-sum (272 wins / path) | Hard contract from game outcomes |
| QB1 distribution guards in tests | Hard contract (fail if 32/32 ≥4000) |
| Fantasy season-total allocator | Same budget math after QB starter lock |

## Approximate (honest labels — do not fake precision)

| Surface | Status |
|---------|--------|
| FG / XP / special-teams points | **Stub** proportional fill in `scoring_bridge.py` |
| Individual defensive player stats (tackles, IDP markets) | Out of scope — not calibrated here |
| Full tackle-by-player / pressure markets | Out of scope |
| Live weekly in-season updater | Design only; not part of this pass |
| Betting CLV loop | Out of scope |
| Fantasy path strengths when Layer-1 book missing | **Synthetic** from raw team pass volume (`synthetic_from_raw_pass_approx`) |
| Published web CSV until republish | Still the old v1.12 research bundle |

## Preseason honesty

Preseason boards remain **prior-heavy**. Volume regression shrinks unstable
prior-year tails but does not erase true team strength. Labels on synthetic
fantasy strengths and scoring-bridge FG fill must stay visible in ops /
diagnostics (`season_coherence.scoring_bridge.status = approximate_fg_stub`).

## Out of scope (listed, not faked)

- Full IDP tackle-by-player market accuracy
- Live weekly in-season updater
- Betting CLV loop
- UI redesign
