# KosEdge CFB — enterprise program (get the line right)

**Repo:** `kosedge/kosedge`  
**SoT stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Doctrine:** power ≠ E[wins] ≠ natty % ≠ KEI. KEI is the published game line after information. Edge = KEI vs trusted market. PASS default.

This is the plan of record. One chapter per PR. No “fix TCU” ticket. No second engine.

---

## Why we are here (honest)

Desk is enterprise-shaped. The **line is not**.

Shipped (do not reopen):

- One engine / one `as_of` (#337–#338)
- Week 0 slate closed; Week 1 default (#340)
- Trust home-sign; books visible; UMass alias (market-visible)
- Utah title blocker 6.2%
- Cupcake WP into the 90s; USF E[wins] un-cloned from OSU

Still wrong (operator can see in 10 seconds): mid-band KEI too long or wrong side; cupcake/long KEI too short vs a 30-point book; short/pick actually close.

---

## Laws (every chapter)

1. One spine. `v0.15-power-sot` until a chapter *names* a version bump.
2. Discovery audit with file:line before edits.
3. No `if team == …`.
4. No Week 0 power rebuild off 6 games.
5. No invented books.
6. No second CFB stack.
7. No Utah / title-scale beauty pass until CFP chapter.
8. No NFL/CBB/MLB product diffs.
9. Canaries on every ratings-adjacent PR: BALL@OSU · UNC@TCU · HAW@STAN · top-7 power · USF E[wins] vs power rank.
10. Scorecard + blocker-or-done.

---

## Chapter map

### Chapter 0 — Finish the tape (this PR)

- `scripts/cfb/cfb_dump_kei_buckets.py`
- W0+W1 KEI vs close/open by bucket
- Closes: Odds historical preferred; else `data/ops/book/cfb-2026-08-29.json` labeled
- Five scorecard questions
- **No line changes**

### Chapter 1 — Margin → points by bucket (next)

Fit 2019–2025 FBS. Discovery first. Do not shuffle top-7. Do not special-case TCU/Hawaii.

### Chapter 2 — Power units (only if Ch 1 blocker)

### Chapter 3 — Situation layer on KEI

### Chapter 4 — Season tails / CFP (later)

### Chapter 5 — Portal / returning snaps (later)

### Chapter 6 — Operating cadence

Every Saturday: close week, dump buckets, no mid-week refit.

---

## Operator / Cursor contract

- Operator names **one chapter** per chat.
- Cursor ships audit → allowlist → scorecard.
- If Cursor skips discovery or special-cases a team, reject.

**Named now:** Chapter 0 (bucket dump + scorecard). Do not start Chapter 1 edits in this PR.
