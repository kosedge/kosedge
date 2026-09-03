# CFB spread Tag vs close — unused holdout (2026-09-03)

**Branch:** `cursor/cfb-spread-tag-holdout-6bf5` → `deploy-vercel`  
**Script:** `scripts/cfb/run_spread_tag_close_holdout.py`  
**Artifacts:** `data/ops/cfb-spread-tag-close-holdout-20260903/`  
**Product change:** none (read-only). No KEI recut, no threshold retune, no sit PR.

## Tag rule under test (live web)

From `apps/web/lib/cfb-trusted-market.ts` + published KEI path:

| Piece | Rule |
| --- | --- |
| Trust | absurd \|mkt−KEI\| ≥ **12** untrusted; single-book ≥ **8** (not applied here — see below); outlier vs open ≥ **3.5** N/A |
| Sign | KEI home-signed; SDV close already home (`home_team_spread`) |
| Tag | **PLAY** if \|edge\| ≥ **4.0**; **LEAN** if **2.5** ≤ \|edge\| < **4.0**; else PASS |
| KEI | `apply_bias_guard` on model spread (`cfb-bias-guard-v1-histcal-20260805`) — not raw model |

Python `tag_from_edge` week-varying steady bands (2.5 / 1.5) were **not** used.

## Join that actually ran

| Input | Source on this machine |
| --- | --- |
| Close + scores | SportsDataverse `espn_cfb_betting` + `team_box` + `linescores` (fetched; lake `/Volumes/KosEdgeData` absent; `data/cfb/warehouse` empty) |
| Model | Hist-cal proxy universe (`run_historical_backtest`) — prior-year `cfb_ratings` + league-avg roster/QB |
| KEI | `apply_bias_guard(model, week)` |
| Market for Tag | **Close only** (SDV has no open) |
| Open / owned snaps | **Not available** → CLV unavailable |

**Not usable for this holdout:**

- `data/cfb_grades_2026.jsonl` — has Tag/KEI for W0–W1 but `close` / `open` / `clv` are all null (178 rows).
- Prior-scale / walkforward holdouts — explicitly **No KEI / No Edge tags**.
- Hist-cal `*_games_sample.json` — only 50-row samples; full rows were never committed.

Mapped games graded: **2384** (2023–2025). Skipped: 29 missing line, 1 missing score, 421 unmapped team. Trust: 1811 close consensus, 573 absurd_vs_kei (≥12).

Close treated as **consensus** (`bookCount=2`): only absurd≥12 clears. Strict single-book≥8 was not applied (SDV close is not a lone junk book).

## Definitions

- **ATS vs close:** Tag side vs closing home spread; home covers if `actual_margin + close_spread > 0`; pushes excluded.
- **ROI:** unit stake at **−110** (win +100/110, lose −1).
- **movement-CLV+:** owned open ≠ close favoring Tag side — **unavailable** (close-only series).
- **Edge:** `close_home − kei_home` (positive ⇒ KEI likes home more than close).

## Year-split honesty

| Label | Years | Why |
| --- | --- | --- |
| **Unused** (primary) | **2025** | Hist-cal 2026-08-05 knob decisions used **2023–2024** as primary; 2025 was in the full sample report only |
| **Contaminated** | 2023–2024 | Primary decision set for hist-cal knobs; bias-guard residual source |

Caveat: unused year still applies the same bias-guard coefficients. Reconstruction is hist-cal proxy KEI, **not** live 2026 roster/SP+ published lines. Tag is formed **vs close**, not vs open/best at post — this is band grading of KEI−close, not live Tag-at-open CLV.

## Results — unused (2025)

| Band | n | ATS vs close | ROI (−110) | mean \|edge\| | CLV+ |
| --- | ---: | ---: | ---: | ---: | --- |
| **PLAY (≥4.0)** | **349** | **48.7%** (170–179) | **−7.0%** | 7.53 | unavailable |
| **LEAN (2.5–4.0)** | 87 | 57.5% (50–37) | +9.7% | 3.23 | unavailable |

## Results — contaminated (2023–2024)

| Band | n | ATS vs close | ROI (−110) | mean \|edge\| | CLV+ |
| --- | ---: | ---: | ---: | ---: | --- |
| PLAY | 699 | 51.2% (358–341) | −2.2% | 7.54 | unavailable |
| LEAN | 173 | 59.0% (102–71) | +12.6% | 3.22 | unavailable |

### By season

| Season | Label | PLAY n / ATS / ROI | LEAN n / ATS / ROI |
| --- | --- | --- | --- |
| 2023 | contaminated | 351 / 50.7% / −3.2% | 93 / 65.6% / +25.2% |
| 2024 | contaminated | 348 / 51.7% / −1.3% | 80 / 51.3% / −2.2% |
| 2025 | **unused** | **349 / 48.7% / −7.0%** | 87 / 57.5% / +9.7% |

## Reproduce

```bash
PYTHONPATH=services/model-service \
  python3 scripts/cfb/run_spread_tag_close_holdout.py --seasons 2023,2024,2025 --stamp 20260903
```

## CoS one-liner

**RED → sit PLAY** (unused 2025 PLAY ATS 48.7%, ROI −7% at −110; CLV unavailable; leave LEAN uncapped only if desk accepts thin n=87 and close-formed Tag — do not treat LEAN as a green lock).
