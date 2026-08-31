# CFB grade schema (desk publication)

**Phase:** Infrastructure. Not a ratings pass.  
**Stamp frozen:** `cfb-season-engine-v0.15-power-sot` + 1C–1E + `EFF_CARRY_SHRINK=0.85`  
**SHA baseline:** `ce41aaf9` (Chapter 2) + `#357` (Phase 1 remainder)  
**Store:** append-only `data/cfb_grades_2026.jsonl`  
**Card seed:** `data/ops/cfb-w1-handicap-card-20260831.json` (`sheet_ts=2026-08-31T21:38Z`)

KEI files are **not** rewritten by this harness.

---

## Purpose

Freeze what the desk published, then grade it after the ball is kicked.  
Side and total are **separate rows**.

Freeze **at kick** (not at card stamp, not at close). W1 first fill starts from the stamped card and may overwrite Best/tag if the board moved before kick.

---

## Row contract

One JSON object per line in `data/cfb_grades_2026.jsonl`.

| Field              | Type                                        | Notes                                                                        |
| ------------------ | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `season`           | int                                         | 2026                                                                         |
| `week`             | int                                         | 0 or 1 (later weeks append)                                                  |
| `game_id`          | string \| null                              | Official slate / ESPN id when known                                          |
| `home`             | string                                      | Abbr                                                                         |
| `away`             | string                                      | Abbr                                                                         |
| `market`           | `"spread"` \| `"total"`                     | Separate rows                                                                |
| `kei`              | number \| null                              | Published KEI at kick (home-signed spread, or total)                         |
| `model_kei`        | number \| null                              | Research-fair; not tagged                                                    |
| `open`             | number \| null                              | First trusted print (home-signed spread / total); else null                  |
| `best_kick`        | number \| null                              | Trusted Best at kick — **home-signed** for spreads; total points for O/U     |
| `book`             | string \| null                              | Book on Best                                                                 |
| `trusted`          | bool \| null                                | Trust gate; null when tag is `n/a`                                           |
| `tag`              | `"PASS"` \| `"LEAN"` \| `"PLAY"` \| `"n/a"` | As printed; W0 close tape = `n/a`                                            |
| `size_note`        | `"fat-dog"` \| null                         | Set when `\|best_kick\| ≥ 28` (spread, home-signed) **or** cupcake WP ≥ 0.90 |
| `close`            | number \| null                              | Last trusted before kick-off + 5m (same sign convention as `best_kick`)      |
| `final_home`       | int \| null                                 | Official                                                                     |
| `final_away`       | int \| null                                 | Official                                                                     |
| `ats_vs_kei`       | `"cover"` \| `"push"` \| `"miss"` \| null   | KEI line vs final (not vs the bet)                                           |
| `ats_vs_tag`       | `"cover"` \| `"push"` \| `"miss"` \| null   | Tagged number vs final; null if PASS / n/a                                   |
| `clv`              | number \| null                              | Best_kick → close, signed with the tagged side                               |
| `signed_error_kei` | number \| null                              | See sign conventions                                                         |
| `wp_bucket`        | string \| null                              | `cupcake` / `fav_60_75` / `tossup` / `other`                                 |
| `card_stamp`       | string \| null                              | W1 seed stamp when row came from the card                                    |
| `source`           | string                                      | `w0_published` \| `w1_card_20260831` \| later writers                        |
| `recorded_at`      | string                                      | ISO UTC when the line was appended                                           |

### Sign conventions

- Spreads: `kei`, `model_kei`, `open`, `best_kick`, `close` are **home-signed** (same as published KEI).
- Totals: points (over/under line).
- `signed_error_kei` (spread): `(final_home - final_away) + kei`  
  (home margin minus expected home margin `−kei`).  
  Example: KEI −40.5, final 45–3 → margin +42; error = 42 − 40.5 = +1.5.
- `signed_error_kei` (total): `(final_home + final_away) - kei`.

### ATS helpers

- Spread vs KEI: home covers KEI when `(final_home - final_away) + kei > 0`; push at 0; else miss.  
  (`ats_vs_kei` is from the **line**, not which side the desk tagged.)
- Spread vs tag: evaluate the **tagged side’s** number (Best when tagged LEAN/PLAY) against the final. Null when `tag` is PASS or n/a.
- Total vs KEI: over covers when `final_total > kei`; push equal; else under (miss for over). Same for tag when Over/Under was tagged.

### `wp_bucket`

From published home WP when available:

| Bucket      | Rule                                 |
| ----------- | ------------------------------------ |
| `cupcake`   | WP ≥ 0.90 or WP ≤ 0.10               |
| `fav_60_75` | 0.60 ≤ WP < 0.90 or 0.10 < WP ≤ 0.40 |
| `tossup`    | 0.45 ≤ WP ≤ 0.55                     |
| `other`     | everything else / missing            |

---

## Allowlist

- This schema doc
- `data/cfb_grades_2026.jsonl` (append-only)
- `data/ops/cfb-w1-handicap-card-20260831.json` (seed input only)
- `scripts/cfb/grade_harness.py` — seed + summarize + later close/final fill
- Read-only summary output under `data/ops/` (markdown/json)

No publisher. No tag rewriter. No dashboard redesign for v0.

---

## Forbidden

- Same-week KEI re-emit justified by the harness
- Changing 2.5 / 4.0 because early ATS looks bad
- Dropping fat-dog PLAYs from the table
- Power SoT / shrink / Utah edits
- Chapter 3 coefficients from W0/W1 grades

---

## First fill checklist

1. Schema + empty store
2. Insert W0 six (spread + total each) — KEI pre-final published; tag `n/a`; finals from official slate
3. Insert W1 from stamped card (sides + totals)
4. After Sat 9/5: fill `close`, `final_*`, ATS, CLV, `signed_error_kei` for W1

**Pre-registered question:** did tagged PLAY sides beat chance, and did fat-dog PLAY sides beat the rest?

Chapter 3 Phase 0 stays parked until this harness ships.
