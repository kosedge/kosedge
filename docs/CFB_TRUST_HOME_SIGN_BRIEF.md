# CFB trusted-market — home-side sign (no ratings)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after the Week 1 book-audit merge  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah blocker:** stays. Not this pass.

This is **not** a KEI pass. KEI stays. −42.2 stays. The 12-pt absurd band stays.  
The bug: `trustCfbMarket` compares home-signed KEI to away-signed Open/Best and wipes real books as `absurd_vs_kei`.

Audit fact (do not rediscover as a theory):

- 35 W1 FBS `absurd_vs_kei` clears
- **27** are sign-mismatch (`sign_bug=Y`); same-side gap `< 12`
- `BALL@OSU`: `kei_h −42.2`, `open_h −50.5`, `raw_gap 92.7`, `ss_gap 8.3`
- Family A Open is a longer favorite on 6/7; board hid all 7

---

## Laws

Inherited from #337 / #338 / #340 / book-audit.

Plus:

1. One convention on the compare: **home-signed**. KEI home-signed is SoT. Flip the book, not KEI.
2. Absurd band **unchanged** (12 pts same-side, or whatever Phase 0 quotes from code — quote it, do not pick a new number).
3. Edge = KEI_home − Best_home after normalize. Same formula the board already uses, on consistent signs.
4. Family A is not a special case. If OSU same-side gap is 8.3, Best must **survive** if the band is 12. Tag is still PASS unless |edge| ≥ 4 **and** operator names a driver.
5. Rows that are truly absurd same-side stay cleared.
6. Do not publish a new PLAY card. Re-dump. Operator gates.

---

## Phase 0 — Discovery (READ ONLY)

Write `docs/CFB_TRUST_HOME_SIGN_AUDIT.md`.

### Greps

```bash
rg -n "trustCfbMarket|absurd_vs_kei|trusted-market|trustedMarket|raw_gap|ss_gap" \
  apps/web services scripts/cfb | head -200
```

### Required headings

```markdown
# CFB trustCfbMarket — home-sign audit

## Function path + signature

## What KEI sign is (home)

## What Open/Best sign is on the row today

## Exact compare (file:line) that produces raw_gap 92.7 on BALL@OSU

## Band constant (quote)

## Call sites (Edge Board, dump script, any API)

## Shared with NFL/CBB? (if yes, CFB-only branch or arg — do not retune other sports)

## Phase 1 allowlist (named files)
```

Stop if you cannot point at the compare with a line number.

---

## Phase 1 — Implementation

1. Normalize book spread to **home** before:
   - absurd / trusted test
   - edge_line
   - tag
2. Prefer a single helper (`toHomeSpread(keiHome, bookSpread, bookSide)` or whatever already exists). No `if team == "Ohio State"`.
3. If Open is stored away-sided in the odds client, do not rewrite the raw odds cache. Convert at the trust/edge boundary so dumps stay auditable (`open_raw`, `open_h`).
4. Re-run `python3 scripts/cfb/cfb_dump_edgeboard.py` (same as book-audit). Write `data/ops/cfb-week1-book-dump-homesign-YYYYMMDD.json`.
5. Update `docs/CFB_TRUST_HOME_SIGN_SCORECARD.md` with before/after on the canaries below.
6. Tests: BALL@OSU KEI still −42.2; after normalize, `ss_gap ≈ 8.3` and Best is **not** cleared if band is 12; UCLA@CAL must not keep a −14.33 PLAY that was a sign artifact.

### Canaries (must appear on the scorecard)

| pair                   | before (audit)               | after (required direction)                                                                                                                                                                                |
| ---------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BALL@OSU`             | raw 92.7, Best cleared, PASS | Best **kept** if ss 8.3 < band; edge = KEI_h − Open_h ≈ **+8.3** (KEI shorter fav than book); tag from thresholds — likely **PLAY on the book side / PASS on fire** — print the tag, do not invent a card |
| `ECU@ALA`              | ss 2.28, cleared             | Best kept; tiny edge; PASS                                                                                                                                                                                |
| `FIU@USF`              | ss 6.24, KEI longer          | Best kept; edge ≈ −6.24                                                                                                                                                                                   |
| `TXST@TEX`             | ss 5.35                      | Best kept                                                                                                                                                                                                 |
| `UCLA@CAL`             | PLAY −14.33                  | Must **drop** if it was a sign artifact; if same-side edge still ≥ 4, print it and leave for operator                                                                                                     |
| `SMU@FSU`              | PLAY +5.35 same-sign already | Should stay in the same ballpark; do not “fix” it toward market                                                                                                                                           |
| `UNLV@HAW` / `WYO@CSU` | polarity-odd PLAY            | Recalc; if they disappear, they were bugs                                                                                                                                                                 |

### Forbidden

- Widen band so OSU 8.3 _and_ a 20-pt miss both survive
- Clamp KEI toward −50.5
- Flip KEI to away
- Loosen trusted-market for missing books
- Touch `apply_cfb_kei`, power, WP, shock, Utah
- Auto-publish PLAY on Family A just because Best now exists

---

## Done

- Compare is home vs home
- 27 sign-mismatch Family-A-class rows no longer wiped
- True same-side absurd still wiped
- Dump + scorecard show before/after on the canary table
- Tag thresholds unchanged
- Zero new product surface
- Operator still gates fire (trusted Best + \|edge\| ≥ 4 + named driver ≠ “soft slate”)

## Blocker

If Open side is not labeled in the odds row and you cannot prove away vs home, **stop** and write `docs/CFB_TRUST_HOME_SIGN_BLOCKER.md`. Do not guess.

## Fire rule after merge (unchanged)

Desk can show Family A books now. That is the point.

Still not a card:

- OSU KEI −42 vs book −50 is **calibration**, not fade-OSU
- SMU@FSU remains the only Family B name previously allowed to be _discussed_
- UCLA/UNLV/WYO wait for the after-dump
