# NFL fantasy rank vs ADP diagnosis — 2026-08-13

Half-PPR primary. ADP: FantasyPros partners snapshot (`apps/web/data/fantasy/adp-fantasypros-2026-half_ppr.json`, updated 8/05, 339 players). Δ = ModelRank − ADP (negative = model earlier than market). Live desk Value Δ is the opposite sign (ADP − ModelRank).

**Live Railway `/nfl/fantasy/draft-rankings` returns 0 rows.** Production `/pro/nfl/fantasy` uses `preseason-fallback` from the web launch pointer. Until #224 is on production, that pointer is still `nfl-preseason-sim-2026-20260809T165350Z`. This note diagnoses **both** the live pointer and the #224 bundle `nfl-preseason-sim-2026-20260813T132801Z`.

## Smell test

| Board | Top-50 matched | \|Δ\|≥8 | \|Δ\|≥10 | median \|Δ\| |
|---|---:|---:|---:|---:|
| Live pointer 20260809 | 50 | 38 | 36 | 20.0 |
| Publish bundle 20260813 | 50 | 40 | 38 | 26.2 |

**Systemic, not sharp edges.** 15+ of top-50 at \|Δ\|≥10 with no injury/role story. Republishing SoT 100k did **not** fix rank vs ADP (median got slightly worse).

## Most broken names on the live Half-PPR desk

These are what the production board actually shows (VOR order, no ADP in the sort):

| Player | Model # | ADP | Value Δ (desk) | Why it looks broken |
|---|---:|---:|---:|---|
| Zach Charbonnet | 4 | ~135 | +129 | SEA committee RB with 1,423 rush — treated as RB1 |
| Jacory Croskey-Merritt | 19 | ~111 | +91 | WAS committee / camp ADP |
| Rhamondre Stevenson | 15 | ~76 | +60 | even rush split (~1,400) |
| D'Andre Swift | 5 | ~54 | +49 | CHI committee pile |
| Bhayshul Tuten | 12 | ~56 | +44 | JAX committee / rookie workload |
| David Montgomery | 11 | ~51 | +41 | **HOU-RB1 label** (identity) + 1,318 rush |
| Brian Thomas Jr. | 22 | ~73 | +51 | WR volume vs ADP |
| Marvin Harrison Jr. | 24 | ~78 | +54 | ARI pass volume |
| Jahmyr Gibbs | 17 | ~1 | −16 | DET split; Montgomery/HOU identity steals the contrast |
| Puka Nacua | 25 | ~4 | −21 | model WR8 vs ADP 4 |
| Jaxon Smith-Njigba | 20 | ~6 | −14 | SEA identity OK; not top-tier WR |
| Mike Gesicki | 47 | ~251 | +204 | TE VOR pile (expert sleeper copy) |

## Systemic drivers (not one-off vibes)

1. **Rank sort key is pure model VOR.** `rankSeasonFantasyPlayers` / `nfl_fantasy_draft_rankings` sort overall by VOR from raw format points. ADP is not in the sort. Value-aware recs (`value-aware-recs.ts`, `MAX_RECOMMEND_RANK_DELTA = 12`) apply on **Mock / Builder only**.
2. **Display vs order.** Model pts / Model # / ADP / Value Δ are honest. The *order* of the board was Model #, so a 1,400-yard committee RB prints as overall #4.
3. **Season-total rush pile.** League rush is locked at 64,000. Soft RB priors split that too evenly — 10+ RBs at ~1,300–1,500 rush yards. That is projection **shape**, not 4k-QB hangover (only 7–8 QBs ≥ 4,000 pass yards on these bundles).
4. **TE replacement / VOR.** Gesicki / Engram / Parkinson land overall ~45–70 because TE replacement is cheap; ADP still treats them as streamers.
5. **ADP match is not rank 999.** Unmatched ADP → Value Δ `—` (null). Cross-format matches display ADP but leave Value Δ blank. Coverage on the live desk: 237/250 matched, 204 high-confidence.
6. **Identity leftover.** David Montgomery is `HOU-RB1-DavidMontgomery` in both 20260809 and 20260813 CSVs. 2025 owned depth had him DET. Not JSN-wrong-team; still a silent wrong-team production risk for DET/HOU.

