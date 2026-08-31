# CFB KEI vs close — spread-bucket audit (no ratings)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after market-visible merge  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah blocker / −42.2 / band 12 / tag cuts:** do not change.

This is **measurement**. Do not “fix” TCU −20.4 → −8.5. Diagnose the **band**.

---

## Why

Cupcake WP/shock moved huge favorites. Home-sign + aliases made Week 1 books visible.  
**UNC @ TCU did not move.** KEI TCU **−20.4**. Market ~ **−8.5**. Score UNC **15–10**.

| Family         | Pattern                                  | Example              |
| -------------- | ---------------------------------------- | -------------------- |
| A cupcake 21+  | KEI _shorter_ than book after saturation | OSU −42 vs book −50  |
| Mid 3–14 P4/G5 | KEI _longer_ than book                   | TCU −20 vs book −8.5 |

---

## Laws

1. No Week 0 power rebuild.
2. No team special cases.
3. No invented closes.
4. KEI formula untouched.
5. Scorecard is the deliverable, not a new line.

---

## Phase 0 — Discovery (READ ONLY)

Write `docs/CFB_KEI_BUCKET_AUDIT.md`.

### Greps

```bash
rg -n "historical|odds-api|historical_odds|closing_line|close_spread" \
  apps/web/lib services/model-service scripts/cfb | head -200

rg -n "kei_spread_home|week.: 0|week\": 0" \
  apps/web/lib/data/cfb-kei-w0-w1-2026.json | head -40
```

### Close source rule

1. If Odds historical exists and is already used in-repo → use it.
2. Else if `data/ops/` already has a W0 close snapshot → use it.
3. Else create template for operator paste — do not invent / scrape.
4. Do not scrape DK/FanDuel.

---

## Phase 1 — Dump + scorecard

Dump KEI vs open vs close by spread bucket. Answer five scorecard questions. Do not retune.

### Forbidden

`apply_cfb_kei` · power · WP/shock · `if "TCU"` · invented closes · PLAY card
