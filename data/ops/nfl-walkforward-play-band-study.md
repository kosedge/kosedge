# Walk-forward PLAY edge-band study

Generated: `2026-07-28T22:53:35.766040+00:00`

## Protocol

- Selection: **2023 only** (ATS≥breakeven, n≥60), rank by movement CLV+
- Confirm once: **2024–25**
- Product remains **`spread_play_v2_cap7`** unless a band clears GREEN *and* beats v2 CLV+

## Product decision

- Keep `spread_play_v2_cap7` band `[2.5,7.0)`
- Promote new band: **False**
- Rationale: Only capped band that clears confirmatory GREEN (n_clv≥200, CLV+≥0.55, ATS≥breakeven). Tighter CLV-max bands improve CLV+ but drop below n_clv=200 — research-only.

## 2023 selection (top)

| Band | n | ATS | CLV n | CLV+ |
| --- | ---: | ---: | ---: | ---: |
| [5.0,8.0) | 70 | 0.771 | 62 | 0.629 |
| [4.0,7.0) | 71 | 0.732 | 61 | 0.590 |
| [3.5,100.0) | 148 | 0.743 | 127 | 0.583 |
| [4.0,8.0) | 91 | 0.747 | 79 | 0.582 |
| [3.5,7.0) | 86 | 0.709 | 73 | 0.575 |
| [3.0,7.0) | 96 | 0.698 | 82 | 0.573 |
| [3.5,8.0) | 106 | 0.726 | 91 | 0.571 |
| [2.5,100.0) | 181 | 0.735 | 155 | 0.561 |

## Confirmatory 2024–25

| Band | Product? | n | ATS | CLV n | CLV+ | Gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [2.5,7.0) | yes | 232 | 0.724 | 214 | 0.598 | GREEN |
| [5.0,8.0) | no | 127 | 0.787 | 112 | 0.625 | YELLOW |
| [4.0,7.0) | no | 132 | 0.758 | 120 | 0.633 | YELLOW |
| [3.5,100.0) | no | 326 | 0.804 | 292 | 0.606 | GREEN |
| [4.0,8.0) | no | 172 | 0.756 | 155 | 0.645 | YELLOW |
| [3.5,7.0) | no | 158 | 0.759 | 145 | 0.614 | YELLOW |

## Research registrations (not product)

- **`spread_play_research_50_80`** `[5.0,8.0)` — confirm CLV+ 0.625 ATS 0.787 n_clv=112 gate=YELLOW — Improves confirmatory CLV+ vs v2 but fails n_clv≥200 GREEN volume
- **`spread_play_research_40_70`** `[4.0,7.0)` — confirm CLV+ 0.633 ATS 0.758 n_clv=120 gate=YELLOW — Improves confirmatory CLV+ vs v2 but fails n_clv≥200 GREEN volume
- **`spread_play_research_40_80`** `[4.0,8.0)` — confirm CLV+ 0.645 ATS 0.756 n_clv=155 gate=YELLOW — Improves confirmatory CLV+ vs v2 but fails n_clv≥200 GREEN volume
- **`spread_play_research_35_70`** `[3.5,7.0)` — confirm CLV+ 0.614 ATS 0.759 n_clv=145 gate=YELLOW — Improves confirmatory CLV+ vs v2 but fails n_clv≥200 GREEN volume

Re-run: `DATABASE_URL=... .venv/bin/python scripts/nfl/walkforward_play_band_study.py`

