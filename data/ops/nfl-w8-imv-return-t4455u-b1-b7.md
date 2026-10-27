# W8 #640 IMV RETURN close — t4455u B1–B7

**Authority:** DECISION_RYAN_t4455u H-1 (`89fdd45f`).  
**RETURN:** IMV sealing-controls vs H-1 condition 1 (sha8 `d831`).  
**ENG PASS `86c6dbce` stands for eng-package only — NOT sealing ACCEPT.**  
**PR:** https://github.com/kosedge/kosedge/pull/640 (**DRAFT**).  
**Base:** `deploy-vercel` `bfc89f57`. NFL NO-GO / Coming Soon ON.

This file maps the shortest path. It is **not** a seal-ack and **not** H-1 live-pull authorization.

## B1–B7

| ID | Item | Status | Code |
| --- | --- | --- | --- |
| B1 | Auth ≠ fail-closed | **Closed** | Hold default-on. Lift only `NFL_W8_H1_AUTH_CITE=89fdd45f` + `NFL_W8_PR_ROTATE_CONFIRM`. Else `refuse_odds_fetch` + hold alert. HOLD=0 alone cannot lift. |
| B2 | Seal producer AC-1/AC-2 | **Closed** | `seal.produce_seal` ≥60m + AC-2 receipt slot. `refuse_seal` still always raises (AC-12). |
| B3 | 3000-credit ledger | **Closed** | `credits.py` hash-chained `credits.jsonl`. Pre-call check. Hard stop ≤3000. Missing headers stop. Tests 2999/3000/3001. `refuse_credit_purchase` only. |
| B4 | F-8 T=90m | **Closed** | `cadence.F8_CUTOFF` + T-90 sample + late-join refuse. PART B books + S=10 + k≥3 unchanged. |
| B5 | Alerts ceiling/hold/fetch-fail | **Closed (path)** | `control_alert` kinds + file sink. Webhook code path present; unwired (no live POST). |
| B6 | Live fetch + provenance | **Closed (no live HTTP)** | `fetch.fetch_odds_with_provenance`: env key only, redacted; raw-body sha256. Transport required. Default = refuse (no Odds network). |
| B7 | AC-8 / AC-10 | **EXPLICIT_CARVE_OUT** | `carveouts.py`. Not silently stubbed. No invented baselines / no performer grader. |

## Hard stops still hard

- No Odds network / no key in logs, tests, or commits.
- `refuse_odds_fetch` is the fail-closed default until cite + rotate-confirm.
- `refuse_seal` always raises.
- No merge / deploy / Coming Soon OFF / `NFL_ODDS_API_CARRIED_BOOKMAKERS` edit.

## Remains for IMV re-grade

- Condition 1: IMV ACCEPT of sealing controls on this successor tip (this RETURN close).
- Condition 2: Platform Reliability rotate / credential verify (no key in agent logs).
- Condition 5: first legitimate sealed capture → independent IMV verify before scheduled collection.
- Live Odds pull still STOP until IMV ACCEPT.
- AC-8 / AC-10 remain carve-outs unless Ryan/IMV later adopt them.