## Classification of top-50 \|Δ\|≥8 (20260813 bundle)

1 Data/identity · 35 Projection shape · 4 Market · 0 Intentional thesis

**Intentional thesis count: 0.** None of these gaps were labeled as a desk take. They are silent noise from sort policy + committee shape.

### Top 50 (publish bundle, Half-PPR, Model VOR order)

| Player | Pos | ModelRank | ADP | Δ | Model season yards/pts | Notes |
|---|---|---:|---:|---:|---|---|
| Christian McCaffrey | RB | 1 | 5.0 | -4.0 | 1452 rush; 434 rec; 318 pts | committee/even rush split (1452 rush) |
| Josh Jacobs | RB | 2 | 28.3 | -26.3 | 1407 rush; 360 rec; 295 pts | committee/even rush split (1407 rush) |
| James Cook III | RB | 3 | 9.7 | -6.7 | 1505 rush; 316 rec; 294 pts | committee/even rush split (1505 rush) |
| Ja'Marr Chase | WR | 4 | 3.0 | +1.0 | 1716 rec; 314 pts | 1716 rec / 0 rush / 0 pass |
| Saquon Barkley | RB | 5 | 13.7 | -8.7 | 1464 rush; 306 rec; 292 pts | committee/even rush split (1464 rush) |
| Bijan Robinson | RB | 6 | 1.7 | +4.3 | 1417 rush; 359 rec; 289 pts | committee/even rush split (1417 rush) |
| CeeDee Lamb | WR | 7 | 11.3 | -4.3 | 1676 rec; 310 pts | 1676 rec / 0 rush / 0 pass |
| Zach Charbonnet | RB | 8 | 134.7 | -126.7 | 1425 rush; 339 rec; 289 pts | committee/even rush split (1425 rush); SEA RB2/committee treated like workhorse |
| D'Andre Swift | RB | 9 | 54.0 | -45.0 | 1438 rush; 326 rec; 288 pts | committee/even rush split (1438 rush) |
| Derrick Henry | RB | 10 | 21.3 | -11.3 | 1500 rush; 262 rec; 285 pts | committee/even rush split (1500 rush) |
| J.K. Dobbins | RB | 11 | 92.0 | -81.0 | 1386 rush; 369 rec; 284 pts | committee/even rush split (1386 rush) |
| Cam Skattebo | RB | 12 | 37.3 | -25.3 | 1434 rush; 282 rec; 271 pts | committee/even rush split (1434 rush) |
| Marvin Harrison Jr. | WR | 13 | 78.0 | -65.0 | 1577 rec; 291 pts | ARI pass volume high vs ADP 78 |
| Bhayshul Tuten | RB | 14 | 56.0 | -42.0 | 1404 rush; 293 rec; 269 pts | committee/even rush split (1404 rush) |
| Bucky Irving | RB | 15 | 44.3 | -29.3 | 1389 rush; 285 rec; 265 pts | committee/even rush split (1389 rush) |
| Rhamondre Stevenson | RB | 16 | 76.0 | -60.0 | 1406 rush; 252 rec; 258 pts | committee/even rush split (1406 rush) |
| Jacory Croskey-Merritt | RB | 17 | 110.7 | -93.7 | 1392 rush; 233 rec; 252 pts | committee/even rush split (1392 rush); WAS committee / camp ADP lag |
| Jahmyr Gibbs | RB | 18 | 1.3 | +16.7 | 956 rush; 478 rec; 248 pts | 478 rec / 956 rush / 0 pass |
| Rashee Rice | WR | 19 | 28.7 | -9.7 | 1427 rec; 267 pts | 1427 rec / 0 rush / 0 pass |
| Javonte Williams | RB | 20 | 31.0 | -11.0 | 976 rush; 445 rec; 246 pts | 445 rec / 976 rush / 0 pass |
| David Montgomery | RB | 21 | 51.3 | -30.3 | 1084 rush; 375 rec; 244 pts | labeled HOU-RB1; 2025 depth was DET — identity to confirm vs SoT |
| Emeka Egbuka | WR | 22 | 41.7 | -19.7 | 1409 rec; 259 pts | 1409 rec / 0 rush / 0 pass |
| Jonathan Taylor | RB | 23 | 6.7 | +16.3 | 1023 rush; 378 rec; 235 pts | 378 rec / 1023 rush / 0 pass |
| Brian Thomas Jr. | WR | 24 | 72.7 | -48.7 | 1375 rec; 253 pts | 1375 rec / 0 rush / 0 pass |
| Joe Burrow | QB | 25 | 51.7 | -26.7 | 4857 pass; 158 rush; 375 pts | 4857 pass yds; ADP late is 1QB-normal |
| Jeremiyah Love | RB | 26 | 25.0 | +1.0 | 802 rush; 486 rec; 229 pts | 486 rec / 802 rush / 0 pass |
| Omarion Hampton | RB | 27 | 15.3 | +11.7 | 878 rush; 429 rec; 227 pts | 429 rec / 878 rush / 0 pass |
| Mike Evans | WR | 28 | 60.3 | -32.3 | 1336 rec; 248 pts | 1336 rec / 0 rush / 0 pass |
| Malik Nabers | WR | 29 | 35.0 | -6.0 | 1324 rec; 247 pts | 1324 rec / 0 rush / 0 pass |
| Puka Nacua | WR | 30 | 4.0 | +26.0 | 1326 rec; 246 pts | 1326 rec / 0 rush / 0 pass |
| Carnell Tate | WR | 31 | 71.7 | -40.7 | 1319 rec; 244 pts | 1319 rec / 0 rush / 0 pass |
| Alec Pierce | WR | 32 | 85.0 | -53.0 | 1324 rec; 243 pts | 1324 rec / 0 rush / 0 pass |
| Chris Olave | WR | 33 | 29.0 | +4.0 | 1322 rec; 243 pts | 1322 rec / 0 rush / 0 pass |
| Nico Collins | WR | 34 | 23.0 | +11.0 | 1312 rec; 242 pts | 1312 rec / 0 rush / 0 pass |
| Dak Prescott | QB | 35 | 83.0 | -48.0 | 4645 pass; 134 rush; 363 pts | 4645 pass yds; ADP late is 1QB-normal |
| Travis Etienne Jr. | RB | 36 | 40.0 | -4.0 | 858 rush; 407 rec; 219 pts | 407 rec / 858 rush / 0 pass |
| Jaxon Smith-Njigba | WR | 37 | 6.3 | +30.7 | 1276 rec; 239 pts | SEA identity OK; jsn_top_tier gate wants WR rank ≤8 |
| Ladd McConkey | WR | 38 | 45.3 | -7.3 | 1297 rec; 238 pts | 1297 rec / 0 rush / 0 pass |
| Matthew Stafford | QB | 39 | 107.7 | -68.7 | 4452 pass; 179 rush; 361 pts | 4452 pass yds; ADP late is 1QB-normal |
| Ashton Jeanty | RB | 40 | 11.0 | +29.0 | 883 rush; 375 rec; 215 pts | 375 rec / 883 rush / 0 pass |
| Courtland Sutton | WR | 41 | 87.7 | -46.7 | 1291 rec; 235 pts | 1291 rec / 0 rush / 0 pass |
| Jacoby Brissett | QB | 42 | 200.5 | -158.5 | 4612 pass; 95 rush; 356 pts | 4612 pass yds; ADP late is 1QB-normal |
| Kenneth Walker III | RB | 43 | 19.3 | +23.7 | 795 rush; 407 rec; 212 pts | 407 rec / 795 rush / 0 pass |
| Patrick Mahomes | QB | 44 | 100.3 | -56.3 | 4394 pass; 142 rush; 353 pts | 4394 pass yds; ADP late is 1QB-normal |
| Breece Hall | RB | 45 | 33.0 | +12.0 | 1003 rush; 273 rec; 209 pts | 273 rec / 1003 rush / 0 pass |
| Mike Gesicki | TE | 46 | 251.0 | -205.0 | 798 rec; 160 pts | TE VOR pile — mid TE volume vs replacement |
| Kyren Williams | RB | 47 | 29.0 | +18.0 | 806 rush; 382 rec; 206 pts | 382 rec / 806 rush / 0 pass |
| Rome Odunze | WR | 48 | 64.3 | -16.3 | 1226 rec; 225 pts | 1226 rec / 0 rush / 0 pass |
| DK Metcalf | WR | 49 | 85.0 | -36.0 | 1205 rec; 223 pts | 1205 rec / 0 rush / 0 pass |
| De'Von Achane | RB | 50 | 13.3 | +36.7 | 834 rush; 336 rec; 199 pts | 336 rec / 834 rush / 0 pass |

