# NFL KEI Week 1 reprice — Gate B (2026-08-13)

**Branch / PR:** `feat/nfl-kei-week1-reprice-factors` → `deploy-vercel`  
**Scope:** 2026 Week 1 REG only (16 games). Model untouched. No 100k republish in this PR.

## Doctrine

| Layer | Meaning |
|-------|---------|
| **Model** | Pre-reprice research fair (`model_markets` / pre-blend). Frozen. |
| **KEI** | Model + Gate B desk factors (this pass). |
| **Edge / Tag** | KEI − best market. Never Model vs market for PLAY/LEAN. |

Identity fallback remains when Model/spread is missing. PRE stays off the board.

Copy: **KEI = model + Week 1 desk factors.** Soft Launch notes page still accurate as a how-to-read desk.

## Factor definitions

SoT is the #220 depth pack (`nfl_depth_chart_2026_w1.json`). No second QB/injury map.

### 1. QB confirmation / backup drop-off

| Situation | Spread | Total | Confidence |
|-----------|--------|-------|------------|
| Named starter / starter | 0 | 0 | unchanged; logged |
| `open_competition` | 0 | 0 | −0.12 (`qb_clear=false`) — **not a fake spread lock** |
| QB1 out / IR / PUP | +3.5 team-weaker | +1.5 | −0.08 |

W1 pack: ATL Tua/Penix open competition; CLE Watson/Sanders open competition; MIA Willis named; MIN Kyler named.

### 2. Injury (known SoT only)

| Role | Status | Spread (team weaker) | Total |
|------|--------|----------------------|-------|
| OL starter or `depth_slot=out` | out / IR | 0.50 | 0.25 |
| Skill starter (RB/WR/TE1) | out | 0.75 | 0.40 |
| Skill #2 | out | 0.40 | 0.20 |
| TE3 / depth | any | **not applied** (logged) |
| Starter limited / questionable | unresolved | 0.25 | 0.10 + `injury_clear=false` |

Team injury spread subcap **1.5**. Bates TE3 out is logged, not stacked. Tunsil LT out + Allegretti C out **are** stacked (WAS @ PHI).

**No double count:** if the frozen projection already has `diagnostics.injury_kei_reprice` or non-zero `factor_contributions.injuries_depth`, injury points are not restacked.

### 3. Rest / travel

- **Short week / bye:** not applied on Week 1 (no prior REG rest gap). Logged.
- **Thu/Mon:** if kickoff weekday is detectable, logged as W1 opener — not a short-week tax.
- **Timezone travel** (hours west of ET: Pacific 3 / Mountain 2 / Central 1 / Eastern 0):

| TZ bands | Away spread (visitor weaker) | Total |
|----------|------------------------------|-------|
| ≥ 3 (cross-country) | 1.00 | −0.50 |
| 2 | 0.75 | −0.30 |
| 1 | 0.35 | −0.15 |
| 0 (same coast) | not applied | — |

Skip restack if frozen model already has non-zero `travel_schedule` / `rest_travel`.

### 4. Weather — honest stub

- Indoor home (`ATL DET NO MIN DAL HOU ARI LV IND`): `weather not applied (indoor)`.
- Else if projection already has a real forecast: not restacked.
- Else: `weather not applied (no forecast on this read path)`. **Do not fake stadium weather.** SoFi (LA/LAC) is outdoor.

### 5. Refs — stub

Always `ref not applied (crew data not ready)`. Does not block the board.

## Caps

| Cap | Value | Why |
|-----|-------|-----|
| Net spread | ±4.0 | Fits QB1-out 3.5 plus a modest travel/injury remainder |
| Net total | ±2.0 | Prevent runaway total stacks |
| Team injury spread | 1.5 | OL + skill on one side |

## Wiring

Read-time on `GET /nfl/fair-lines` after `resolve_model_and_handicap`:

1. Freeze Model.
2. Apply Gate B to handicap only.
3. Recompute edges/tags from new KEI.
4. Attach `kei_reprice` log (applied + considered-not-applied).
5. Open-competition → `nfl_assess_confidence(qb_clear=False)`.

