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
| Model MAE vs market close | model ≤ market on spread and/or total |
| Supervised chronological holdout | Brier ≤ 0.22, margin MAE ≤ 9.5, total MAE ≤ 10.5, schema ≥ v3 + KAV |
| Props stake | must remain `PLAY_STAKE_ELIGIBLE=False` |

## Selective publish (sides/totals)

Code:

- Python: `services/model-service/src/services/nfl_side_total_publish_policy.py`
- Web: `apps/web/lib/nfl-publish-policy.ts` (Edge Board)
- Evaluator: `scripts/nfl/evaluate_enterprise_gates.py`
- Aggregate gates: `services/model-service/src/services/nfl_enterprise_gates.py`

Rules (from `data/ops/nfl-edge-bucket-roi-study.json`):

1. **Default PASS** on the full slate.
2. **Spread PLAY** only if \|edge\| ≥ 2.5 **and** segment ATS evidence clears
   (study: PLAY n=535, hit 56.5%, +ROI).
3. **Spread LEAN disabled** — 1.1–2.5 band settled −14% ROI (n=174).
4. **Total PLAY** only if 2.5 ≤ \|edge\| < 3.0 (narrow band that cleared ATS).
5. **Total ≥ 3.0** → PASS (toxic / size-down research only).
6. If product gate is **RED**, force PASS even for large edges.
7. Props stay research-only until a pre-registered holdout flips
   `PLAY_STAKE_ELIGIBLE`.

## Ops commands

```bash
export DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge

# After grading / retrain artifacts exist:
.venv/bin/python scripts/nfl/evaluate_enterprise_gates.py

# Unit tests
cd services/model-service && PYTHONPATH=. \
  ../.venv/bin/python -m pytest tests/test_nfl_enterprise_gates.py -q
```

Artifacts:

- `data/ops/nfl-enterprise-gates-latest.json`
- `data/ops/nfl-enterprise-gates-latest.md`

## Honesty rules

1. Failed blend/calibration retunes must not be promoted (see KAV sprint).
2. KAV features use week−1 lag only — no same-week leakage.
3. If gates fail, still ship the gate infrastructure and model improvements;
   do **not** market the board as a paid every-game betting card.
4. Prefer DB-owned open/close densify before Odds API gap pulls.
