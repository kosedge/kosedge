# WNBA grade schema (desk publication)

**Phase:** Infrastructure. Not a ratings pass.  
**Stamp frozen:** `v0.1` · Ch2–Ch7  
**Store:** append-only `data/wnba_grades_2026.jsonl`

Ch4 KEI / Ch5 projection / Ch6 props packs are **not** rewritten by this harness.  
Fantasy stays Ch5-scored only (Ch7). Props stay untagged (`n/a` on prop rows).

---

## Purpose

Freeze what the desk published, then grade it after tip-off.  
Side, total, and **each displayed prop** are **separate rows**.

Freeze **at tip** (not at card stamp, not at close). First fill seeds schema example rows only; regular-season / playoff `close` / `final` stay empty on purpose until real games tip.

Playoffs begin **Sep 27** — this PR is schema + empty store only so grading can start when tips land. **Not** a tag PR.

---

## Row contract

One JSON object per line in `data/wnba_grades_2026.jsonl`.

| Field          | Type                                        | Notes                                                                                              |
| -------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `season`       | int                                         | 2026                                                                                               |
| `date`         | string \| null                              | Game date `YYYY-MM-DD` (tip local calendar day)                                                    |
| `game_id`      | string \| null                              | Stable game id when known                                                                          |
| `player_id`    | string \| null                              | Null on team side/total rows; set on prop rows                                                     |
| `market`       | string                                      | `"spread"` \| `"total"` \| Odds-backed prop (`pts` \| `reb` \| `ast` \| `threes`)                  |
| `kei`          | number \| null                              | Ch4 team KEI at tip (home-signed spread, or total). **Null on prop rows.**                         |
| `proj`         | number \| null                              | Ch5 `PlayerProjection` mean for that prop. **Null on team side/total rows.**                       |
| `open`         | number \| null                              | First trusted print (same sign convention as `best_kick`)                                          |
| `best_kick`    | number \| null                              | Trusted Best **at tip** — home-signed spread / total points / prop line                            |
| `book`         | string \| null                              | Book on Best                                                                                       |
| `trusted`      | bool \| null                                | Trust gate; null when unknown                                                                      |
| `tag`          | `"PASS"` \| `"LEAN"` \| `"PLAY"` \| `"n/a"` | Team rows: as printed (Ch4). **Prop rows: always `n/a` until a later tag PR.**                     |
| `size_note`    | string \| null                              | Optional desk size flag; null until a size policy ships                                            |
| `close`        | number \| null                              | Last trusted before tip + 5m (same sign as `best_kick`). Empty until real tips.                    |
| `final`        | number \| null                              | Outcome for this row’s market (see below). Empty until real tips.                                  |
| `ats_vs_kei`   | `"cover"` \| `"push"` \| `"miss"` \| null   | Team KEI line vs final. Null on props / when unfilled.                                             |
| `ats_vs_tag`   | `"cover"` \| `"push"` \| `"miss"` \| null   | Tagged number vs final; null if PASS / n/a / unfilled                                              |
| `clv`          | number \| null                              | Best_kick → close, signed with the tagged side                                                     |
| `signed_error` | number \| null                              | See sign conventions                                                                               |
| `source`       | string                                      | `schema_example` \| later tip writers                                                              |
| `recorded_at`  | string                                      | ISO UTC when the line was appended                                                                 |

### Markets

- **Team:** `spread`, `total` — `kei` from Ch4; `proj` null; `player_id` null.
- **Props (displayed / Odds-backed only):** `pts`, `reb`, `ast`, `threes` — `proj` from Ch5; `best_kick` from Ch6 Best; `kei` null; `tag` = `n/a`. Do **not** invent PRA/PR/RA rows until Odds posts them.

### `final` meaning

| Market   | `final`                                             |
| -------- | --------------------------------------------------- |
| `spread` | Home margin (`home_score − away_score`)             |
| `total`  | Combined points (`home_score + away_score`)         |
| prop     | Official counted stat for that market (e.g. points) |

### Sign conventions

- Spreads: `kei`, `open`, `best_kick`, `close` are **home-signed** (same as Ch4 KEI).
- Totals / props: points (over/under or prop line).
- `signed_error` (spread): `final + kei` (home margin vs expected `−kei`).
- `signed_error` (total): `final − kei`.
- `signed_error` (prop): `final − proj` when both filled.

### ATS helpers

- Spread vs KEI: home covers when `final + kei > 0`; push at 0; else miss.
- Total vs KEI: over covers when `final > kei`; push equal; else miss.
- Props: `ats_vs_kei` stays null (no KEI). `ats_vs_tag` stays null while `tag` is `n/a`.
- Team `ats_vs_tag`: evaluate the tagged side’s number (Best when LEAN/PLAY) against `final`. Null when `tag` is PASS or n/a.

---

## Allowlist

- This schema doc
- `data/wnba_grades_2026.jsonl` (append-only)
- `scripts/wnba/grade_harness.py` — seed + summarize + later tip close/final fill
- Read-only summary output under `data/ops/` (markdown/json)
- WNBA-only CI

No publisher. No tag rewriter. No preview copy. No dashboard redesign for v0. No Fantasy scorer change.

---

## Forbidden

- KEI re-emit justified by the harness
- Props PLAY / LEAN (tag PR later)
- New means / minute-grid rewrite / Ch7 fantasy retune
- Preview copy / Chapter 8 chrome / 15 team previews
- CFB/NBA/NFL grade files (except a shared helper if one already exists — none today)

---

## First fill checklist

1. Schema + empty store
2. Seed **schema example rows only** (no fake finals)
3. Leave regular-season / playoff `close` / `final` empty on purpose

**Done when** those three exist and Ch4 / Ch5 / Ch6 packs are unchanged.

Not a tag PR. Fantasy remains Ch5-only. Props stay untagged.
