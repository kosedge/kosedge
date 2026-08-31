# CFB Chapter 2 Phase 1B-0 — qb_situation construction (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH2_QB_SITUATION_BRIEF.md`  
**Artifact:** `data/ops/cfb-ch2-qb-situation-cap-20260831.json`  
**1A (#348):** TCU/HAW share `qb_score=80.4` / `qb_index=1.38` (clamp).  
**This PR:** **no** edits to `qb_situation.py`, clamp, compose weights, priors, KEI, or power sort.

---

## Formula (file:line) score → index → clamp 1.38

`compute_qb_situation_index` (`qb_situation.py:60–92`):

```text
talent_index = 1 + (qb_talent - 50) / 80                         # :75
class_mult   = QB_CLASS_OFFENSE_MULT[qb_class]                   # priors.py:154–160
cast_mult    = 1 + 0.11 * (supporting_cast - 50) / 50            # :77, QB_CAST_INDEX_SCALE
raw          = talent_index * class_mult * cast_mult             # :78
index        = clamp(raw, 0.62, 1.38)                            # :79–80, QB_SITUATION_INDEX_CLAMP
score        = clamp(50 + (index - 1) * 80, 0, 100)              # :81
```

**Identity at the ceiling:** when `index == 1.38`, `score = 50 + 0.38×80 = 80.4` exactly.  
Every capped team therefore prints the **same** `(1.38, 80.4)` — the score is the clamp’s image, not a separately authored “elite = 80.4” label.

Class multipliers (`priors.py:154–160`): incumbent **1.06**, portal **0.95**, open_competition **0.87**, true_freshman **0.79**, unknown **0.92**.

Supporting cast (`qb_situation.py:54–57`): `0.55*ol_support + 0.45*weapons_support`.

Wire-up: pack → optional expert override (`qb_situation_overrides.py`) → `build_qb_situation` (`:95–182`) → compose (`team_projection.py:102–128`).

---

## Inputs to qb_situation_score (recruiting? returning starter? transfer portal class?)

| Input                            | Role                                               | Source                                                                                                                                                                        |
| -------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `qb_class`                       | Multiplier on raw index                            | Pack + classify (`incumbent` / `portal` / `open_competition` / `true_freshman`) from ESPN starter flags / attempts; expert overlay may rewrite class                          |
| `qb_talent` (0–100)              | Dominant continuous driver                         | **Approximate** composite from **2025 pass attempts / yards / TDs** via `talent_from_qb_stats` in `scripts/cfb/package_real_roster_2026.py:355–362` — **not** recruiting rank |
| `ol_support` / `weapons_support` | Cast (±11% index)                                  | Packaged unit grades (often prior OL/skill)                                                                                                                                   |
| `experience_starts`              | Classification / notes                             | Proxy from roster packaging                                                                                                                                                   |
| Recruiting                       | **Not** a direct QB score input                    | Lives on roster layer, not `qb_situation`                                                                                                                                     |
| Returning starter                | Via `qb_class=incumbent` + starts ≥1               | ESPN “returning production starter” notes on TCU/HAW                                                                                                                          |
| Transfer portal                  | Via `qb_class=portal` (+2 talent bump in packager) |                                                                                                                                                                               |

Talent formula (packager):  
`base = 42 + min(28, attempts/18) + min(12, ypa*1.1) + min(10, tds*0.35)` (+2 if portal), clamp 35–96.  
**Volume-heavy:** large 2025 attempt counts push talent into the 70s–80s even for mid/G5 offenses.

---

## Every team with score==80.4 or index==1.38 in the 2026 pack

Power-board FBS teams present in the packaged universe: **125**.  
At clamp (`index=1.38` ⇒ `score=80.4`): **43 (34.4%)**.  
**All top-7** (OSU, ORE, MISS, MIA, IU, TAMU, ND) are at the cap.

### Cap table (required)

| team    | qb_score | qb_index | starter name if present  | returning? | transfer? | notes                                                   |
| ------- | -------: | -------: | ------------------------ | ---------- | --------- | ------------------------------------------------------- |
| OSU     |     80.4 |     1.38 | Julian Sayin             | Y          | N         | unc=1.577; talent=83.88; cast=70.54; incumbent; power#1 |
| ORE     |     80.4 |     1.38 | Dante Moore              | N          | Y         | unc=1.435; talent=86.41; cast=67.22; portal; #2         |
| MISS    |     80.4 |     1.38 | Trinidad Chambliss       | N          | Y         | unc=1.443; talent=86.15; cast=71.02; portal; #3         |
| MIA     |     80.4 |     1.38 | Darian Mensah            | N          | Y         | unc=1.493; talent=90.52; cast=69.69; portal; #4         |
| IU      |     80.4 |     1.38 | Josh Hoover              | Y          | N         | unc=1.546; talent=84.19; cast=59.92; incumbent; #5      |
| TAMU    |     80.4 |     1.38 | Marcel Reed              | Y          | N         | unc=1.524; talent=80.94; cast=66.81; incumbent; #6      |
| ND      |     80.4 |     1.38 | CJ Carr                  | Y          | N         | unc=1.463; talent=76.97; cast=64.52; incumbent; #7      |
| TEX     |     80.4 |     1.38 | Arch Manning             | Y          | N         | unc=1.560; talent=82.16; cast=72.63; #8                 |
| USC     |     80.4 |     1.38 | Jayden Maiava            | N          | Y         | unc=1.413; talent=84.92; cast=66.20; portal; #11        |
| WASH    |     80.4 |     1.38 | Demond Williams Jr.      | Y          | N         | unc=1.502; talent=79.94; cast=63.97; #12                |
| AUB     |     80.4 |     1.38 | Byrum Brown              | Y          | N         | unc=1.534; talent=80.93; cast=69.68; #13                |
| SMU     |     80.4 |     1.38 | Kevin Jennings           | Y          | N         | unc=1.571; talent=85.14; cast=63.55; #14                |
| ARI     |     80.4 |     1.38 | Noah Fifita              | Y          | N         | unc=1.556; talent=84.07; cast=63.36; #15                |
| PSU     |     80.4 |     1.38 | Rocco Becht              | Y          | N         | unc=1.444; talent=74.82; cast=67.94; #20                |
| BYU     |     80.4 |     1.38 | Bear Bachmeier           | Y          | N         | unc=1.453; talent=77.37; cast=59.59; #24                |
| NCSU    |     80.4 |     1.38 | CJ Bailey                | Y          | N         | unc=1.527; talent=81.41; cast=65.67; #27                |
| **TCU** | **80.4** | **1.38** | **Jaden Craig**          | **Y**      | **N**     | **unc=1.481; talent=78.86; cast=62.02; #28**            |
| ISU     |     80.4 |     1.38 | Jaylen Raynor            | Y          | N         | unc=1.550; talent=83.86; cast=62.34; #30                |
| ASU     |     80.4 |     1.38 | Cutter Boley             | Y          | N         | unc=1.390; talent=71.87; cast=63.59; #31                |
| SCAR    |     80.4 |     1.38 | LaNorris Sellers         | Y          | N         | unc=1.400; talent=71.98; cast=66.55; #33                |
| BAY     |     80.4 |     1.38 | DJ Lagway                | Y          | N         | unc=1.428; talent=73.71; cast=67.82; #35                |
| PITT    |     80.4 |     1.38 | Mason Heintschel         | Y          | N         | unc=1.403; talent=73.35; cast=61.17; #36                |
| KSU     |     80.4 |     1.38 | Avery Johnson            | Y          | N         | unc=1.427; talent=74.94; cast=62.00; #37                |
| CIN     |     80.4 |     1.38 | JC French IV             | Y          | N         | unc=1.478; talent=78.89; cast=61.25; #38                |
| DUKE    |     80.4 |     1.38 | Walker Eget              | Y          | N         | unc=1.472; talent=78.32; cast=61.77; #39                |
| NEB     |     80.4 |     1.38 | Anthony Colandrea        | N          | Y         | unc=1.408; talent=84.34; cast=66.75; portal; #40        |
| UCF     |     80.4 |     1.38 | Alonza Barnett III       | Y          | N         | unc=1.484; talent=78.95; cast=62.60; #46                |
| BOISE   |     80.4 |     1.38 | Maddux Madsen            | Y          | N         | unc=1.399; talent=73.58; cast=58.67; #47                |
| MD      |     80.4 |     1.38 | Malik Washington         | Y          | N         | unc=1.510; talent=81.12; cast=61.70; #48                |
| MINN    |     80.4 |     1.38 | Drake Lindsey            | Y          | N         | unc=1.438; talent=76.65; cast=57.97; #49                |
| CAL     |     80.4 |     1.38 | Jaron-Keawe Sagapolutele | Y          | N         | unc=1.539; talent=83.36; cast=61.25; #51                |
| WIS     |     80.4 |     1.38 | Colton Joseph            | Y          | N         | unc=1.434; talent=75.41; cast=62.19; #54                |
| UTSA    |     80.4 |     1.38 | Owen McCown              | N          | Y         | unc=1.383; talent=84.81; cast=56.68; portal; #55        |
| WSU     |     80.4 |     1.38 | Caden Pinnick            | Y          | N         | unc=1.489; talent=81.39; cast=54.08; #58                |
| TXST    |     80.4 |     1.38 | Brad Jackson             | Y          | N         | unc=1.458; talent=78.98; cast=54.56; #60                |
| **HAW** | **80.4** | **1.38** | **Micah Alejado**        | **Y**      | **N**     | **unc=1.502; talent=82.23; cast=54.68; #62**            |
| OHIO    |     80.4 |     1.38 | Matt Vezza               | Y          | N         | unc=1.428; talent=77.12; cast=52.71; #75                |
| DEL     |     80.4 |     1.38 | Nick Minicucci           | Y          | N         | unc=1.562; talent=85.96; cast=57.46; #79                |
| NMSU    |     80.4 |     1.38 | Trey Hedden              | Y          | N         | unc=1.471; talent=79.02; cast=58.47; #83                |
| WYO     |     80.4 |     1.38 | Tyler Hughes             | Y          | N         | unc=1.393; talent=74.43; cast=53.22; #86                |
| ORST    |     80.4 |     1.38 | Braden Atkinson          | Y          | N         | unc=1.528; talent=84.37; cast=53.84; #95                |
| OKST    |     80.4 |     1.38 | Drew Mestemaker          | Y          | N         | unc=1.583; talent=88.13; cast=55.24; #97                |
| NIU     |     80.4 |     1.38 | Taron Dickens            | Y          | N         | unc=1.494; talent=82.85; cast=49.59; #110               |

Starter names **are** present in the pack (ESPN QB1 identities). Cap class mix: **37 incumbent / 6 portal**.

Incumbent@cast≈50 hits clamp near **talent ≥ 74.2**; portal@cast≈50 near **talent ≥ 86.2**. Volume-heavy talent + incumbent mult puts a wide band of FBS QBs over the ceiling.

---

## Is 80.4 a continuous rating or a tier bucket?

**Both, stacked:**

1. **Upstream:** continuous function of talent × class × cast (`raw` differs: TCU 1.481 vs HAW 1.502 vs OSU 1.577).
2. **Downstream:** hard clamp collapses every `raw ≥ 1.38` into one output pair `(1.38, 80.4)`.

So **80.4 is a discrete ceiling tier** — the published face of the clamp — not a hand-labeled “elite QB” enum. One-third of the power board sits in that bucket. Near-cap continuous values still exist (PUR 1.369, ILL 1.366, …) just below the cut.

---

## Why TCU == HAW numerically (same inputs or same tier?)

**Same tier (clamp), different inputs.**

|                       |             TCU |             HAW |
| --------------------- | --------------: | --------------: |
| starter               |     Jaden Craig |   Micah Alejado |
| class                 |       incumbent |       incumbent |
| qb_talent             |           78.86 |           82.23 |
| supporting_cast       |           62.02 |           54.68 |
| unclamped raw         |       **1.481** |       **1.502** |
| published index/score | **1.38 / 80.4** | **1.38 / 80.4** |

Both are returning volume starters (TCU 338 att / HAW 430 att → high approximate talent). Neither is a copy-paste of the other payload; both independently clear the ceiling, so compose sees identical QB levers. That is **schema compression**, not a Hawaii-only data bug.

---

## OSU / other top-7 at the cap? (if yes, haircutting the cap is forbidden)

**Yes — entire top-7 is at 1.38 / 80.4.** OSU unclamped **1.577** (Julian Sayin, incumbent, talent 83.88, cast 70.54).

**Haircutting `QB_SITUATION_INDEX_CLAMP` (or scoring everyone at 80.4 down together) is forbidden** as a 1C patch: it would move OSU/ORE/MISS/… with TCU/HAW. Phase 1A paper sim already showed QB 0.9 shuffles top-7.

---

## Phase 1C allowlist — what _could_ change later without a team if

Allowed to **audit / redesign** (separate PR, with top-7 + BALL@OSU + TCU/HAW canaries):

1. **`talent_from_qb_stats`** — reduce volume dominance; add opponent/context or efficiency grain so G5 attempt volume ≠ P4 offense prior.
2. **Class / cast response** — retune `QB_CLASS_OFFENSE_MULT` or cast scale so incumbent+high-volume does not saturate.
3. **Soft ceiling / tapered response** above ~1.25 so raw 1.48 ≠ raw 1.58 in published score (continuous elite, not flat 80.4).
4. **Score↔index map** after a softer index (still global).

Still **forbidden** in 1C unless separately approved: `if team == "TCU"|"Hawaii"`, cut `WEIGHT_QB` / `QB_INDEX_BLEND`, set `MATCHUP_RESPONSE=1.00`, hard-cap haircut alone, Utah beauty-pass, NFL/CBB/MLB trees.

---

## Blocker if 80.4 is a designed elite tier and TCU/HAW belong there by construction

**Blocker (construction, not bad Hawaii row):** under current rules, returning high-attempt incumbents **belong** at the clamp by design. TCU and Hawaiʻi are correctly classified as that schema class. Demoting only them is a team if. The honest next pass is **rebuilding the score / talent / ceiling response** so “elite” is continuous and not shared by 34% of the board — not `if hawaii: 50`.

---

## Verdict line (operator gate for 1C)

**Schema clamp tier (compression) — not a broken TCU/HAW input.**  
`80.4` = image of `index=1.38`; **43/125 (34%)** of power-board teams sit there, including **all top-7**. Next fit, if any: score-function / talent / soft-ceiling redesign — never a team if, never clamp haircut alone, never `MATCHUP_RESPONSE=1.00`.

---

## Forbidden check

No writes to `qb_situation.py` logic, `QB_SITUATION_INDEX_CLAMP`, compose weights, priors SD, KEI, or power sort in this PR.
