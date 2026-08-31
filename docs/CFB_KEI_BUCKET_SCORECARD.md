# CFB KEI bucket scorecard — Chapter 0

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Dump:** `data/ops/cfb-kei-bucket-20260831.json` via `scripts/cfb/cfb_dump_kei_buckets.py`  
**Close source:** Odds API historical preferred (`odds_api_historical`); desk book only as fallback.  
**Chapter:** 0 only — no ratings / WP / KEI map edits.

## Five questions

### 1. W0 mid residual mean vs cupcake residual mean — same sign or flipped?

**Flipped (opposite signs).**

| Bucket | n | mean (KEI − close_home) | median |
|--------|---:|------------------------:|-------:|
| mid (7–14) | 1 | **−12.89** | −12.89 |
| cupcake (≥28) | 2 | **+9.85** | +9.85 |

Mid: KEI too long as favorite (more negative than close).  
Cupcake: KEI too short vs book (less negative than close).

`same_sign: false` in dump summary.

### 2. TCU vs Hawaii vs USC — one family or two?

**Two failure families on one curve.**

| Game | Bucket | KEI | Close | Residual | Pattern |
|------|--------|----:|------:|---------:|---------|
| UNC@TCU | mid | −20.39 | −7.5 | **−12.89** | Mid favorite too long |
| HAW@STAN | short | +10.90 | −4.5 | **+15.40** | Wrong side / polarity (KEI Hawaii, close Stanford) |
| SJSU@USC | cupcake | −34.24 | −38.5 | **+4.26** | Cupcake KEI short of book |
| NMSU@FSU | cupcake | −16.06 | −31.5 | **+15.44** | Cupcake KEI short of book |

TCU and Hawaii are not the same bug as USC/FSU. Short/pick can still be tight (below).

### 3. Does W1 Family A (BALL@OSU) show KEI shorter than Current?

**Yes.**

| Game | KEI | Current (live Odds, home) | Residual |
|------|----:|--------------------------:|---------:|
| BALL@OSU | −42.2 | −50.5 | **+8.3** |

Same cupcake-direction pattern as W0 USC/FSU: model not spending enough points into long favorites. (No W1 close yet — Current only.)

### 4. Any W0 mid \|KEI − close\| < 3?

**No game in the mid bucket** meets that (only UNC@TCU, |res|=12.89).

**Short/pick are often close** (operator intuition confirmed):

| Game | Bucket | Residual |
|------|--------|---------:|
| NCSU@UVA | short | −1.30 |
| MEM@UNLV | short | −0.66 |
| FAU@MD | pick | −0.82 |

### 5. Recommend next chapter?

**Chapter 1 Phase 0 only** — discovery audit for 2019–2025 margin → spread / WP **by bucket**.  
Do **not** start margin→KEI edits in the Chapter 0 PR.  
Do **not** special-case TCU or Hawaii. Do **not** shuffle top-7 power.

If an honest bucket fit still leaves TCU near −20 vs −7.5, write a **blocker** — do not stretch one constant.

## Canaries (frozen for later chapters)

| Canary | Value |
|--------|------:|
| BALL@OSU KEI | −42.2 |
| UNC@TCU KEI | ≈ −20.39 |
| HAW@STAN KEI | +10.90 (home) |
| Top-7 power | unchanged this chapter |
| USF E[wins] vs OSU | unchanged this chapter |

`python3 scripts/cfb/cfb_dump_kei_buckets.py --assert-canaries`

## Blocker-or-done

**Chapter 0: DONE.** Tape proves mid vs cupcake residuals are opposite-signed. That is the input Chapter 1 must fit. No line changes in this PR.
