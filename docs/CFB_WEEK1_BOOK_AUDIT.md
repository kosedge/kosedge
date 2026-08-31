# CFB Week 1 Book Audit — Phase 0

**Phase:** 0 (READ ONLY / MEASURE)  
**Branch:** `cursor/cfb-week1-book-audit-3ca1`  
**Base:** `deploy-vercel` @ `#340` (`7e71fc0f`)  
**Engine:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Dump:** `ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py`  
**Artifact:** `data/ops/cfb-week1-book-dump-20260831.json`  
**Utah / power / WP / `apply_cfb_kei`:** untouched. BALL@OSU KEI still **−42.2**.

---

## Audit outline (greps run)

| Area           | Path                                                                            | Finding                                                           |
| -------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Board assemble | `loadAssembledEdgeBoardRows` → odds + KEI merge + `applyCfbTrustedMarketToRows` | same path as `/edge-board/cfb`                                    |
| KEI SoT        | `apps/web/lib/data/cfb-kei-w0-w1-2026.json` via `cfbKeiLinesFromBundledPack`    | home-signed `kei_spread_home`                                     |
| Odds           | `odds-api.ts` `americanfootball_ncaaf`                                          | Open/Best stored **away-signed**                                  |
| Trust          | `cfb-trusted-market.ts`                                                         | compares `row.kei` (home) to `row.open`/`row.best` (**away**) raw |
| Tags           | LEAN ≥ 2.5 · PLAY ≥ 4.0 · PASS default                                          | unchanged                                                         |

**Named loader bug (measure only):** `trustCfbMarket` sees home KEI vs away Open → `|−42.2 − (+50.5)| = 92.7` clears as `absurd_vs_kei` even when same-side `|−42.2 − (−50.5)| = 8.3` is inside the 12-pt band.

---

## Loader dump summary (live Odds, 2026-08-31)

| Metric                                                      |                       Value |
| ----------------------------------------------------------- | --------------------------: | -------------- | ------------------------------------------- |
| Odds events returned                                        | **103** (`feed_error=null`) |
| W1 FBS rows with KEI                                        |                      **43** |
| W1 FCS null KEI (count only)                                |                      **46** |
| Trusted Best kept (`reason=best`)                           |                       **7** |
| KEI but no trusted Best                                     |                      **36** |
| → `absurd_vs_kei`                                           |                      **35** |
| → of which **sign-mismatch clears** (same-side gap &lt; 12) |                      **27** |
| → true same-side absurd (ss_gap ≥ 12)                       |                       **8** |
| → `no_market`                                               |          **1** (`MASS@RUT`) |
| Board PLAY candidates (`                                    |                        edge | ≥4` + trusted) | **5** (listed below — **not** fired louder) |

Thresholds (verbatim): `ABSURD_VS_KEI=12` · `SINGLE_BOOK=8` · `LEAN=2.5` · `PLAY=4.0`.

---

## Full Week 1 FBS+KEI table

Columns:

- `open_h` / `best_h_tr` = home-signed for reading (`−open_away`)
- `reason` = board `trustCfbMarket` enum (raw home-KEI vs away-Open)
- `raw_gap` = `|kei_h − open_away|` (what trust sees)
- `ss_gap` = `|kei_h − open_h|` (same-side residual)
- `sign_bug` = Y if cleared `absurd_vs_kei` but `ss_gap < 12`

