# NCAAM Fair Lab Protocol v1.0

**Status:** `locked` (Phase E Lab Protocol — Contract v1)  
**Lab:** Kos Edge #14 CBB / NCAAM research fair engine  
**Protocol version:** `ncaam-fair-lab-protocol-v1.0`  
**Registered:** 2026-09-04  
**Machine twin:** [`data/ops/lab/ncaam/ncaam-fair-lab-protocol-v1.json`](../../data/ops/lab/ncaam/ncaam-fair-lab-protocol-v1.json)

> **NO SCORECARD RESULTS IN THIS DOCUMENT.** This file freezes Lab fair
> materialize rules before scorecard fill. Amending cut dates, HCA, or
> uncertainty floors requires a **protocol version bump** (v1.1+), not a
> silent edit after peeking ATS/CLV.

---

## 0. Intent

Research-only fair path for `ncaam` under Contract v1. **Not** live Edge Board.

Outputs are evidence artifacts for a later scorecard vs baselines **B1** + **B2**.
They do **not** populate Edge Board assemble, `kei_lines_ncaam.json`, PLAY / LEAN /
Conf%, or props.

---

## 1. Baselines (LOCKED)

| ID     | Definition                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **B1** | Close consensus from Odds **Path A** parquet (`ncaab_historical_odds_open_close.parquet`) — mean `close_spread_home` / `close_total` across books per `event_id` |
| **B2** | Legacy KenPom AdjEM + HCA (`home_court` from `ensemble_weights.json`, default 2.8696) with **PRIOR / UNKNOWN** continuity honesty                                |

KenPom is a **feed only**, never SoT. Methodology evidence for the KenPom+HCA
experiment: `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md` — informs B2; does not
license ensemble fiction or product publish.

---

## 2. Cut-dates (LOCKED tip dates, inclusive)

| Window          | Tips                        | Role                                  |
| --------------- | --------------------------- | ------------------------------------- |
| Universe Path A | **2022-11-01 → 2024-01-28** | Eligible Path A universe              |
| Train-A         | **2022-11-07 → 2023-03-12** | Train (Valid-A folded in)             |
| Test-A          | **2023-11-06 → 2024-01-28** | OOS test                              |
| 2025 pocket     | 2025-11+                    | **OUT** — never Lab fair research set |

Odds Path A only: `apps/web/data/raw/odds/{open,close}` + processed parquet.
**Path B never.**

---

## 3. Schedule SoT D (Lab joins)

Lab game grain:

1. Odds API `event_id`
2. `commence_time` / tip date
3. B7 `team_id` via `apps/web/lib/ncaam/` + `apps/web/src/ncaam_identity.py`

**Fail-closed:** unresolved or omit aliases → event omitted (no fuzzy join).
**No** `odds_team_to_short`.

`espn_game_id` is reserved **null** for a future Schedule SoT A crosswalk
(parallel ESPN track). Full portal continuity model = **DATA GAP**.

---

## 4. Fair fields

| Field              | Rule                                                                                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fair_spread_home` | Primary. `clip(adjem_home − adjem_away + HCA, ±28)` when both AdjEM as-of ≤ tip                                                                                |
| `fair_total`       | Only if AdjOE/AdjDE/AdjT all present as-of ≤ tip. Method stamp: `kenpom_adj_oe_de_tempo_v1` = `(pace/100) * (OE_h+DE_a+OE_a+DE_h)/2`, `pace=(AdjT_h+AdjT_a)/2` |
| `fair_ml_home`     | **Omitted** — no silent spread→ML                                                                                                                              |

### Continuity honesty

| State     | When                                  | Uncertainty floor σ |
| --------- | ------------------------------------- | ------------------- |
| `PRIOR`   | Both sides have KenPom as-of ≤ tip    | **4.0** pts         |
| `UNKNOWN` | Missing/failed as-of ratings          | **6.0** pts         |
| `SETTLED` | **FORBIDDEN** — portal model DATA GAP |

---

## 5. Market Edge honesty filter

When attaching open lines for later Market Edge scoring: exclude days whose
open API `timestamp` drifts **>7 days** from the Path A filename date.
Those days keep B1 close consensus but null open consensus / mark
`open_snapshot_honest=false`.

**No Edge>4 shopping. No peek-tuning after scorecard.**

---

## 6. Artifacts

| Artifact            | Path                                                      |
| ------------------- | --------------------------------------------------------- |
| Fair rows (parquet) | `data/ops/lab/ncaam/ncaam-fair-lab-{cut}-*.parquet`       |
| Manifest            | `data/ops/lab/ncaam/ncaam-fair-lab-{cut}-*.manifest.json` |
| Protocol twin       | `data/ops/lab/ncaam/ncaam-fair-lab-protocol-v1.json`      |

---

## 7. Hard NOT

- Edge Board populate / PLAY / Conf% / props
- Odds densify credit burns
- Invent tips
- KenPom-as-SoT claims
- #12 GO-2
- Scorecard peek-then-retune
- Writing `kei_lines_ncaam.json` / assemble product JSON as “live” progress
