# CFB trustCfbMarket — home-sign scorecard

**Branch:** `cursor/cfb-trust-home-sign-3ca1`  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Dump:** `data/ops/cfb-week1-book-dump-homesign-20260831.json`  
**Reproduce:** `ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py --json`

**Band (quoted, unchanged):** `CFB_ABSURD_VS_KEI_PTS = 12` · `CFB_SINGLE_BOOK_ABSURD_PTS = 8` · LEAN 2.5 / PLAY 4.0  
**KEI:** untouched (BALL@OSU still **−42.2**)  
**Python ledger `spread_home`:** not flipped  
**Odds cache:** still away-signed; convert only at trust boundary via `cfbAwayBookToHome`  
**Card:** none. Operator gates fire.

---

## Headline (after)

| Metric                                         | Before (book-audit) |                After (home-sign) |
| ---------------------------------------------- | ------------------: | -------------------------------: |
| W1 FBS + KEI                                   |                  43 |                               43 |
| Trusted Best                                   |                   7 |                           **33** |
| No trusted Best                                |                  36 |                           **10** |
| `absurd_vs_kei`                                |                  35 |      **9** (true same-side only) |
| Sign-mismatch clears                           |                  27 |                            **0** |
| `no_market`                                    |                   1 |                   1 (`MASS@RUT`) |
| Board PLAY candidates (`\|edge\|≥4` + trusted) |                   5 | **20** (listed — **not** a card) |

---

## Canary table

| pair       | before                       | after                                                                                                                                              |
| ---------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BALL@OSU` | raw 92.7, Best cleared, PASS | Best **kept** (−50.5); ss **8.3**; edge **+8.3**; tag **PLAY** (threshold only — calibration vs longer book, **not** fade-OSU / not operator-fire) |
| `ECU@ALA`  | ss 2.28, cleared             | Best kept (−29); edge **+2.78**; tag **LEAN**                                                                                                      |
| `FIU@USF`  | ss 6.24, KEI longer, cleared | Best kept (−13.5); edge **−6.24**; tag **PLAY** (candidate)                                                                                        |
| `TXST@TEX` | ss 5.35, cleared             | Best kept (−31.5); edge **+6.35**; tag **PLAY** (candidate)                                                                                        |
| `UCLA@CAL` | PLAY −14.33 (sign artifact)  | **`absurd_vs_kei`** ss 14.33 ≥ 12; Best cleared; tag **PASS**                                                                                      |
| `SMU@FSU`  | PLAY +5.35                   | Best kept (+3); edge **+5.35**; tag **PLAY** — same ballpark                                                                                       |
| `UNLV@HAW` | PLAY −4.98 polarity-odd      | Still trusted; edge **−4.98**; tag **PLAY** — honest same-side; operator gate                                                                      |
| `WYO@CSU`  | PLAY +6.18 polarity-odd      | Still trusted; edge **+6.18**; tag **PLAY** — honest same-side; operator gate                                                                      |

Family A also kept: `MOST@TAMU` edge +9.25 · `UTEP@OU` +8.39 · `UNT@IU` +8.38 (all PLAY-threshold candidates; **not** auto-fired).

---

## True same-side absurd (still wiped)

`AKR@WAKE` · `ORST@HOU` · `OHIO@NEB` · `BC@CIN` · `OKST@TLSA` · `ULM@MSST` · `WMU@MICH` · `FAU@UF` · `UCLA@CAL`

---

## What changed (allowlist only)

1. `cfbAwayBookToHome` + home compare in `trustCfbMarket` call path (`cfb-trusted-market.ts`)
2. `EdgeBoard.tsx` second gate uses the same helper (no raw away `lineRow.best`)
3. Dump script mirrors convert; artifact dated homesign
4. Tests: KEI −42.2 · OSU keep · UCLA artifact gone
5. When both Open and Best are posted, board path uses `bookCount=2` so `open===best` does not false-trigger SINGLE_BOOK=8 (dump already had real `n_books`)

## What did not change

Band 12 · KEI · power/WP/shock · Utah · Python `cfb_snapshot` · odds-api away storage · tag thresholds · PLAY card

---

## Operator fire gate (unchanged)

Discuss only if: trusted Best + `\|edge\| ≥ 4` + named family + one-sentence driver ≠ “soft slate.”

OSU +8.3 is **calibration** (KEI shorter fav than a longer book), not fade-OSU. SMU@FSU remains the Family B name previously allowed to be discussed. UCLA gone. UNLV/WYO wait for your gate.