| family | pair        | kickoff          |  kei_h | open_h | best_h_tr | reason        | raw_gap | ss_gap | sign_bug |   edge | tag  | fire           |
| ------ | ----------- | ---------------- | -----: | -----: | --------: | ------------- | ------: | -----: | -------- | -----: | ---- | -------------- |
| A      | `BALL@OSU`  | 2026-09-05T16:30 |  -42.2 |  -50.5 |         — | absurd_vs_kei |    92.7 |    8.3 | Y        |      — | PASS | NO             |
| A      | `ECU@ALA`   | 2026-09-05T16:00 | -26.22 |  -28.5 |         — | absurd_vs_kei |   54.72 |   2.28 | Y        |      — | PASS | NO             |
| A      | `FIU@USF`   | 2026-09-05T23:00 | -19.74 |  -13.5 |         — | absurd_vs_kei |   33.24 |   6.24 | Y        |      — | PASS | NO             |
| A      | `MOST@TAMU` | 2026-09-05T23:00 | -32.25 |  -41.5 |         — | absurd_vs_kei |   73.75 |   9.25 | Y        |      — | PASS | NO             |
| A      | `TXST@TEX`  | 2026-09-05T19:30 | -25.15 |  -30.5 |         — | absurd_vs_kei |   55.65 |   5.35 | Y        |      — | PASS | NO             |
| A      | `UNT@IU`    | 2026-09-05T16:00 | -33.12 |  -40.5 |         — | absurd_vs_kei |   73.62 |   7.38 | Y        |      — | PASS | NO             |
| A      | `UTEP@OU`   | 2026-09-05T00:00 | -33.61 |  -41.5 |         — | absurd_vs_kei |   75.11 |   7.89 | Y        |      — | PASS | NO             |
| B      | `BOISE@ORE` | 2026-09-05T19:30 | -23.97 |  -24.5 |         — | absurd_vs_kei |   48.47 |   0.53 | Y        |      — | PASS | NO             |
| B      | `CLEM@LSU`  | 2026-09-05T23:30 |  -2.21 |  -10.5 |         — | absurd_vs_kei |   12.71 |   8.29 | Y        |      — | PASS | NO             |
| B      | `LOU@MISS`  | 2026-09-06T23:30 | -11.53 |   -6.5 |         — | absurd_vs_kei |   18.03 |   5.03 | Y        |      — | PASS | NO             |
| B      | `MIA@STAN`  | 2026-09-05T01:00 |  27.95 |   24.5 |         — | absurd_vs_kei |   52.45 |   3.45 | Y        |      — | PASS | NO             |
| B      | `SMU@FSU`   | 2026-09-07T23:30 |   8.35 |    3.5 |         3 | best          |   11.85 |   4.85 |          |   5.35 | PLAY | CANDIDATE_ONLY |
| B      | `WIS@ND`    | 2026-09-06T23:30 | -16.67 |  -20.5 |         — | absurd_vs_kei |   37.17 |   3.83 | Y        |      — | PASS | NO             |
| B      | `WSU@WASH`  | 2026-09-06T20:00 | -18.62 |  -23.5 |         — | absurd_vs_kei |   42.12 |   4.88 | Y        |      — | PASS | NO             |
| other  | `AKR@WAKE`  | 2026-09-03T23:00 | -11.93 |  -24.5 |         — | absurd_vs_kei |   36.43 |  12.57 |          |      — | PASS | NO             |
| other  | `ARST@MEM`  | 2026-09-05T23:00 | -12.04 |    -10 |         — | absurd_vs_kei |   22.04 |   2.04 | Y        |      — | PASS | NO             |
| other  | `BAY@AUB`   | 2026-09-05T19:30 | -10.37 |     -7 |         — | absurd_vs_kei |   17.37 |   3.37 | Y        |      — | PASS | NO             |
| other  | `BC@CIN`    | 2026-09-05T19:30 | -23.16 |   -7.5 |         — | absurd_vs_kei |   30.66 |  15.66 |          |      — | PASS | NO             |
| other  | `CCU@WVU`   | 2026-09-05T16:00 | -17.55 |  -21.5 |         — | absurd_vs_kei |   39.05 |   3.95 | Y        |      — | PASS | NO             |
| other  | `CMU@UNM`   | 2026-09-06T02:00 |  -5.84 |  -10.5 |         — | absurd_vs_kei |   16.34 |   4.66 | Y        |      — | PASS | NO             |
| other  | `COLO@GT`   | 2026-09-04T00:00 |  -5.26 |   -6.5 |      -6.5 | best          |   11.76 |   1.24 |          |   1.24 | PASS | NO             |
| other  | `FAU@UF`    | 2026-09-05T23:45 | -12.67 |  -27.5 |         — | absurd_vs_kei |   40.17 |  14.83 |          |      — | PASS | NO             |
| other  | `FRES@USC`  | 2026-09-05T01:00 | -29.76 |  -22.5 |         — | absurd_vs_kei |   52.26 |   7.26 | Y        |      — | PASS | NO             |
| other  | `KENT@SCAR` | 2026-09-05T16:45 | -27.02 |  -36.5 |         — | absurd_vs_kei |   63.52 |   9.48 | Y        |      — | PASS | NO             |
| other  | `LIB@JMU`   | 2026-09-05T16:00 |  -9.13 |   -6.5 |         — | absurd_vs_kei |   15.63 |   2.63 | Y        |      — | PASS | NO             |
| other  | `M-OH@PITT` | 2026-09-05T16:30 | -19.29 |  -16.5 |         — | absurd_vs_kei |   35.79 |   2.79 | Y        |      — | PASS | NO             |
| other  | `MASS@RUT`  | 2026-09-03T22:00 | -27.42 |      — |         — | no_market     |       — |      — |          |      — | PASS | NO             |
| other  | `MRSH@PSU`  | 2026-09-05T19:30 | -20.56 |  -24.5 |         — | absurd_vs_kei |   45.06 |   3.94 | Y        |      — | PASS | NO             |
| other  | `NIU@IOWA`  | 2026-09-05T20:15 | -21.68 |  -31.5 |         — | absurd_vs_kei |   53.18 |   9.82 | Y        |      — | PASS | NO             |
| other  | `OHIO@NEB`  | 2026-09-05T16:00 | -11.01 |  -23.5 |         — | absurd_vs_kei |   34.51 |  12.49 |          |      — | PASS | NO             |
| other  | `OKST@TLSA` | 2026-09-05T19:45 |  -1.07 |     14 |         — | absurd_vs_kei |   12.93 |  15.07 |          |      — | PASS | NO             |
| other  | `ORST@HOU`  | 2026-09-05T16:00 |  -6.38 |  -20.5 |         — | absurd_vs_kei |   26.88 |  14.12 |          |      — | PASS | NO             |
| other  | `SHSU@TROY` | 2026-09-05T23:00 | -17.67 |  -16.5 |         — | absurd_vs_kei |   34.17 |   1.17 | Y        |      — | PASS | NO             |
| other  | `SJSU@EMU`  | 2026-09-04T22:30 |  -5.41 |   -3.5 |      -3.5 | best          |    8.91 |   1.91 |          |  -1.91 | PASS | NO             |
| other  | `TOL@MSU`   | 2026-09-05T00:00 | -16.36 |    -10 |         — | absurd_vs_kei |   26.36 |   6.36 | Y        |      — | PASS | NO             |
| other  | `TULN@DUKE` | 2026-09-05T19:30 | -16.29 |   -9.5 |         — | absurd_vs_kei |   25.79 |   6.79 | Y        |      — | PASS | NO             |
| other  | `UAB@ILL`   | 2026-09-04T01:00 | -25.61 |  -28.5 |         — | absurd_vs_kei |   54.11 |   2.89 | Y        |      — | PASS | NO             |
| other  | `UCLA@CAL`  | 2026-09-06T02:30 | -12.83 |    1.5 |       1.5 | best          |   11.33 |  14.33 |          | -14.33 | PLAY | CANDIDATE_ONLY |
| other  | `ULM@MSST`  | 2026-09-05T23:30 | -13.42 |  -28.5 |         — | absurd_vs_kei |   41.92 |  15.08 |          |      — | PASS | NO             |
| other  | `UNLV@HAW`  | 2026-09-06T02:00 |  -2.48 |    3.5 |       2.5 | best          |    1.02 |   5.98 |          |  -4.98 | PLAY | CANDIDATE_ONLY |
| other  | `WKU@NEV`   | 2026-09-06T02:30 |   9.03 |    2.5 |       2.5 | best          |   11.53 |   6.53 |          |   6.53 | PLAY | CANDIDATE_ONLY |
| other  | `WMU@MICH`  | 2026-09-05T23:30 | -13.32 |  -27.5 |         — | absurd_vs_kei |   40.82 |  14.18 |          |      — | PASS | NO             |
| other  | `WYO@CSU`   | 2026-09-05T22:00 |   2.68 |     -3 |      -3.5 | best          |    0.32 |   5.68 |          |   6.18 | PLAY | CANDIDATE_ONLY |