Does **not** mutate DB. Does **not** wait on 100k. Reprice errors are swallowed so the board stays 200.

## Sample Week 1 table (factor-only)

Synthetic Model −3.0 / 44.0 on every game so the **delta is the desk stack only**. Live Model / market numbers come from the board after 100k + books. Do not treat this table as a betting card.

| Game | Model spr | KEI spr | Δ spr | Δ tot | Drivers (abbrev) | Market |
|------|-----------|---------|-------|-------|------------------|--------|
| CHI @ CAR | −3.0 | −3.35 | −0.35 | −0.15 | CHI 1-band travel | live board |
| TB @ CIN | −3.0 | −3.0 | 0 | 0 | Burrow / Mayfield confirmed; same-coast | live board |
| NO @ DET | −3.0 | −3.35 | −0.35 | −0.15 | NO 1-band; weather indoor | live board |
| BUF @ HOU | −3.0 | −3.35 | −0.35 | −0.15 | BUF 1-band; weather indoor | live board |
| BAL @ IND | −3.0 | −3.0 | 0 | 0 | named QBs; indoor; same-coast | live board |
| CLE @ JAX | −3.0 | −3.0 | 0 | 0 | **open_competition** Watson/Sanders (confidence only) | live board |
| DEN @ KC | −3.0 | −3.35 | −0.35 | −0.15 | DEN 1-band | live board |
| SF @ LA | −3.0 | −3.0 | 0 | 0 | same-coast outdoor | live board |
| ARI @ LAC | −3.0 | −3.0 | 0 | 0 | Brissett named; same-coast | live board |
| MIA @ LV | −3.0 | −4.0 | −1.00 | −0.50 | **Willis named**; MIA 3-band travel; indoor | live board |
| GB @ MIN | −3.0 | −3.0 | 0 | 0 | **Kyler named**; indoor; same-coast | live board |
| DAL @ NYG | −3.0 | −3.35 | −0.35 | −0.15 | DAL 1-band | live board |
| WAS @ PHI | −3.0 | −4.0 | −1.00 | +0.50 | Tunsil LT out + Allegretti C out; Bates TE3 **not** stacked | live board |
| ATL @ PIT | −3.0 | −3.0 | 0 | 0 | **open_competition** Tua/Penix (confidence only) | live board |
| NE @ SEA | −3.0 | −4.0 | −1.00 | −0.50 | NE 3-band travel | live board |
| NYJ @ TEN | −3.0 | −3.35 | −0.35 | −0.15 | NYJ 1-band | live board |

**9 / 16 games Model ≠ KEI** on this factor-only pass (travel and/or WAS OL). ATL/CLE stay identity on the number with honest QB drivers. Indoor no-travel games can stay near identity — logged.

Sign convention: negative Δ spread = away weaker (home relatively stronger). WAS is the visitor → Commanders OL hits move PHI spread more negative.

## What was not applied (and why)

| Factor | Why |
|--------|-----|
| Weather forecast | No KEI-read forecast source wired. Indoor logged. Do not invent. Gate B.1 when a real feed exists. |
| Ref crews | Data not ready. Stub only. |
| Short week / bye | Week 1 has no prior REG rest gap. |
| Bates (WAS TE3) | Not a key role. |
| Skill IR list | `injury_paths` on the pack is empty; no invented IR. |
| Double-count injury/travel | Skipped when already inside the frozen projection snapshot. |
| PLAY band rewrite | Unchanged. Tags still KEI vs market. |

## Tests

- `tests/test_nfl_kei_week1_reprice.py` — unit direction per factor; open-competition ≠ fake precision; W1 SoT smoke ≥1 (actually 9) Model ≠ KEI.
- Fair-lines fixture without `week` does not apply Gate B (identity preserved).

## After merge

- Human spot-check 4–6 games (WAS @ PHI, MIA @ LV, ATL @ PIT, NE @ SEA, CLE @ JAX, GB @ MIN).
- When 100k completes: publish research bundle; confirm ATL/MIA no longer dual-map.
- Optional Gate B.1: refs + stronger weather when data exists.
