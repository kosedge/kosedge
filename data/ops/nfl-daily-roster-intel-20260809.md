# Daily Roster + Injury Intel → SoT → Engine — 2026-08-09

Branch: `feat/nfl-daily-roster-intel-20260809` → `deploy-vercel`  
Depends on: Roster SoT (#160 merged) — engine reads packaged depth exclusively.

## Path (reinforced)

```
news / camp intel → expert note (cited) → depth SoT pack → engine → board / lines
```

| Artifact | Path |
|----------|------|
| **Depth / roster SoT** | `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json` |
| **Daily checklist** | `scripts/nfl/daily_roster_injury_intel_checklist.md` |
| **Helper** | `scripts/nfl/run_daily_roster_injury_intel.sh` (`--verify` / `--sim`) |
| **Re-sim bundle** | `data/ops/nfl-preseason-sim-2026-daily-intel-20260809` |

**Engine read path:** `load_packaged_depth_chart` → `build_packaged_real_universe` / DB loader. When the pack exists it is the **only** player→team + skill depth source (DB weekly/official ignored). No dual maps. No single-player simulator patches.

## Verified WAS flashpoints (run-time 2026-08-09)

| Player | Finding | Sources |
|--------|---------|---------|
| **Laremy Tunsil (LT)** | Torn triceps (practice 2026-08-08); surgery; expected to miss **most of 2026**. | [AP/Sportsnet](https://www.sportsnet.ca/nfl/article/report-commanders-tunsil-expected-to-miss-most-of-2026-with-torn-triceps/), [Garafolo / FantasyPros](https://www.fantasypros.com/nfl/news/601310/laremy-tunsil-torn-triceps-to-undergo-surgery-miss-majority-season.php) |
| **Brandon Coleman → LT** | Camp plan: Coleman slides back to LT; LG competition opens. | [Nicki Jhabvala / SI](https://www.si.com/nfl/commanders/onsi/brandon-coleman-left-tackle-laremy-tunsil-injury-commanders), [Commanders Wire](https://commanderswire.usatoday.com/story/sports/nfl/commanders/2026/08/09/commanders-laremy-tunsil-injury-replacement/91232445007/) |
| **Nick Allegretti (C)** | Calf; missing extended camp; Quinn ~another week (2026-08-08/09). W1 = **unknown / monitor**. | [Commanders Wire OL](https://commanderswire.usatoday.com/story/sports/nfl/commanders/2026/08/09/commanders-offensive-line-dealing-two-injuries/91230469007/), [Quinn update](https://commanderswire.usatoday.com/story/sports/nfl/commanders/2026/08/08/commanders-dan-quinn-injury-update-john-bates-nick-allegretti/91226994007/) |
| **John Bates (TE)** | Hamstring; Quinn “couple of weeks” (early Aug, still out 08/08). W1 = **unknown / monitor** (no invented IR). | [Commanders.com notebook](https://www.commanders.com/news/commanders-training-camp-notebook-treylon-burks-back-together-saturday), [Quinn update](https://commanderswire.usatoday.com/story/sports/nfl/commanders/2026/08/08/commanders-dan-quinn-injury-update-john-bates-nick-allegretti/91226994007/) |
| **Trey Amos (CB)** | Activated off PUP **2026-08-07** (official). No confirmed new multi-week OUT at verify — **monitor**. | [Commanders.com](https://www.commanders.com/news/trey-amos-dorance-armstrong-tress-way-activated) |
| **Armstrong / Wise** | Armstrong off PUP; **Wise remains on PUP** (quad) — corrected vs prior “both off” rumor. | [PFT](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/commanders-activate-tress-way-dorance-armstrong-trey-amos) |
| **Jayden Daniels / Diggs** | Daniels healthy 1st team; Diggs signed + practiced 2026-08-07 → SoT WR2. | [Commanders Diggs signing](https://www.commanders.com/news/commanders-sign-wr-stefon-diggs) |

## Before / after — WAS skill + OL roles

### Skill depth (engine usage SoT)

| Slot | Before (#160 pack) | After (2026-08-09) |
|------|--------------------|--------------------|
| WR1 | Terry McLaurin | Terry McLaurin |
| WR2 | Antonio Williams | **Stefon Diggs** |
| WR3 | Luke McCaffrey | Antonio Williams |
| TE1 | Chig Okonkwo | Chig Okonkwo |
| TE2 | John Bates | **Ben Sinnott** |
| TE3 | Ben Sinnott | **John Bates** (`injury_status=out`, window unknown/monitor) |
| QB1 | Jayden Daniels | Jayden Daniels (`active`) |

### OL roles (`ol_roles` — tracking SoT, not skill usage rows)

| Role | Player | Status |
|------|--------|--------|
| LT1 starter | **Brandon Coleman** | active (slide from LG) |
| LT2 backup | Andrew Wylie | active |
| LT out | **Laremy Tunsil** | out — majority of 2026 (surgery) |
| LG | Chris Paul | starter_competition (opens with Coleman→LT) |
| C1 | **Nick Allegretti** | out — camp calf; W1 unknown/monitor |
| C2 filling | Julian Good-Jones | active |
| RT1 | Josh Conerly Jr. | active (stays RT) |

## OL → efficiency (documented, not magical)

Pack `camp_intel.ol_efficiency_hooks`:

- Skill usage path still QB/RB/WR/TE only from depth rows.
- Team-strength hook exists: `TeamStrengthState.injury_delta_offense` / `drivers.stubs.injury_at_time_depth` (currently **`stub_not_applied`** on packaged backbone).
- **No invented OL→EPA magnitude** this pass. Tunsil + Allegretti stack is a **KEI attention / Edge Board risk flag** until that stub is wired from `ol_roles`.
- Direction if/when wired: weaker blindside + center instability → pass protection / pass EPA pressure; rush mixed.

`injury_paths[]` left **empty** — Bates/Allegretti windows are camp-scale / unknown for W1; we do not invent multi-week IR lengths. Depth reorder carries TE usage (Sinnott↑ / Bates↓).

## Propagate — re-sim

Bundle: `data/ops/nfl-preseason-sim-2026-daily-intel-20260809`  
(`--force-packaged`, 5k team / 200 player, seed 20260807)

| Check | Result |
|-------|--------|
| Roster source | `packaged_nflverse_depth_2026` + `daily_intel_as_of=2026-08-09` |
| Diggs | WAS WR2 in universe + player totals (~390 rec yds mean) |
| Bates / Sinnott | Bates TE3 OUT metadata; Sinnott TE2 (~+167 rec yds vs prior) |
| Σ mean wins | **272.0** OK |
| Pass/rush team skill yard pools (WAS sum) | Conserved (~3136 / ~2198 / ~2885) |

### WAS team deltas vs roster-SoT baseline (`…-roster-sot-20260809`)

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| Team W/L mean wins (5k) | 6.613 | 6.606 | **−0.007** |
| Player-path mean wins (200) | 6.24 | 6.535 | **+0.30** (small-N noise) |
| Analytic expected wins | 7.169 | 7.169 | 0 (strength priors unchanged — OL stub) |

Team W/L barely moves because **OL strength shock was not invented**. Usage redistributed inside WAS.

### High-impact usage (rec yards mean)

| Player | Before | After | Δ |
|--------|-------:|------:|--:|
| Stefon Diggs | — | 389.9 | **+389.9** |
| Antonio Williams | 402.0 | 179.3 | −222.7 |
| Luke McCaffrey | 177.4 | (off pack top-3) | −177.4 |
| Ben Sinnott | 206.5 | 373.5 | **+167.1** |
| John Bates | 370.2 | 212.8 | −157.4 |
| Chig Okonkwo | 635.2 | 637.0 | +1.7 |
| Terry McLaurin | 697.9 | 694.4 | −3.6 |

## KEI / board attention

1. **WAS OL stack** — Tunsil season-long OUT + Allegretti camp OUT → protection / interior risk; flag until `injury_at_time_depth` consumes `ol_roles`.
2. **WAS TE** — Okonkwo/Sinnott receiving path while Bates OUT/monitor.
3. **WAS WR** — Diggs WR2 with McLaurin; Williams WR3; McCaffrey competition below pack top-3.
4. **Amos** — active off PUP; monitor only.
5. **Kyler-class errors** — still impossible while pack is exclusive (#160).

## Conservation

- Team mean wins sum = **272.0** (`team_mean_wins_sum_ok: true`)
- Locked pass-pool / alpha / coherence **not** touched
- WAS skill pass/rush/rec yard sums conserved under depth reallocation

## Tomorrow

```bash
bash scripts/nfl/run_daily_roster_injury_intel.sh
# edit SoT pack from checklist
bash scripts/nfl/run_daily_roster_injury_intel.sh --verify
bash scripts/nfl/run_daily_roster_injury_intel.sh --sim
# write data/ops/nfl-daily-roster-intel-YYYYMMDD.md → PR to deploy-vercel
```
