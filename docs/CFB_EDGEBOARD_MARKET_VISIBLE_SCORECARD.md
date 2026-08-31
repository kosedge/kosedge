# CFB Edge Board market-visible — scorecard

**Branch:** `cursor/cfb-edgeboard-market-visible-3ca1`  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Dump:** `data/ops/cfb-week1-market-visible-20260831.json`  
**Reproduce:** `ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py --json`

Band **12** · PLAY **4.0** · LEAN **2.5** · BALL@OSU KEI **−42.2** · Utah untouched.  
**No fire card.** Display gate only.

---

## Checks

| Check                     | After                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| MASS@RUT Open/Current     | **Joined** — Open **−29.5** · Current **−30.5** · KEI **−27.42** · tag LEAN (edge 3.08) — not `no book` |
| AKR@WAKE Current LINE     | **−24.5 visible** + `untrusted` footnote (`painted_without_trust=true`)                                 |
| AKR@WAKE Edge/Tag         | Edge **null** · Tag **PASS** · fire **NO**                                                              |
| AKR@WAKE KEI              | Still **−11.93** (not moved toward −24.5)                                                               |
| FCS with feed line        | Odds rows still assemble; null-KEI not required to paint books                                          |
| Invented prices           | **0**                                                                                                   |
| KEI BALL@OSU              | **−42.2**                                                                                               |
| Band                      | **12**                                                                                                  |
| `best: ""` in trust apply | **Gone**                                                                                                |
| PLAY created by this pass | **0** (Wake stays PASS; no new card)                                                                    |
| Miami OH ≠ Miami FL       | Tested — keys use `miami-ohio` vs `miami-florida`; same-opponent trap fails closed                      |

---

## What changed

1. `applyCfbTrustedMarketToRows` — keeps feed Best; sets `cfbMarketTrusted` / `cfbTrustLabel` only
2. `EdgeBoard` — Current paints number + `untrusted`/`no book` footnote
3. `cfb-match-keys.ts` — UMass↔Massachusetts (+ Miami OH/FL split)
4. Dump columns: `open_h`, `current_h`, `trusted`, `trust_label`, `painted_without_trust`

## Operator display gate

- Wake: Current **−24.5**, footnote **untrusted**, Edge **—**, **PASS**
- Rutgers: Open/Current around **−29.5/−30.5**, KEI **−27.4**
- Still not a fire card
