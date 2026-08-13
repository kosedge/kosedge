# NFL depth identity full sweep — 2026-08-13

Depends on: #227 (`20260813T161500Z`)  
Bundle: `nfl-preseason-sim-2026-20260813T164500Z`  
Rule: **pack team = projection team = fantasy desk team**. Pack wins. ADP is a note, not a second map.

Weekly props stay **gated**. KEI untouched. No 100k re-sim.

## Full skill diff (pack ∩ CSV)

After #227, every must-reconcile name except Evans/Egbuka already matched the pack. Full RB/WR/TE/QB overlap found **exactly two** franchise mismatches:

| Player | CSV before | Pack / ADP | CSV after |
|--------|------------|------------|-----------|
| Mike Evans | TB WR1 / ov 48 / 258 pts / 1336 rec | **SF WR1** (ADP 61 SF) | **SF WR11 / ov 46 / 262 pts / 1360 rec** |
| Emeka Egbuka | SF WR1 / ov 36 / 272 pts / 1410 rec | **TB WR1** (ADP 41 TB) | **TB WR9 / ov 39 / 267 pts / 1384 rec** |

Re-allocated **SF + TB only**. Team rec/rush/TD budgets conserved. Evans/Egbuka no longer inverted vs pack.

## Must-reconcile list (pack = fantasy CSV)

| Player | Pack | Fantasy CSV | ADP | Notes |
|--------|------|-------------|-----|-------|
| A.J. Brown | NE WR1 | **NE** | NE 23 | Already aligned in #227 CSV |
| Mike Evans | SF WR1 | **SF** | SF 61 | **Moved this pass** |
| Emeka Egbuka | TB WR1 | **TB** | TB 41 | **Moved this pass** |
| DJ Moore | BUF WR1 | **BUF** | BUF 52 | Already aligned |
| Travis Etienne Jr. | NO RB1 | **NO** | NO 39 | Already aligned |
| David Montgomery | HOU RB1 | **HOU** | HOU 50 | Already aligned |
| Jaylen Waddle | DEN WR2 | **DEN** | DEN 48 | Already aligned |
| Michael Pittman Jr. | PIT WR2 | **PIT** | PIT 103 | Already aligned |
| Isiah Pacheco | DET RB2 | **DET** | DET 157 | Already aligned; KC RB1 = Emmett Johnson |
| Kenneth Walker III | SEA RB1 | **SEA** | **KC 18** | Pack/desk SoT; ADP stale |
| Zach Charbonnet | SEA RB2 | **SEA RB2** | 124 | Unchanged from #227 |

**Fantasy team labels match pack for top-100 ADP** where the player exists in both (gate in `check_nfl_fantasy_shape_gates.py`). ADP≠pack only: Walker (KC vs SEA) — pack wins.

## #227 holdovers (not regressed)

| Player | #227 | This pass |
|--------|------|-----------|
| Gibbs | DET RB4 / ov 24 / 290 | **same** |
| Allen | ov 10 | **same** |
| Lamar | ov 11 | **same** |
| Walker | SEA RB6 / ov 41 / 266 | **same** |
| Charbonnet | SEA RB2 / RB13–14 / 225 | **same pts; still outside top 8** |
| JSN | WR13 / 255 / 1293 rec | **same** (SEA budget ceiling) |
| Puka | WR6 / ov 31 / 1450 | **same** |
| Top-5 RB spread | ~102 | **~104** (CMC 371 → Henry 267) |

CMC ticked +2 pts because SF was a touched team (Evans arrived); Gibbs/Allen/Lamar untouched.

## Pack audit

No duplicate skill slots. No missing must-list player. Pack was already internally consistent; CSV was the dual-map.

## Weekly props

Still `PROPS_PATH_COHERENT=gated`. Do not ungate until this identity path is also on the weekly box sim.

## Gates

- Zero must-reconcile pack≠fantasy — **PASS**
- Evans/Egbuka not inverted vs pack — **PASS**
- Walker SEA / Charbonnet SEA RB2 — **PASS**
- Gibbs/Allen/Lamar not regressed vs #227 — **PASS**
- Top-5 RB spread healthy — **PASS**
- Checksum QBs unchanged — **PASS**
