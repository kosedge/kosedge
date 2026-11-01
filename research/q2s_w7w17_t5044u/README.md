# t5044u — 2017 REG W7–W17 Q2s inputs + Phase 4 IF emit (pre-look)

**RETRO_FIT / DEV_RESEARCH · A1 · CERT=0 · NFL NO-GO · DRAFT**

Cite **12763c08 · adbcf11d · 7cefecef · 1114f24e · 6ca03716 · 84eacd96 · d7e0a6bc**.

NEW bounded package. Does **not** amend [#685](https://github.com/kosedge/kosedge/pull/685) look/guard artifacts. No merge. No fetch/spend. No look. No bootstrap.

## Status

| Gate / phase | Result |
|---|---|
| 1 Identity seal | **PASS** — 165/165 from games `4fe1cdd7` |
| 2 Reconstruct | **PASS** — PBP **84eacd96** owned. Matrix **b56be146** |
| t5049u compare | **PASS** — all 27 fields asserted vs Stage B |
| 3 Alex pre-IF | **ACCEPT** tip **adbcf11d** |
| 4 IF + emit | **DONE** — 141 scored / 24 T2 sealed not scored. Freeze has **row identity** |
| 5 Alex pre-look | **SUPERSEDED for look** — `8b80ad7b` does not bind the final evaluator freeze |
| t5053u evaluator bind | **DONE** — code + protocol frozen; synthetic tests only |
| 6 ONE look | **NOT RUN** — await Alex RO of `evaluator/FINAL_PRELOOK_FREEZE.json` |

## Completeness

| Class | N |
|---:|---:|
| Identity sealed | 165 |
| Complete 27/27 IF+Q2s | **141** |
| Partial T2 sealed, not scored | **24** |
| Examined 70 pooled | **0** |

Matrix: `gate2/RECON_MATRIX_W7W17.csv` sha256 `b56be1462e591ac5e04cfaf860938118e013664a2c661e156afdf5c5f41bc216` — **unchanged**.

## Phase 4 artifacts

| File | sha256 / sha8 |
|---|---|
| `phase4/artifacts/IF_MUS_W7W17.json` | **32e97434…** |
| `phase4/artifacts/q2s_rows_w7w17.json` | **55d8c8bc…** |
| `phase4/artifacts/PROTOCOL_FREEZE.json` | **90774bd4…** (history — not rewritten) |
| `evaluator/FINAL_PRELOOK_FREEZE.json` | **a4652323…** (appends evaluator + parent hashes) |

`research.q2s.margin_mu_q2s = 0.5*IF.margin_mu + 0.5*q2_pm_new`. Fit **70db070d** excludes 2017. Rest BIND_PACKET_ONLY / **155d3ca0**. Never opened **1ee90fac**.

## Reproduce

```bash
git worktree add /tmp/t5044u-if-6ca03716 6ca03716fe52930332d5ffba302c312a651980cc
python3 research/q2s_w7w17_t5044u/phase4/run_phase4.py
python3 -m unittest discover -s research/q2s_w7w17_t5044u/tests -v
```

## Locks

≠look ≠bootstrap ≠re-look 70 ≠reopen 03a4dd90 ≠1ee90fac score ≠merge ≠deploy ≠Stage C ≠CERT lift ≠fetch/spend
