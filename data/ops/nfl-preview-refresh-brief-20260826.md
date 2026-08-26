# NFL full preview refresh brief — 2026-08-26

**Assignment:** Full rewrite of all 32 season previews (not Monday “updated” appendices). Paint season outlook; verify numbers; deep beat research.

**Date stamp on every piece:** August 26, 2026  
**Market fact-check:** August 26, 2026 · DraftKings via RotoWire · Editor Riley Nash  
**Model SoT:** `nfl-preseason-sim-2026-20260822T013711Z` (N=100000) `expected_wins`  
**Live board (DK / RotoWire, Aug 2026 confirmed):**

| Team | Market | O/U juice | Model E[W] | Δ (M−mkt) | Default lean guidance |
|------|-------:|-----------|----------:|----------:|------------------------|
| LAR | 11.5 | -125 / +105 | 11.07 | −0.43 | Pass |
| BAL | 11.5 | +115 / -140 | 8.98 | −2.52 | Pass (Model↔market conflict) |
| BUF | 10.5 | -120 / +100 | 10.26 | −0.24 | Pass |
| SEA | 10.5 | -115 / -105 | 10.81 | +0.31 | Pass |
| DET | 10.5 | -110 / -112 | 10.69 | +0.19 | Pass |
| PHI | 10.5 | +105 / -125 | 10.35 | −0.15 | Pass |
| KC | 10.5 | +115 / -140 | 9.31 | −1.19 | Pass (Model↔market) |
| SF | 10.5 | +125 / -145 | 8.53 | −1.97 | Pass (Model↔market) |
| NE | 10.5 | +125 / -150 | 9.98 | −0.52 | Pass |
| GB | 9.5 | -140 / +115 | 9.33 | −0.17 | Pass |
| HOU | 9.5 | -125 / +105 | 10.34 | +0.84 | Soft Over only if juice OK; else Pass; conf ≤2 |
| DEN | 9.5 | -115 / -105 | 10.51 | +1.01 | Soft Over if research agrees; conf ≤2 |
| LAC | 9.5 | -130 / +110 | 8.48 | −1.02 | Pass / soft Under scrutiny (Biadasz ACL) |
| CHI | 9.5 | +100 / -120 | 8.34 | −1.16 | Pass (Model↔market) |
| CIN | 9.5 | -140 / +115 | 7.21 | −2.29 | Pass (Model↔market) |
| DAL | 9.5 | +115 / -140 | 7.10 | −2.40 | Pass (Model↔market) |
| JAX | 8.5 | +110 / -130 | 9.77 | +1.27 | Soft Over if juice OK; conf ≤2 |
| TB | 8.5 | -125 / +105 | 8.37 | −0.13 | Pass |
| PIT | 8.5 | +100 / -120 | 8.16 | −0.34 | Pass |
| MIN | 8.5 | -110 / -110 | 8.38 | −0.12 | Pass |
| NYG | 7.5 | -115 / -105 | 7.03 | −0.47 | Pass |
| NO | 7.5 | -120 / +100 | 8.96 | +1.46 | Soft Over if juice OK; conf ≤2 |
| CAR | 7.5 | +110 / -130 | 6.46 | −1.04 | Pass / soft Under scrutiny |
| WAS | 7.5 | -120 / +100 | 6.31 | −1.19 | Pass / soft Under (injury cluster) |
| IND | 7.5 | -130 / +110 | 10.29 | +2.79 | Pass (Model↔market conflict — do not force Over) |
| TEN | 6.5 | -110 / -110 | 5.88 | −0.62 | Pass |
| ATL | 6.5 | -115 / -105 | 9.03 | +2.53 | Pass (QB fog / Model↔market until Week 1 starter clear) |
| CLE | 6.5 | +105 / -120 | 8.59 | +2.09 | Pass (Watson named; Model↔market — show both) |
| LV | 5.5 | -146 / +120 | 6.07 | +0.57 | Pass (thin; Jeanty ankle) |
| NYJ | 5.5 | -120 / +100 | 4.73 | −0.77 | Pass / soft Under scrutiny |
| ARI | 4.5 | +125 / -150 | 6.55 | +2.05 | Pass (Model↔market; basement board) |
| MIA | 4.5 | -110 / -110 | 6.14 | +1.64 | Pass (Model↔market; rebuild) |

## Edge Threshold Discipline (mandatory)

- |fair − market| ≤ ~0.5 win → **Pass**
- Never dress Pass as soft Over/Under
- Material Model↔market conflict → **Pass** (present both)
- Confidence never 3+ on thin edges
- Fair number in Handicapper’s Note = Model E[wins] (2 decimals)

## Material camp updates since prior desk (must be in relevant previews)

- **CLE:** Monken named Deshaun Watson Week 1 starter over Sanders (Aug 24). Not week-to-week. Road opener @ JAX.
- **ATL:** Penix cleared 11-on-11 (Aug 22); first full-team work Aug 24; still competing with Tua — Week 1 starter **unset**.
- **BAL:** Danny Pinter season-ending torn patella; center = Pocic vs Gwyn. Madubuike Week 1 uncertain (neck ramp).
- **HOU:** Jayden Higgins ACL — season over. WR2 open (Dell/Noel/Hutchinson).
- **WAS:** OL cluster — Tunsil long-term; Newton pec surgery; Allegretti calf; White hamstring; Mariota MCL (out rest of preseason).
- **NYG:** Calvin Austin III serious knee (Aug 25, Schefter) — slot room thins.
- **LAC:** Tyler Biadasz ACL season-ending; Jake Slaughter likely center path.
- **LV:** Ashton Jeanty ankle sprain (Aug 23) — Week 1 uncertain.
- **MIN:** Murray remains named QB1; McCarthy left Ravens preseason with injury; Adams season-ending quad.
- **CAR:** Hubbard on track Week 1 (hamstring); committee with Brooks; Legette boot.
- **CHI:** Kyle Monangai hyperextended knee — multi-week / Week 1 doubt.

## Output path

Overwrite: `content/writers/season-previews-2026/{TEAM}.md`

## Required header block

```
# {Team} 2026 Season Preview

**By {Writer}** · Kos Edge Analytics · {Division} desk  
**Angle:** {one-line hook}  
**Date:** August 26, 2026
**Market fact-check:** August 26, 2026 · DraftKings via RotoWire · Editor Riley Nash  
**Model SoT:** nfl-preseason-sim-2026-20260822T013711Z (N=100000) expected_wins
**Market (DK / RotoWire, Aug 2026 fact-check):** Win total **X.5** (O juice / U juice)
**Sources (beat desk):** {name (outlet); …}
```

## Structure

1. Strong lede framing the market question / season outlook  
2. Camp / roster / injury reality (researched, dated)  
3. Win-total math vs Model SoT + juice  
4. Division / schedule context  
5. Betting Guide bullets  
6. Handicapper’s Note (Fair = Model E[W]; Market; Lean; Confidence; Key risk)  
7. Required disclaimer  

**Length:** 900–1,600 words. Full rewrite — no “Monday desk refresh” appendix.  
**Sources:** Use `python scripts/writers/beat-lookup.py --team XYZ` + WebSearch/WebFetch. No invented quotes. No X profile links in product.  
**Voice:** style-bible.md — no hype, no locks, Pass when thin.