### Worst 15 \|Δ\| in Model top 80 (publish bundle)

| Player | Pos | ModelRank | ADP | Δ | Model season yards/pts | Notes |
|---|---|---:|---:|---:|---|---|
| Mike Gesicki | TE | 46 | 251.0 | -205.0 | 798 rec; 160 pts | TE VOR pile — mid TE volume vs replacement |
| Evan Engram | TE | 64 | 247.0 | -183.0 | 694 rec; 138 pts | TE VOR pile — mid TE volume vs replacement |
| Colby Parkinson | TE | 67 | 247.5 | -180.5 | 663 rec; 136 pts | TE VOR pile — mid TE volume vs replacement |
| Jacoby Brissett | QB | 42 | 200.5 | -158.5 | 4612 pass; 95 rush; 356 pts | 4612 pass yds; ADP late is 1QB-normal |
| Tre Tucker | WR | 61 | 212.0 | -151.0 | 1134 rec; 210 pts | 1134 rec / 0 rush / 0 pass |
| Zach Charbonnet | RB | 8 | 134.7 | -126.7 | 1425 rush; 339 rec; 289 pts | committee/even rush split (1425 rush); SEA RB2/committee treated like workhorse |
| Jerry Jeudy | WR | 59 | 178.0 | -119.0 | 1138 rec; 211 pts | 1138 rec / 0 rush / 0 pass |
| Daniel Jones | QB | 75 | 175.3 | -100.3 | 3966 pass; 183 rush; 317 pts | 3966 pass yds; ADP late is 1QB-normal |
| Jacory Croskey-Merritt | RB | 17 | 110.7 | -93.7 | 1392 rush; 233 rec; 252 pts | committee/even rush split (1392 rush); WAS committee / camp ADP lag |
| J.K. Dobbins | RB | 11 | 92.0 | -81.0 | 1386 rush; 369 rec; 284 pts | committee/even rush split (1386 rush) |
| Brenton Strange | TE | 71 | 145.7 | -74.7 | 640 rec; 129 pts | TE VOR pile — mid TE volume vs replacement |
| Matthew Stafford | QB | 39 | 107.7 | -68.7 | 4452 pass; 179 rush; 361 pts | 4452 pass yds; ADP late is 1QB-normal |
| Baker Mayfield | QB | 73 | 140.3 | -67.3 | 3684 pass; 306 rush; 317 pts | 3684 pass yds; ADP late is 1QB-normal |
| Marvin Harrison Jr. | WR | 13 | 78.0 | -65.0 | 1577 rec; 291 pts | ARI pass volume high vs ADP 78 |
| Rhamondre Stevenson | RB | 16 | 76.0 | -60.0 | 1406 rush; 252 rec; 258 pts | committee/even rush split (1406 rush) |

