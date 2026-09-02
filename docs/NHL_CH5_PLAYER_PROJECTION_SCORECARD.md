# NHL Chapter 5 — PlayerProjection scorecard

**Stamp:** `nhl-season-engine-v0.1` · target season `2026-27`  
**Weights:** `0.20 / 0.30 / 0.50` on 2023–24 / 2024–25 / 2025–26  
**Identity:** `|Σ G − GF/G| ≤ 0.15` · `Σ start_share = 1` · TOI Σ = 300 (from Ch2)  
**Brief:** [`docs/NHL_CH5_PLAYER_PROJECTION_BRIEF.md`](./NHL_CH5_PLAYER_PROJECTION_BRIEF.md)  
**Ch1 shrink:** `NHL_TEAM_CARRY_SHRINK = 0.85` **unchanged**  
**Pack:** 576 skaters · 126 goalies · max `g_drift` ≈ 0.0003

---

## Sample stars (per-game P)

| Player             | Team | TOI_EV |     G |     A |     P |   SOG | σ_G   |
| ------------------ | ---- | -----: | ----: | ----: | ----: | ----: | ----- |
| Nikita Kucherov    | TBL  |   19.2 | 0.545 | 1.046 | 1.591 |  3.03 | 0.052 |
| Connor McDavid     | EDM  |   20.4 | 0.512 | 1.044 | 1.556 |  3.13 | 0.077 |
| Macklin Celebrini  | SJS  |   18.6 | 0.778 | 0.658 | 1.436 |  3.10 | 0.131 |
| Leon Draisaitl     | EDM  |   19.5 | 0.614 | 0.788 | 1.403 |  2.71 | 0.098 |
| Nathan MacKinnon   | COL  |   20.7 | 0.479 | 0.919 | 1.398 |  4.04 | 0.096 |
| David Pastrnak     | BOS  |   19.3 | 0.577 | 0.801 | 1.378 |  3.61 | 0.113 |
| Sidney Crosby      | PIT  |   18.1 | 0.639 | 0.620 | 1.259 |  2.48 | 0.062 |
| William Nylander   | TOR  |   18.1 | 0.567 | 0.614 | 1.181 |  2.68 | 0.043 |

`TOI_PP = 0` for everyone — raw skater box has no PP TOI split (Phase 1 honesty).  
Warehouse note: 1-GP rate spikes (e.g. Oliver Bonk PHI) can outrank stars on raw P until a later GP floor; identity still holds.

---

## Goalie 1A / 1B (start_share · SV% · SAVES)

| Team | 1A                     | share |  SV% | SAVES | 1B                  | share |  SV% | SAVES |
| ---- | ---------------------- | ----: | ---: | ----: | ------------------- | ----: | ---: | ----: |
| FLA  | Sergei Bobrovsky       | 0.674 | .893 | 15.26 | Daniil Tarasov      | 0.326 | .893 |  8.87 |
| WPG  | Connor Hellebuyck      | 0.738 | .909 | 18.53 | Eric Comrie         | 0.250 | .894 |  6.01 |
| TBL  | Andrei Vasilevskiy     | 0.670 | .913 | 16.29 | Jonas Johansson     | 0.249 | .888 |  6.66 |
| BOS  | Jeremy Swayman         | 0.631 | .905 | 16.54 | Joonas Korpisalo    | 0.369 | .893 |  9.91 |
| COL  | Mackenzie Blackwood    | 0.422 | .905 | 10.87 | Scott Wedgewood     | 0.338 | .913 |  8.20 |
| NSH  | Juuse Saros            | 0.725 | .897 | 18.48 | Justus Annunen      | 0.275 | .904 |  7.64 |

Shares come from Ch2 tandem (not rewritten). SA = `sa_per_gs × start_share`; SAVES = SA × SV%. σ from year-rate `pstdev` — not a hardcoded 4.

---

## Gates

| Gate                                              | Result   |
| ------------------------------------------------- | -------- |
| 576 skaters · full vector + σ · TOI_PP = 0        | **PASS** |
| Goalie Σ start_share = 1 · full vector + σ        | **PASS** |
| Σ G ≈ Ch1 GF/G within residual 0.15 (max drift ≪) | **PASS** |
| σ computed / not hardcoded 4                      | **PASS** |
| Ch1 shrink still 0.85 · Ch2 packs untouched       | **PASS** |
| KEINHL still blank · no props PLAY                | **PASS** |
| NBA / WNBA / CFB untouched                        | **PASS** |

**Stop.** Pack on disk. Board still markets-only.  
Next: Chapter 3 situation (NHL goal units, paper-sim). Chapter 4 is the first emit.
