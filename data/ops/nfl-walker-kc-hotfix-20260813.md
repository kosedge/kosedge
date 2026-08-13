# NFL Walker → KC hotfix — 2026-08-13

Depends on: #228 (`20260813T164500Z`)  
Bundle: `nfl-preseason-sim-2026-20260813T172000Z`  
Doctrine: **Reality > pack when pack is wrong.** Then update the pack so the error cannot recur.

Weekly props stay **gated**. KEI untouched. No 100k re-sim. Rank ≠ ADP.

## What went wrong

#227 / #228 treated the depth pack as infallible. Pack still had Kenneth Walker III on SEA. Identity sweep “fixed” CSV to match pack, which **reintroduced the dual-map error in the opposite direction of ADP and 2026 reality**.

Walker signed with Kansas City in March 2026 (after Super Bowl MVP in Seattle). ADP ~18 KC was correct. Pack was wrong.

## Fact (locked)

| Player | Team | Role |
|--------|------|------|
| Kenneth Walker III | **KC** | RB1 |
| Zach Charbonnet | **SEA** | RB1 / primary (not RB2 behind a ghost Walker) |
| Emmett Johnson | **KC** | RB2 (secondary to Walker) |

Evans = SF and Egbuka = TB from #228 still hold.

## Pack

`SOT_SKILL_OVERRIDES` is the lock. Live pack rewritten in place via `apply_sot_skill_overrides_to_pack.py`.

| Slot | Before (#228 pack) | After |
|------|-------------------|-------|
| SEA RB1 | Kenneth Walker III | **Zach Charbonnet** |
| SEA RB2 | Zach Charbonnet | Jadarian Price |
| SEA RB3 | Jadarian Price | George Holani |
| KC RB1 | Emmett Johnson | **Kenneth Walker III** |
| KC RB2 | Emari Demercado | Emmett Johnson |
| KC RB3 | — | Emari Demercado |
| Walker rows | SEA only | **KC only** |

Bates `injury_status=out` preserved. No duplicate skill slots. QB1 checksum unchanged.

## Fantasy / projection CSV

Source: `20260813T164500Z`. Identity align to corrected pack, then role-aware reshape of **KC + SEA RBs only** (WR alpha skipped so JSN/Puka/Rice do not move). Rec restore is **by position group** so an RB franchise move cannot inflate SEA WRs.

| Player | Before (#228) | After |
|--------|---------------|-------|
| Kenneth Walker III | SEA RB1 / RB6 / ov 41 / 266 pts / 1395 rush | **KC RB1 / RB29 / ov 98 / 170 pts / 904 rush** |
| Zach Charbonnet | SEA RB2 / ~RB14 / 225 pts | **SEA RB1 / RB5 / ov 36 / 272 pts / 1188 rush** |
| Emmett Johnson | KC RB1 | **KC RB2**, rush behind Walker |

Walker is a Chief on every surface. Charbonnet is Seattle’s back without a ghost Walker.

### Why Walker is not ADP-18 points

Conservation kept each franchise’s existing rush budget. KC’s Johnson-era RB rush pool is ~1,300 yards. Walker takes a **feature share** of that pool (904 rush, primary over Johnson) — not a 1,400-yard magnet invented from nowhere. ADP ~18 is the market; this board will not print Henry/Gibbs points on a thin KC rush total until a 100k with Walker-in-KC usage. Rank ≠ ADP (explicit non-goal).

SEA’s feature-back rush that the sim had allocated to “Walker on Seattle” now sits with Charbonnet as the actual Seahawks lead back. That is franchise conservation, not a claim Charbonnet is CMC-class.

## #228 holdovers (not regressed)

| Player | #228 | This pass |
|--------|------|-----------|
| Gibbs | DET RB4 / ov 24 / 290 | **same** |
| Allen | ov 10 | **same** |
| Lamar | ov 11 | **same** |
| Evans | SF | **SF** |
| Egbuka | TB | **TB** |
| JSN | WR13 / 255 / 1293 rec | **same** |
| Puka | WR6 / ov 31 / 1450 | **same** |
| Top-5 RB spread | ~104 | **~99** (CMC 371 → Charbonnet 272) |

## Weekly props

Still `PROPS_PATH_COHERENT=gated`. Do not ungate until the weekly box sim is rebuilt on Walker=KC + this production path.

## Gates

- Walker pack + fantasy CSV = **KC** — **PASS**
- Charbonnet pack + fantasy CSV = **SEA RB1** — **PASS**
- Walker rush > Johnson — **PASS**
- Evans=SF / Egbuka=TB — **PASS**
- Gibbs/Allen/Lamar not regressed — **PASS**
- Checksum QBs (Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler) — **PASS**
- Pack file updated so Walker-SEA cannot recur via re-pack — **PASS**
