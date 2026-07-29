# NFL Enterprise Gates

Go/no-go framework for calling NFL sides/totals a **betting product**.
Default board posture is **PASS**. PLAY/LEAN are selective and must clear
edge + historical ATS/CLV evidence.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| **GREEN** | Clears the bar for that check |
| **YELLOW** | Partial / sample thin — ship cautiously, no full-slate claim |
| **RED** | Failed — do not claim betting-product ready on that axis |

Overall **betting-product ready** requires GREEN on ATS, CLV sample, and
supervised holdout; MAE vs market at least YELLOW; props stake-off.

## Product-level floors

| Gate | Floor |
| --- | --- |
| Full-slate ATS hit rate | ≥ 52.38% (−110 breakeven), n ≥ 200 |
| CLV spread +rate | ≥ 55%, **n ≥ 200** (hundreds+) |
| **PLAY-only unused holdout (2025)** | Spread PLAY ATS ≥ 52.38% (n ≥ 60); CLV+ ≥ 55% with **n ≥ 200** for GREEN |
| Model MAE vs market close | model ≤ market on spread and/or total |
| Supervised chronological holdout | Brier ≤ 0.22, margin MAE ≤ 9.5, total MAE ≤ 10.5, schema ≥ v3 + KAV |
| Props stake | must remain `PLAY_STAKE_ELIGIBLE=False` |

**Selective subscription claim** requires PLAY-only holdout GREEN (not full-slate ATS).
Scope claim to **2024+ confirmatory** (2020–22 clears −110 ATS but fails movement-CLV).
Primary-2025 consensus CLV n≥200 is a **hard ceiling** inside v2 PLAY (≤112 PLAY games).
Totals PLAY has no GREEN band yet — research-only.
Exceptional PLAY ATS with flat CLV stays **YELLOW** — do not market ~60% win rate.

## Selective publish (sides/totals)

Code:

- Python: `services/model-service/src/services/nfl_side_total_publish_policy.py`
- Web: `apps/web/lib/nfl-publish-policy.ts` (Edge Board)
- Evaluator: `scripts/nfl/evaluate_enterprise_gates.py`
- Aggregate gates: `services/model-service/src/services/nfl_enterprise_gates.py`

Rules (v2 `spread_play_v2_cap7` — see `nfl-play-only-holdout.json`):

1. **Default PASS** on the full slate.
2. **Spread PLAY** only if **2.5 ≤ \|edge\| < 7.0** and segment ATS+CLV evidence clears
   (confirmatory 2024–25: n=227, ATS 73.1%, movement-CLV+ 61.2% n=206).
3. **Spread \|edge\| ≥ 7.0** → PASS (mega-edge size-down / research).
4. **Spread LEAN disabled** — 1.1–2.5 band settled −14% ROI (n=174).
5. **Totals: sides-only at Week-1 launch** — confirmatory totals CLV RED (~0.35).
   `TOTAL_PLAY_ENABLED=False`. Narrow 2.5–3.0 band retained for research re-enable only.
6. **ML PLAY** only when spread PLAY + vig-aware EV ≥ 2% (`ml_from_spread_play_v1`).
7. If product gate is **RED**, force PASS even for large edges.
8. Props stay research-only until a pre-registered holdout flips
   `PLAY_STAKE_ELIGIBLE`.
9. Product CLV+ uses **movement sample** (open≠close, n_snaps≥2).
10. **Preseason** (`NFL_PRESEASON_MODE=info`): PRE games never receive season PLAY tags.

## Factor freeze (Aug 25, 2026)

**Freeze date: 2026-08-25** — no new factor promotion into the Week-1 product path
without a fresh confirmatory holdout + explicit unfreeze.

| Factor | Default | Status |
| --- | --- | --- |
| KAV v3 | ON | Locked product core |
| H travel×weather | ON | Promoted (ablation) |
| D error-regime | ON | Promoted (uncertainty only) |
| E info velocity | OFF | Killed (ATS −3.5pp) |
| B personnel | OFF | Killed (unmaterializable) |
| A coach aggression | OFF | Killed (regress) |
| Market blend weight | locked | No retune without holdout |
| PLAY band | `spread_play_v2_cap7` | Do not widen |

See `data/ops/nfl-factor-freeze-aug25.md`.

## Ops commands

```bash
export DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge

# Pre-registered PLAY-only unused holdout (2025 KAV boards):
.venv/bin/python scripts/nfl/play_only_holdout.py

# Walk-forward edge-band study (select 2023 → confirm 2024–25 once):
.venv/bin/python scripts/nfl/walkforward_play_band_study.py

# After grading / retrain / PLAY holdout artifacts exist:
.venv/bin/python scripts/nfl/evaluate_enterprise_gates.py

# Unit tests
cd services/model-service && PYTHONPATH=. \
  ../../.venv/bin/python -m pytest tests/test_nfl_enterprise_gates.py -q
```

Artifacts:

- `data/ops/nfl-play-only-holdout.{json,md}`
- `data/ops/nfl-enterprise-gates-latest.json`
- `data/ops/nfl-enterprise-gates-latest.md`
- `data/ops/nfl-path-to-95-report.md`

## Honesty rules

1. Failed blend/calibration retunes must not be promoted (see KAV sprint).
2. KAV features use week−1 lag only — no same-week leakage.
3. If gates fail, still ship the gate infrastructure and model improvements;
   do **not** market the board as a paid every-game betting card.
4. Prefer DB-owned open/close densify before Odds API gap pulls.
