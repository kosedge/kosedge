# CFB Edge Board Week 1 — Scorecard

**Branch:** `cursor/cfb-edgeboard-week1-slate-odds-3ca1`  
**Engine (untouched):** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31` · seed `20260831`  
**Pass:** Phase 1 allowlist only — slate close + Week 1 desk defaults + honest Odds join path  
**KEI rebuild:** **No** (BALL@OSU KEI −42.2 left as cupcake saturation exhibit)

| Check | After | Notes |
|---|---|---|
| Slate `as_of` | **2026-08-31** | `cfb-official-slate-v2-dual-20260831` |
| Week 0 rows | **finals** | UNC 15–10 TCU, SJSU 26–42 USC, NCSU 8–34 UVA, HAW 27–37 STAN, NMSU 17–34 FSU, MEM 27–21 UNLV |
| Default week (Slate) | **Week 1** | `parseOfficialSlateWeek` prefers 1 |
| Default week (Edge Board) | **Week 1** | missing/`?week=1` → 1; `?week=0` finals tab |
| CFB Overview → Edge Board | `/edge-board/cfb?week=1` | nav + desk cards updated |
| Week-tab counts | **fixed** | `week0Count` / `week1Count` (was swapped) |
| Engine stamp | `v0.15-power-sot` | unchanged |
| KEI on Week 1 FBS | yes | bundled pack; BALL@OSU −42.2 unchanged |
| Open column | feed or `—` | existing `odds-api.ts` · key `americanfootball_ncaaf` |
| Current/Best | feed or `—` | trusted-market guard unchanged |
| Edge/Tag | only KEI + trusted Best | PASS / LEAN≥2.5 / PLAY≥4.0; no book ⇒ no edge |
| UNC–TCU labeled | **Week 0 final** | Project Game slate lookup; bare default week 0 |
| Power top-7 | unchanged | not touched |
| Utah blocker | still present | `docs/CFB_ENGINE_BLOCKER.md` |
| NFL/CBB/MLB product diffs | none | CFB desk + shared odds key already existed |
| Publisher | no Aug 17 stamp | `as_of` from engine schedule |

## Fail conditions checked

| Condition | Result |
|---|---|
| New odds client / scraped lines | **No** |
| Trusted-market loosened | **No** |
| `apply_cfb_kei` / power / shock / Utah | **No** |
| PLAY on cupcakes with no book | **No** (edge requires trusted Best) |
| Still shipping `as_of=2026-08-17` on slate | **No** |
| Loading `kei_lines_cfb.json` as SoT | **No** (bundled `cfb-kei-w0-w1-2026.json`) |

## Fire-on (operator)

Desk can be shown. Not a play card. PASS unless \|KEI − Best\| ≥ 4.0 **and** a named driver. OSU −42 vs book −35 is calibration, not a PLAY. No market ⇒ dashes.
