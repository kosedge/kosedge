# Hist diagnostic score t4910u — 70 complete 2017 REG games (DRAFT)

OWNER t4910u ACCEPT · CoS EXEC_FREEZE · **one** frozen Independent Fair consume.

Eng self-label: `CONDITIONAL_DIAG` (`VERDICT_ENG.md`). NFL NO-GO · CERT=0. Not E1. Not publish. Not betting.

## What this is

Diagnostic score of sealed Stage-1b IF inputs for **exactly 70** complete 2017 REG games (W2 14 + W3–W6 56) at IF tip **6ca03716**, market_blend=0, simulations=4000.

It is **not** a fit, not a tune, not CERT, not a market claim, not ATS.

## Packet

| File | Role |
|---|---|
| `EXEC_FREEZE_t4910u_BOUNDED_DIAG_SCORE_70.md` | CoS freeze recreation (Box sha8 expected 5ecdef1c; remount unmatched) |
| `OWNER_ACCEPT_t4910u_BOUNDED_DIAG_SCORE_70.md` | OWNER accept recreation (Box sha8 expected 1102720e; remount unmatched) |
| `ASSUMPTIONS.md` | Frozen formulas **before** first score write (naive W-L, pick'em, 45.3, seed, rest bind) |
| `SAMPLE_MANIFEST_70.json` / `.md` | 70 games + visible exclusions |
| `SCORE_RESULTS.json` / `.md` | per-game forecast vs realized |
| `METRICS_TABLE.json` / `.md` | ACCEPT-named metrics |
| `COMPRESSION_HIST_DIAG.json` / `.md` | forecast-mean SD vs realized SD + coverage |
| `CALL_AUDIT.md` | Odds=0; rest bind; sources |
| `PINS.json` | rehashed pins this exec |
| `VERDICT_ENG.md` | Eng self-label only |
| `score_t4910u.py` | reproducible wrapper (no math change) |
| `SHA256SUMS` | packet digests |

Box-mirror copies of the freeze/accept filenames also sit at `data/ops/EXEC_FREEZE_t4910u_BOUNDED_DIAG_SCORE_70.md` and `data/ops/OWNER_ACCEPT_t4910u_BOUNDED_DIAG_SCORE_70.md`.

## Pins (rehashed this exec)

| pin | sha8 | match |
|---|---|---|
| IF tip | **6ca03716** | yes |
| simulator | **52d9e909** | MATCH |
| framework | **a0051cc4** | MATCH |
| contract | **b41f4b43** | MATCH |
| as-of module | **7dc6afea** / identity **cf514078** | MATCH |
| PBP | **84eacd96** | cited, not opened |
| W2 tip / matrix | **440314e4** / **708513db** | |
| W3–W6 tip / matrix | **f92aaea3** / **cdff0115** | #671 |
| OOS scores | **1ee90fac** | MATCH; scores only |

## Rest

BIND_PACKET_ONLY. Sealed ET DOW `rest_days_*` from hist packets. W8 UTC caller at 6ca03716 not used. Tip not switched to 90bf65ab.

## Sample

- In: 70 complete 27/27 games
- Out (visible): `2017_02_CHI_TB`, `2017_02_MIA_LAC`, `2017_06_DET_NO`, `2017_06_MIA_ATL`, `2017_06_SF_WAS`, `2017_06_NYG_DEN`

## Reproduce

ASSUMPTIONS must already exist (it did before this score).

```bash
git worktree add /tmp/t4910u-if-6ca03716 6ca03716fe52930332d5ffba302c312a651980cc
PYTHONPATH=/tmp/t4910u-if-6ca03716/services/model-service \
  python3 data/ops/nfl-hist-diag-score-70-t4910u/score_t4910u.py
```

## Headline (diagnostic, not edge)

IF SU 0.4714 · MAE margin 10.745 · MAE total 11.963 · Brier 0.2584 · coverage margin/total 0.800 / 0.743. Does not beat labeled baselines. See `VERDICT_ENG.md`.

NFL NO-GO · CERT=0 · 0 Odds credits
