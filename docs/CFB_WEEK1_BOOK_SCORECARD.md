# CFB Week 1 Book Scorecard — Phase 1

**Branch:** `cursor/cfb-week1-book-audit-3ca1`  
**Base:** `deploy-vercel` @ `#340`  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Dump:** `ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py`  
**Artifact:** `data/ops/cfb-week1-book-dump-20260831.json`  
**Audit:** `docs/CFB_WEEK1_BOOK_AUDIT.md`

This pass is **measurement**. Tag thresholds, KEI, power, WP, shock, Utah: untouched. Zero PLAY created by this pass.

---

## Five questions

| # | Question | Answer |
|---|---|---|
| 1 | W1 FBS rows with KEI but no trusted Best? | **36 / 43** (`absurd_vs_kei` 35 · `no_market` 1 = `MASS@RUT`) |
| 2 | Best cleared as untrusted — what was Open? | **35** `absurd_vs_kei`. **27** are sign-mismatch clears (same-side gap &lt; 12; Open real). **8** true same-side absurd. See audit table. |
| 3 | Family A: KEI longer or shorter than Open? | **Open longer favorite on 6 / 7** (home-side). Only **FIU@USF** has KEI longer (−19.74 vs −13.5). All Family A **PASS** (Best cleared). |
| 4 | BALL@OSU −42.2 vs Open ~−50? | **Both.** Feed real (−50.5 home). KEI is cupcake-saturation exhibit (do not clamp). Board wipe is mostly home-KEI vs away-Open compare (`raw_gap` 92.7 vs `ss_gap` 8.3). |
| 5 | Any PLAY ≥ 4.0 with trusted Best? | **5 board candidates already tagged PLAY** — listed below; **not amplified**. Family A: **0**. |

### PLAY candidates (gate only — not a card)

| pair | family | edge | caution |
|---|---|---:|---|
| `SMU@FSU` | B | +5.35 | only Family B; needs named driver |
| `WYO@CSU` | other | +6.18 | side review |
| `WKU@NEV` | other | +6.53 | |
| `UNLV@HAW` | other | −4.98 | polarity odd |
| `UCLA@CAL` | other | −14.33 | contaminated by away/home compare |

Operator fire rule still: trusted Best + \|edge\| ≥ 4.0 + named family + one-sentence driver that is **not** “soft slate.”

---

## Ship checks

| Check | Result |
|---|---|
| Dump reproducible from `cfb_dump_edgeboard.py` | **Yes** (live Odds or KEI-only + `no_feed`) |
| Scorecard answers five questions | **Yes** |
| PLAY created by this pass | **0** |
| Production stamp | `v0.15-power-sot` / `as_of=2026-08-31` |
| Operator can see missing vs untrusted vs real edge | **Yes** (dump `trusted_reason` + UI `untrusted` / `no book` under cleared Best) |
| Utah / WP / `apply_cfb_kei` / −42.2 clamp | **Not touched** |
| Trusted-market loosened | **No** |

---

## Phase 1 deliverables

1. `scripts/cfb/cfb_dump_edgeboard.py` — mirrors Edge Board loaders.
2. `data/ops/cfb-week1-book-dump-20260831.json` — dated dump.
3. This scorecard + `docs/CFB_WEEK1_BOOK_AUDIT.md`.
4. Optional UI: cleared Best shows `untrusted` or `no book` in footnote style (was swallowed when Best = —).
5. Test: bundled pack BALL@OSU KEI still **−42.2**.

### Still out of scope

Flip Open to home inside `trustCfbMarket` · retune absurd band · 2019–2025 WP refit · Utah title · PLAY card.
