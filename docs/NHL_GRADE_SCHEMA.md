# NHL grade schema (desk publication)

**Phase:** Infrastructure. Not a ratings pass.  
**Stamp frozen:** `v0.1` · Ch2–Ch7  
**Store:** append-only `data/nhl_grades_2026.jsonl`

Ch4 KEI / Ch5 projection / Ch6 props packs are **not** rewritten by this harness.  
Fantasy stays Ch5-scored only (Ch7). Props stay untagged (`n/a` on prop rows).

---

## Flag — season length (do not patch Ch7 in this PR)

2026–27 NHL regular season is **84** games. Ch7 currently multiplies `fantasy_pts × 82`.

```text
NHL_FANTASY_GAMES = 84   # register here; apply in a one-line Ch7 follow-up
```

**Not** a ratings pass. Do **not** change `nhl_fantasy.py` / `SEASON_GAMES` in this harness PR. Follow-up may bump the constant only.

---

## Purpose

Freeze what the desk published, then grade it after puck-drop.  
Puck / total and **each displayed prop** are **separate rows**.

Freeze **at tip** (not at card stamp, not at close). First fill seeds schema example rows only; regular-season `close` / `final` stay empty on purpose until real games tip.

Opening night **Sep 29**. After this PR, NHL is **parked** until camps (~Sep 16) for Chapter 8 chrome. **No tag PR this week.**

---

## Row contract

One JSON object per line in `data/nhl_grades_2026.jsonl`.

| Field          | Type                                        | Notes                                                                                       |
| -------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `season`       | int                                         | 2026 (2026–27 season label)                                                                 |
| `date`         | string \| null                              | Game date `YYYY-MM-DD` (tip local calendar day)                                             |
| `game_id`      | string \| null                              | Stable game id when known                                                                   |
| `player_id`    | string \| null                              | Null on team puck/total rows; set on prop rows                                              |
| `market`       | string                                      | `"spread"` (puck) \| `"total"` \| Odds-backed prop (`goals` \| `assists` \| `pts` \| `sog`) |
| `kei`          | number \| null                              | Ch4 team KEI at tip (home-signed puck, or total). **Null on prop rows.**                    |
| `proj`         | number \| null                              | Ch5 `PlayerProjection` mean for that prop. **Null on team puck/total rows.**                |
| `open`         | number \| null                              | First trusted print (same sign convention as `best_kick`)                                   |
| `best_kick`    | number \| null                              | Trusted Best **at tip** — home-signed puck / total goals / prop line                        |
| `book`         | string \| null                              | Book on Best                                                                                |
| `trusted`      | bool \| null                                | Trust gate; null when unknown                                                               |
| `tag`          | `"PASS"` \| `"LEAN"` \| `"PLAY"` \| `"n/a"` | Team rows: as printed (Ch4). **Prop rows: always `n/a` until a later tag PR.**              |
| `size_note`    | string \| null                              | Optional desk size flag; null until a size policy ships                                     |
| `close`        | number \| null                              | Last trusted before tip + 5m (same sign as `best_kick`). Empty until real tips.             |
| `final`        | number \| null                              | Outcome for this row’s market (see below). Empty until real tips.                           |
| `ats_vs_kei`   | `"cover"` \| `"push"` \| `"miss"` \| null   | Team KEI line vs final. Null on props / when unfilled.                                      |
| `ats_vs_tag`   | `"cover"` \| `"push"` \| `"miss"` \| null   | Tagged number vs final; null if PASS / n/a / unfilled                                       |
| `clv`          | number \| null                              | Best_kick → close, signed with the tagged side                                              |
| `signed_error` | number \| null                              | See sign conventions                                                                        |
| `source`       | string                                      | `schema_example` \| later tip writers                                                       |
| `recorded_at`  | string                                      | ISO UTC when the line was appended                                                          |

### Markets

- **Team:** `spread` (puck line / `kei_puck_home`), `total` — `kei` from Ch4; `proj` null; `player_id` null.
- **Props (displayed / Odds-backed only):** `goals`, `assists`, `pts`, `sog` — `proj` from Ch5; `best_kick` from Ch6 Best; `kei` null; `tag` = `n/a`. Goalie SAVES stay research-only while `STARTER_GATE=unknown` (not graded as PLAY).

### `final` meaning

| Market   | `final`                                            |
| -------- | -------------------------------------------------- |
| `spread` | Home margin (`home_goals − away_goals`)            |
| `total`  | Combined goals (`home_goals + away_goals`)         |
| prop     | Official counted stat for that market (e.g. goals) |

### Sign conventions

- Puck / spreads: `kei`, `open`, `best_kick`, `close` are **home-signed** (same as Ch4 `kei_puck_home`).
- Totals / props: goals / prop line.
- `signed_error` (spread/puck): `final + kei` (home margin vs expected `−kei`).
- `signed_error` (total): `final − kei`.
- `signed_error` (prop): `final − proj` when both filled.

### ATS helpers

- Puck vs KEI: home covers when `final + kei > 0`; push at 0; else miss.
- Total vs KEI: over covers when `final > kei`; push equal; else miss.
- Props: `ats_vs_kei` stays null (no KEI). `ats_vs_tag` stays null while `tag` is `n/a`.
- Team `ats_vs_tag`: evaluate the tagged side’s number (Best when LEAN/PLAY) against `final`. Null when `tag` is PASS or n/a.

---

## Allowlist

- This schema doc (includes `NHL_FANTASY_GAMES=84` flag)
- `data/nhl_grades_2026.jsonl` (append-only)
- `scripts/nhl/grade_harness.py` — seed + summarize + later tip close/final fill
- Read-only summary output under `data/ops/` (markdown/json)
- NHL-only CI

No publisher. No tag rewriter. No preview copy. No dashboard redesign for v0.

---

## Forbidden

- KEI re-emit justified by the harness (FLA@CAR puck **−0.94** stays Ch4 SoT)
- Props PLAY / LEAN (tag PR later — not this week)
- New means / TOI rewrite
- Preview copy / Chapter 8 chrome (parked until camps ~Sep 16)
- Patching Ch7 `SEASON_GAMES` in this PR (flag only — see above)
- NBA/WNBA/CFB/NFL grade files (except a shared helper if one already exists — none today)

---

## First fill checklist

1. Schema + empty store
2. Seed **schema example rows only** (no fake finals) — team rows Ch4-shaped; prop rows Ch5+Ch6-shaped; props `tag=n/a`
3. Leave regular-season `close` / `final` empty on purpose

**Done when** those three exist and Ch4 / Ch5 / Ch6 packs are unchanged.

Chapter 8 chrome waits on camps (~Sep 16). Chapter 9 is infra only — **not** a ratings pass, **not** a tag PR.
