# NFL depth identity audit — 2026-08-13

SoT pack: `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`  
Compared to: 2025 W1 historical pack (same family as #220) + FantasyPros 2026 Half-PPR ADP.  
Apply path: `SOT_SKILL_OVERRIDES` in `scripts/nfl/package_season_engine_depth_2026.py` via `scripts/nfl/apply_sot_skill_overrides_to_pack.py` (one pack, no second map).  
QB1 identities unchanged — **no 100k republish**.

## Must-fix (applied)

| Player | Before (pack) | After (pack) |
|--------|---------------|--------------|
| Kenneth Walker III | KC RB1 | **SEA RB1** |
| Zach Charbonnet | SEA RB1 | **SEA RB2** |
| Jadarian Price | SEA RB2 | SEA RB3 |
| Emmett Johnson | KC RB2 | KC RB1 |
| Emari Demercado | KC RB3 | KC RB2 |

Pacheco remains DET RB2 (ADP DET 157). Not auto-moved; restoring him to KC would be a second franchise rewrite. Flagged below.

## Before / after — pack smell check

- Walker SEA RB1 — **yes**
- Charbonnet not SEA RB1 — **yes** (RB2)
- Zero known stars on the wrong franchise in the must-fix set — **yes**

## 2025 → 2026 pack team moves (QB1 / RB1–2 / WR1)

ADP agrees with the 2026 pack on almost all of these. **Not auto-fixed** this pass (Walker/Charbonnet was the dual-map scramble; these look like 2026 FA/trade landings). Paste before merge:

| Player | 2025 pack | 2026 pack | ADP team (rank) |
|--------|-----------|-----------|-----------------|
| A.J. Brown | PHI WR1 | NE WR1 | NE (23) |
| Mike Evans | TB WR1 | SF WR1 | SF (61) |
| DJ Moore | CHI WR1 | BUF WR1 | BUF (52) |
| Travis Etienne Jr. | JAX RB1 | NO RB1 | NO (39) |
| David Montgomery | DET RB2 | HOU RB1 | HOU (50) |
| Isiah Pacheco | KC RB1 | DET RB2 | DET (157) |
| Jaylen Waddle | MIA (2025) | DEN WR2 | DEN (48) |
| Michael Pittman Jr. | IND WR1 | PIT WR2 | PIT (103) |
| Stefon Diggs | NE WR1 | WAS WR2 | WAS (154) — already SoT overlay |
| Brian Robinson Jr. | SF RB2 | ATL RB2 | ATL (134) |
| Rachaad White | TB RB2 | WAS RB2 | WAS (110) |
| Rico Dowdle | CAR RB2 | PIT RB2 | PIT (78) |
| Tank Bigsby | JAX RB2 | PHI RB2 | PHI (181) |
| Tyler Allgeier | ATL RB2 | ARI RB2 | ARI (133) |
| Jauan Jennings | SF WR1 | MIN WR3 | MIN (161) |
| Geno Smith | LV QB1 | NYJ QB1 | NYJ (250) |
| Justin Fields | NYJ QB1 | KC QB2 | KC (274) |
| Tua / Kyler | (SoT #220) | ATL / MIN | already checksum |

Jakobi Meyers: pack JAX WR2 vs ADP JAC — same franchise, label only.

## CSV vs pack (after Walker realloc)

Only remaining skill mismatches at depth ≤2:

- **Emeka Egbuka** — CSV SF WR1 vs pack **TB WR1** (ADP TB)
- **Mike Evans** — CSV TB WR1 vs pack **SF WR1** (ADP SF)

These are inverted vs the pack/ADP. Not moved this PR (would reallocate TB/SF pass pools). Add to the next identity pass if desk confirms pack/ADP over the #226 CSV labels.

## Daily intel

Desk record: `data/ops/nfl-daily-intel/20260813-sea-walker-sot.json` (`wait_republish` — intel overlay still cannot reassign `team`; franchise moves go through `SOT_SKILL_OVERRIDES` on the same pack).