## Part 2 — rank policy (shipped this PR)

**Policy:** Board **Rk / Board #** = value-aware desk key in **rank space**; **Model # / pts / ADP / Value Δ stay unmodified.**

Diagnosis proved `score = model_pts − reach_penalty` floods a 1QB board with QBs (Burrow 375 pts vs CMC 318). Shipped key uses the same quantity as Model # (VOR order):

```
board_key = modelRank + reach_penalty_slots − wait_bubble_slots   # lower = earlier
reach_penalty_slots = max(0, ADP − modelRank − 12) × 0.85
wait_bubble_slots   = min(max(0, modelRank − ADP), 24) × 0.35
QB extra slots      = max(0, ADP − modelRank − 24) × 0.50   # 1QB late-QB2, same philosophy as Mock
```

Unmatched / cross-format ADP: no blend (key = modelRank); Value Δ stays —.

Do **not**: set rank = ADP, hide Model, or invent a new ADP source.

### Before / after (publish bundle, Half-PPR top 30)

| | median \|order − ADP\| | \|Δ\|≥10 in top 30 |
|---|---:|---:|
| Before (Model VOR order) | 22.5 | 21 |
| After (desk score order) | 11.8 | 16 |

Remaining large board gaps must keep Model # visible and a High deviation / Methods line — not a silent wall of ±10.

