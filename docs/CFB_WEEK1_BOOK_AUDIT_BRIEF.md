# CFB Week 1 — KEI vs book audit (no ratings)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after #337 + #338 + #340  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah blocker:** stays. Not this pass.

Production slate is live: `as_of 2026-08-31`, default Week 1, Week 0 tab labeled finals. Desk exists. This pass is the **audit that decides whether anything is allowed to be loud**, not another engine rewrite.

---

## PASTE INTO CURSOR AGENT

```
You are working in kosedge/kosedge on a branch off deploy-vercel.

Follow docs/CFB_WEEK1_BOOK_AUDIT_BRIEF.md exactly.
If that path does not exist, copy the operator-pasted brief there, then follow it.

Phase 0 = READ ONLY. Dump Week 1 Edge Board rows the same way the page loads them: KEI, Open, Current/Best, trusted-market reason, Edge, Tag. Write the audit. Do not edit WP, power, shock, KEI formula, or tag thresholds.

Phase 1 = publish a canary dump script + scorecard + (optional) a small board label for "Best cleared untrusted". Do not retune numbers off this slate.

Do not invent books.
Do not loosen trusted-market so a garbage Open becomes a PLAY.
Do not clamp BALL@OSU −42.2.
Do not touch Utah title %.
Do not invent cfb_v2/.
Do not touch NFL/CBB/MLB.

Start Phase 0 now. First reply: audit outline + greps, then run them.
```

Copy this file to `docs/CFB_WEEK1_BOOK_AUDIT_BRIEF.md`.  
Branch: `cfb/week1-book-audit`

---

## Why this is next

#340 made the board honest. It did not prove the line.

The original memo’s ship gates that are still open:

1. Favorite WP / spread vs book by bucket (Family A cupcakes).
2. Trusted-market is eating Best when the book looks “absurd vs KEI” — operator cannot tell feed-fail from real disagreement.
3. No Week 1 residual sheet. Without it you will either fire blind or keep PASS-ing everything forever.

Do **not** open a 2019–2025 WP refit from this pass. One Saturday (Week 0) plus unplayed Week 1 lines is not a fit sample. This is measurement.

---

## Laws

Same house laws as #337/#338/#340.

Plus:

- Tag thresholds stay **LEAN ≥ 2.5 / PLAY ≥ 4.0 / PASS default**.
- Edge is KEI vs **trusted Best** only.
- Family A is an exhibit, not a special case in code.
- If Best is missing, the row is incomplete — not a fade.

---

## Phase 0 — Discovery

Write `docs/CFB_WEEK1_BOOK_AUDIT.md`.

### Required dump

A table, one row per Week 1 FBS game that has KEI, from the **same loaders the Edge Board uses** (bundled KEI pack + existing odds client + trusted-market). Include:

| Col                      | Source                                                              |
| ------------------------ | ------------------------------------------------------------------- |
| game_id / away@home      | slate                                                               |
| kickoff                  | slate                                                               |
| family                   | A (cupcake) / B (P4–P4 or real G5 test) / other                     |
| kei_spread_home          | bundled pack                                                        |
| kei_total                | bundled pack                                                        |
| open_spread / open_total | odds client                                                         |
| best_spread / best_total | odds client after trusted-market                                    |
| trusted_reason           | why Best kept or cleared (verbatim enum from code)                  |
| edge_line / edge_ou      | computed as the board does                                          |
| tag_line / tag_ou        | board tags                                                          |
| fire                     | NO unless \|edge\| ≥ 4.0 AND trusted Best AND a driver you can name |

Family A must include at least:

- BALL@OSU
- TXST@TEX
- ECU@BAMA
- UTEP@OU
- MOST@TAMU
- UNT@IU
- FIU@USF
- BOIS@ORE (real test, label B if you want — Boise is not a cupcake)

Family B / live checks:

- MIA@STAN
- CLEM@LSU
- WIS@ND
- LOU@MISS
- SMU@FSU
- WSU@WASH

FCS with null KEI: list count only. Do not invent KEI.

### Named questions the audit must answer

1. How many W1 FBS rows have KEI but no trusted Best?
2. How many have Best cleared as untrusted, and what was the Open?
3. On Family A, is KEI consistently longer or shorter than Open when Open exists?
4. Is BALL@OSU −42.2 vs Open ~−50 a feed problem, a KEI-saturation exhibit, or both?
5. Any row that would already clear PLAY ≥ 4.0 with a trusted Best? If yes, list it. Do not tag it louder than the board already does.

Stop if you cannot dump from the live loaders. Do not type numbers from memory.

---

## Phase 1 — Allowed edits

1. `scripts/cfb/cfb_dump_edgeboard.py` — print the table from the same loaders. Commit the script + a dated dump under `docs/` or `data/ops/` if that is house convention.
2. `docs/CFB_WEEK1_BOOK_SCORECARD.md` — fill the questions above.
3. **Optional, one UI string:** if Best was cleared, Edge Board already shows `—`. If the code has a reason enum and the UI swallows it, surface `untrusted` / `no book` in the existing footnote style. Do not add a new product surface.
4. Tests only if the dump script can be asserted against the bundled pack (BALL@OSU KEI still −42.2).

### Forbidden

- `apply_cfb_kei`
- power SoT
- WP / shock knobs
- tag thresholds
- loosening trusted-market
- inventing Open from KEI
- Utah / futures
- “fix” −42.2

---

## Done

- Audit table exists and is reproducible from `cfb_dump_edgeboard.py`
- Scorecard answers the five questions
- Zero PLAY created by this pass
- Production still `v0.15-power-sot` / `as_of=2026-08-31`
- Operator can see which rows are missing books vs untrusted vs real edge

## Blocker (acceptable)

Odds client returns empty in CI: dump KEI-only + `trusted_reason=no_feed` and stop. Do not scrape.

---

## Operator fire rule after this pass

Still not a card.

A row may be discussed as a candidate only if:

1. trusted Best exists,
2. \|KEI − Best\| ≥ 4.0,
3. Family is named (A vs B),
4. driver is one sentence that is **not** “soft slate.”

Everything else stays PASS until Saturday’s closes exist. Then a _close_ audit is a new brief, not a mid-week refit.
