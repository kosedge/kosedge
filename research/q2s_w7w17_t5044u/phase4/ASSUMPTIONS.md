# Phase 4 IF + Q2s emit — assumptions (frozen before first score write)

Cite **12763c08 · adbcf11d · 7cefecef · 1114f24e · 6ca03716 · 84eacd96 · d7e0a6bc**.

CERT=0 · NFL NO-GO · DRAFT · RETRO_FIT / DEV_RESEARCH · A1.

This file existed **before** `IF_MUS_W7W17.json` / `q2s_rows_w7w17.json` were written.

## Authorized consume

- Offline IF caller pattern: `score_t4910u` @ tip/pin **6ca03716** (`6ca03716fe52930332d5ffba302c312a651980cc`).
- New research copy only: `phase4/score_if_w7w17.py`. Sealed `score_t4910u.py` is not edited.
- `market_blend=0`. `simulations=4000`.
- Seed: `201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)`.
- Simulator pin **52d9e909**. Framework pin **a0051cc4**. Both from the 6ca03716 tree only.

## Inputs

- Identities: Gate 1 sealed 165 from games **4fe1cdd7**.
- Recon matrix: `gate2/RECON_MATRIX_W7W17.csv` sha256 **b56be146…** — do not alter.
- Complete 27/27: **141** scored.
- Partial T2: **24** sealed cells, visible, **not scored**.
- Rest: BIND_PACKET_ONLY / **155d3ca0** ET DOW from the packet. Never W8 `rest_days_from_schedule`. Never tip `90bf65ab`.
- W-L / as-of history: score-only **50bda875**. Never open **1ee90fac**.
- PBP **84eacd96** owned only (already consumed at Gate 2). No fetch/spend.

## Q2s emit

- `research.q2s.margin_mu_q2s = 0.5 * IF.margin_mu + 0.5 * q2_pm_new`.
- `w=0.5` predeclared. Not a fit. No extra HFA.
- Sealed OLS `q2_pm_new = a_q2 + b_q2 * rating_diff` from fit **70db070d** (DEV 2013–16, n=960). 2017 is HISTORY_ONLY — never fit.
- As-of **cf514078**. Config **aa2b47b3**. Frozen md **28c582a1**.
- Examined 70 (W2–W6) never pooled into a new fit. Not in the 141.
- Research fields only. New research copy only. Baseline IF mus copied, not overwritten.
- No candidate win/ATS/OU probabilities.

## Freeze then STOP

- Freeze **code / config / source / manifest / IF rows / Q2s rows** with hashes.
- Existence-only freeze is insufficient (P1 / #685).
- Do **not** look, score vs realized, or bootstrap. Await Alex `PASS_RO_PRE_LOOK` bound to this freeze.

## Forbidden

≠look ≠bootstrap ≠1ee90fac open ≠merge ≠deploy ≠Stage C ≠scored-index reuse ≠CERT lift ≠re-look 70 ≠reopen 03a4dd90