| Board | Player | Pos | ModelRank | ADP | |Δ| board | Model pts | Notes |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Christian McCaffrey | RB | 1 | 5.0 | 4.0 | 318 |  |
| 2 | James Cook III | RB | 3 | 9.7 | 7.7 | 294 |  |
| 3 | Ja'Marr Chase | WR | 4 | 3.0 | 0.0 | 314 |  |
| 4 | Bijan Robinson | RB | 6 | 1.7 | 2.3 | 289 |  |
| 5 | Saquon Barkley | RB | 5 | 13.7 | 8.7 | 292 | committee/even rush split (1464 rush) |
| 6 | CeeDee Lamb | WR | 7 | 11.3 | 5.3 | 310 |  |
| 7 | Derrick Henry | RB | 10 | 21.3 | 14.3 | 285 | committee/even rush split (1500 rush) |
| 8 | Jahmyr Gibbs | RB | 18 | 1.3 | 6.7 | 248 |  |
| 9 | Josh Jacobs | RB | 2 | 28.3 | 19.3 | 295 | committee/even rush split (1407 rush) |
| 10 | Jonathan Taylor | RB | 23 | 6.7 | 3.3 | 235 |  |
| 11 | Rashee Rice | WR | 19 | 28.7 | 17.7 | 267 | 1427 rec / 0 rush / 0 pass |
| 12 | Javonte Williams | RB | 20 | 31.0 | 19.0 | 246 | 445 rec / 976 rush / 0 pass |
| 13 | Puka Nacua | WR | 30 | 4.0 | 9.0 | 246 | 1326 rec / 0 rush / 0 pass |
| 14 | Omarion Hampton | RB | 27 | 15.3 | 1.3 | 227 |  |
| 15 | Cam Skattebo | RB | 12 | 37.3 | 22.3 | 271 | committee/even rush split (1434 rush) |
| 16 | Jeremiyah Love | RB | 26 | 25.0 | 9.0 | 229 | 486 rec / 802 rush / 0 pass |
| 17 | Emeka Egbuka | WR | 22 | 41.7 | 24.7 | 259 | 1409 rec / 0 rush / 0 pass |
| 18 | Jaxon Smith-Njigba | WR | 37 | 6.3 | 11.7 | 239 | SEA identity OK; jsn_top_tier gate wants WR rank ≤8 |
| 19 | Malik Nabers | WR | 29 | 35.0 | 16.0 | 247 | 1324 rec / 0 rush / 0 pass |
| 20 | Bucky Irving | RB | 15 | 44.3 | 24.3 | 265 | committee/even rush split (1389 rush) |
| 21 | Nico Collins | WR | 34 | 23.0 | 2.0 | 242 |  |
| 22 | Chris Olave | WR | 33 | 29.0 | 7.0 | 243 |  |
| 23 | Ashton Jeanty | RB | 40 | 11.0 | 12.0 | 215 | 375 rec / 883 rush / 0 pass |
| 24 | Kenneth Walker III | RB | 43 | 19.3 | 4.7 | 212 |  |
| 25 | Travis Etienne Jr. | RB | 36 | 40.0 | 15.0 | 219 | 407 rec / 858 rush / 0 pass |
| 26 | David Montgomery | RB | 21 | 51.3 | 25.3 | 244 | labeled HOU-RB1; 2025 depth was DET — identity to confirm vs SoT |
| 27 | D'Andre Swift | RB | 9 | 54.0 | 27.0 | 288 | committee/even rush split (1438 rush) |
| 28 | Ladd McConkey | WR | 38 | 45.3 | 17.3 | 238 | 1297 rec / 0 rush / 0 pass |
| 29 | Joe Burrow | QB | 25 | 51.7 | 22.7 | 375 | 4857 pass yds; ADP late is 1QB-normal |
| 30 | Bhayshul Tuten | RB | 14 | 56.0 | 26.0 | 269 | committee/even rush split (1404 rush) |

