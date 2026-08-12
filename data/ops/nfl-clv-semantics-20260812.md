# NFL CLV semantics audit — 2026-08-12

Date: 2026-08-12  
Branch: `feat/nfl-clv-semantics`  
Doctrine: If the metric can be misread, fix the metric or the copy — or hide the page. Subscribers read “positive CLV” as beating the close.

## Definition (ops + UI)

CLV is the movement of our recommended side's market from the first captured price (open) to the last captured price (called close) on the same market. Positive means the market moved toward our side after the play was implied — we got a better number than the later line (beat the close).

Shared source: `services/model-service/src/services/nfl_clv_semantics.py` and `apps/web/lib/nfl-clv-semantics.ts`.

## Audit

| Question | Finding |
|----------|---------|
| Sign inverted? | **No.** Moneyline `clv = close_imp − open_imp` on the recommended side. +150 open → +120 close is positive (beat). Totals: over `close − open`, under `open − close`. Do not flip. |
| Population | **+EV vs open only** — not PLAY-only, not graded-only. ML: model win prob > open implied on that side. Total: \|model − open\| ≥ 1.0. **No spread** in this pipeline. |
| Timestamps | **MIN/MAX `captured_at`**, not tag/publish vs a true close. |
| Why ~8.9% / 9–32%? | Zeros (identical first/last scrape) counted as **non-positive** in `positive / n`. August 2026 has almost no REG open→close separation. |

## Before / after

**Before (Tracking hero):** unlabeled “Positive CLV rate” = `count(clv > 0) / n`. Pushes in the denominator look like we rarely beat the close.

Example of the old math on a push-heavy window: 1 beat, 9 pushes, 1 lose → **9.1%** “positive CLV.”

**After:**

- `beat / push / lose` shown with **n**
- **Beat later snapshot** = `beat / (beat + lose)` — pushes excluded
- Same example → **50%** of *moved* lines, with n decided = 2, and the rate is **not** heroed while untrustworthy
- Live 2026 is **PRESEASON / incomplete** until REG closes exist (`trustworthy: false` when calendar preseason, decided n < 20, or ≥50% identical open/close)
- Tracking stays off NFL primary nav and NFL tools chrome
- Overview IA hint: incomplete until 2026 REG closes

## Historical n (ARCHIVE — completed seasons)

From `data/ops/nfl-clv-benchmark-report.json` (2024–2025, real open→close, same +EV-vs-open population):

| Market | n | Beat-close rate | Avg CLV |
|--------|---|-----------------|---------|
| Moneyline | 484 | 53.9% | +0.110 (implied win %) |
| Total | 446 | 51.6% | +1.05 points |

2026 is excluded from that report: games have not been played; only near-simultaneous snapshots exist.

## Tests

- `services/model-service/tests/test_nfl_clv_semantics.py` — fixture close sign (ML +150/+120 beat; identical push; reverse lose; totals over/under)
- `apps/web/__tests__/lib/nfl-clv-semantics.test.ts` — Tracking copy matches math; no unlabeled “Positive CLV rate”

## Smoke

Tracking shows the one-sentence definition, PRESEASON/incomplete on live 2026, beat/push/lose with n, and 2024–2025 ARCHIVE rates with n. No mystery 8.9% hero.