---

## Answers to the five questions

### 1. How many W1 FBS rows have KEI but no trusted Best?

**36 / 43.**  
Breakdown: `absurd_vs_kei` 35 · `no_market` 1 (`MASS@RUT`).

### 2. How many have Best cleared as untrusted, and what was the Open?

**35** cleared `absurd_vs_kei` (board shows Best `—`, book label `untrusted`).

Of those, **27** are **sign-mismatch clears**: same-side gap &lt; 12 (Open exists and is not absurd on the home side). Examples:

| pair      | open_h |   ss_gap | note                              |
| --------- | -----: | -------: | --------------------------------- |
| BALL@OSU  |  −50.5 |      8.3 | feed live; trust false-clears     |
| BOISE@ORE |  −24.5 | **0.53** | almost pinned; trust false-clears |
| ECU@ALA   |  −28.5 |     2.28 |                                   |

**8 true same-side absurd** (ss_gap ≥ 12): `AKR@WAKE`, `ORST@HOU`, `OHIO@NEB`, `BC@CIN`, `OKST@TLSA`, `ULM@MSST`, `WMU@MICH`, `FAU@UF`.

### 3. On Family A, is KEI consistently longer or shorter than Open when Open exists?

**Open is the longer favorite on 6 / 7** (home-side):