## Part 3 — props / projection bleed

Fantasy ranks and the 100k season boxes share `player_regular_season_totals`. Week 1 **props** (`GET /nfl/props/board`) read `nfl_player_prop_model_edges`, filled from the **weekly** box-score simulator — not this season-total CSV. Same *family* of player means, not the same published 100k rows.

### Published bundle (`20260813T132801Z`) pool sanity (v1.16+ coherence)

| Check | Result | Evidence |
|---|---|---|
| Not 32 QB1 ≥ 4,000 | **PASS** | 8 QBs ≥ 4,000 pass yards |
| League pass yards | **PASS** | 125,994 (lock ~126,000) |
| League rush yards | **PASS** | 64,000 (lock 64,000) |
| Rec = pass yards | **PASS** | rec 125,994 |
| League TDs | **PASS** | quality_checks: pass 1,085 / rush 517 / rec 1,085 |
| Top WR tails vs ADP | **WATCH** | Chase 1716 rec; Lamb / MHJ also 1,500+ (3 WRs ≥ 1,500) — high but not 2,200 absurd |
| Top RB tails vs ADP | **FAIL as rank shape / WATCH as props** | 14 RBs ≥ 1,300 rush (committee pile). This is what made Charbonnet overall #4. **Not** a 4k-QB hangover. |

**Bleed verdict:** season totals are **coherent at the league pool** (not 32×4k QBs; pass/rush/TD locks hold). The rank bug is **sort policy + even RB split**, not a broken pass-pool hangover. Props weekly means are a **separate table** — do not treat fantasy board order as a props mean rewrite. **Do not nudge ranks only if we were going to “fix” Charbonnet’s 1,425 rush**; that would be an allocator republish (explicitly out of scope; do not re-run 100k). This PR fixes **desk sort**. Model pts stay honest, so the committee pile is still visible in the Model column and High deviation flags.

`props/season totals coherent at league locks; rank issue was sort policy + RB committee shape, not 4k-QB bleed.`

## Part 4 — zone-gate leftovers (JSN / ARI / BAL / SEA)

These flags are **volume envelopes**, not dual-map identity.

| Gate | Status | Resolution |
|---|---|---|
| JSN team | **PASS** | Jaxon Smith-Njigba is SEA on the published CSV (not wrong-team). |
| `jsn_top_tier` (WR rank ≤ 8) | **OPEN** | WR rank 14, 1276 rec yards, Model #37, ADP ~6. Desk policy bubbles him toward ADP; **yards are not silently rewritten**. |
| `ari_bal_sea_pass_untouched` | **PASS** | Scheme-locked team pass yards were not overwritten at finalize. |
| `ari_bal_sea_pass_zones` (QB1 envelopes) | **OPEN** | ARI 4611.7 vs 3850–4200; BAL 2829.5 vs 3250–3550; SEA 3548.6 vs 3650–4050. Brissett/ARI over; BAL/SEA under. Closing this requires allocator republish — **not** a rank-nudge. No silent wrong-team production. |

Montgomery HOU is a separate identity flag (not in the JSN/ARI/BAL/SEA list). Left labeled; no silent team rewrite in this PR.

## Part 5 — LAR KeyError

Already patched on the publish path (`finalize_100k_expert_candidate.py`: remap `LA` → `LAR` via `canonicalize_team` + `dataclasses.replace` because `TeamDefenseBudget` is frozen). **Do not re-run 100k.** Weather/refs remain honest stubs until a forecast/crew pack exists.

## Success bar

Draft desk Board # should not look randomly ±10 vs market. Large remaining gaps keep Model # + ADP + a reason. SoT / KEI go-mode untouched.