| pair      |  kei_h | open_h | kei − open | longer fav |
| --------- | -----: | -----: | ---------: | ---------- |
| BALL@OSU  |  −42.2 |  −50.5 |       +8.3 | Open       |
| TXST@TEX  | −25.15 |  −30.5 |      +5.35 | Open       |
| ECU@ALA   | −26.22 |  −28.5 |      +2.28 | Open       |
| UTEP@OU   | −33.61 |  −41.5 |      +7.89 | Open       |
| MOST@TAMU | −32.25 |  −41.5 |      +9.25 | Open       |
| UNT@IU    | −33.12 |  −40.5 |      +7.38 | Open       |
| FIU@USF   | −19.74 |  −13.5 |      −6.24 | **KEI**    |

All Family A currently **PASS** on the board (Best cleared). Not a fire sheet.

### 4. BALL@OSU −42.2 vs Open ~−50 — feed, saturation, or both?

**Both, with roles named:**

1. **Feed is real.** Odds API returned Ball State +50.5 / Ohio State −50.5 (DraftKings/FanDuel). Not invented; not stale-fallback-only.
2. **KEI −42.2 is the cupcake-saturation exhibit** (unchanged; do not clamp).
3. **Board Best wipe is mostly the home/away compare bug** (`raw_gap=92.7` vs `ss_gap=8.3`). Same-side, this would be inside the 12-pt absurd band (and above single-book 8 if only one book — multi-book here).

So: **not a missing-feed problem.** It is KEI short of a long Open **plus** trust false-clearing Best.

### 5. Any row already clearing PLAY ≥ 4.0 with trusted Best?

**Yes — 5 board candidates** (tag already PLAY on dump; **this pass does not make them louder**):

| pair       | family |  kei_h | best_h_tr |   edge | caution                                                                                   |
| ---------- | ------ | -----: | --------: | -----: | ----------------------------------------------------------------------------------------- |
| `SMU@FSU`  | B      |  +8.35 |      +3.0 |  +5.35 | only Family B in set; discuss only if operator names a driver                             |
| `WYO@CSU`  | other  |  +2.68 |      −3.5 |  +6.18 | sign/side review before any talk                                                          |
| `WKU@NEV`  | other  |  +9.03 |      +2.5 |  +6.53 |                                                                                           |
| `UNLV@HAW` | other  |  −2.48 |      +2.5 |  −4.98 | side polarity odd — gate hard                                                             |
| `UCLA@CAL` | other  | −12.83 |      +1.5 | −14.33 | **ss_gap 14.33** — trust kept Best via away compare; treat as contaminated until sign fix |

**Operator gate:** none of these are a card. Family A has **zero** trusted PLAY. Soft-slate language is forbidden as a driver.

---

## Phase 1 allowlist (shipped this pass)

1. `scripts/cfb/cfb_dump_edgeboard.py` + dated JSON under `data/ops/`.
2. `docs/CFB_WEEK1_BOOK_SCORECARD.md` from this sheet.
3. **UI:** cleared Best shows `untrusted` / `no book` in footnote style (was swallowed when Best = —). **Did not** flip Open to home inside trust.
4. Assert BALL@OSU KEI still −42.2 (vitest + dump `--assert-canary`).

### Still forbidden

`apply_cfb_kei` · power · WP/shock · tag thresholds · loosening absurd band · inventing Open · Utah · clamping −42.2.

---

## Phase 0 → 1 status

Phase 0 dump + Phase 1 scorecard/script/UI label are in. **Operator still gates** which PLAY candidates may be discussed. Not a card.

**Reproduce:** `ODDS_API_KEY=… python3 scripts/cfb/cfb_dump_edgeboard.py --json`  
**Canary (no Odds key):** `python3 scripts/cfb/cfb_dump_edgeboard.py --assert-canary`
