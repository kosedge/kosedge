# NHL Chapter 2 — TOI grid + goalie tandem scorecard

**Stamp:** `nhl-season-engine-v0.1` · target season `2026-27`  
**Weights:** `0.20 / 0.30 / 0.50` on 2023–24 / 2024–25 / 2025–26  
**Identity:** 18 skaters · `Σ toi_share = 1` · `Σ toi_min = 300` · `Σ gs_share = 1`  
**Brief:** [`docs/NHL_CH2_TOI_GRID_BRIEF.md`](./NHL_CH2_TOI_GRID_BRIEF.md)  
**Ch1 shrink:** `NHL_TEAM_CARRY_SHRINK = 0.85` **unchanged**

---

## Sample TOI tops (`toi_min`)

- **COL:** Cale Makar 23.1 · Devon Toews 21.4 · Nathan MacKinnon 20.7 · Martin Necas 18.3 · Brent Burns 18.1
- **TBL:** Victor Hedman 19.6 · Nikita Kucherov 19.2 · J.J. Moser 18.9 · Darren Raddysh 18.7 · Jake Guentzel 18.5
- **CAR:** K'Andre Miller 20.8 · Jaccob Slavin 20.0 · Sean Walker 18.6 · Sebastian Aho 18.6 · Domenick Fensore 18.1
- **DAL:** Miro Heiskanen 23.4 · Thomas Harley 21.1 · Esa Lindell 20.8 · Mikko Rantanen 19.6 · Tyler Myers 18.4
- **BUF:** Rasmus Dahlin 23.3 · Bowen Byram 21.0 · Owen Power 20.8 · Mattias Samuelsson 20.3 · Alex Tuch 18.3
- **FLA:** Seth Jones 21.4 · Gustav Forsling 19.9 · Aaron Ekblad 19.8 · Sam Reinhart 18.4 · Marek Alscher 17.9
- **TOR:** Jake McCabe 20.2 · Morgan Rielly 20.2 · Auston Matthews 19.3 · Oliver Ekman-Larsson 18.8 · William Nylander 18.1
- **VAN:** Filip Hronek 23.8 · Marcus Pettersson 21.3 · Zeev Buium 19.1 · Elias Pettersson 18.6 · Brock Boeser 18.3

Opening-night dressing = top **18** by weighted TOI. Shares are warehouse usage, not a handwritten depth chart.

---

## Goalie tandem (GS share)

| Team | Starter              |   GS′ | Backup            |   GS′ | Residual n |
| ---- | -------------------- | ----: | ----------------- | ----: | ---------: |
| ANA  | Lukas Dostal         | 0.540 | Petr Mrazek       | 0.282 |          1 |
| BOS  | Jeremy Swayman       | 0.631 | Joonas Korpisalo  | 0.369 |          0 |
| BUF  | Ukko-Pekka Luukkonen | 0.419 | Alex Lyon         | 0.320 |          2 |
| CAR  | Brandon Bussi        | 0.329 | Frederik Andersen | 0.231 |          3 |
| CBJ  | Elvis Merzlikins     | 0.540 | Jet Greaves       | 0.445 |          1 |
| CGY  | Dustin Wolf          | 0.686 | Devin Cooley      | 0.300 |          1 |
| CHI  | Spencer Knight       | 0.615 | Arvid Soderblom   | 0.356 |          1 |
| COL  | Mackenzie Blackwood  | 0.422 | Scott Wedgewood   | 0.338 |          3 |
| DAL  | Jake Oettinger       | 0.666 | Casey DeSmith     | 0.322 |          1 |
| DET  | John Gibson          | 0.554 | Cam Talbot        | 0.434 |          1 |
| EDM  | Tristan Jarry        | 0.378 | Connor Ingram     | 0.341 |          3 |
| FLA  | Sergei Bobrovsky     | 0.674 | Daniil Tarasov    | 0.326 |          0 |
| LAK  | Darcy Kuemper        | 0.587 | Anton Forsberg    | 0.373 |          2 |
| MIN  | Filip Gustavsson     | 0.527 | Marc-Andre Fleury | 0.288 |          1 |
| MTL  | Samuel Montembeault  | 0.434 | Jakub Dobes       | 0.369 |          1 |
| NJD  | Jacob Markstrom      | 0.534 | Jake Allen        | 0.388 |          1 |
| NSH  | Juuse Saros          | 0.725 | Justus Annunen    | 0.275 |          0 |
| NYI  | Ilya Sorokin         | 0.530 | David Rittich     | 0.262 |          3 |
| NYR  | Igor Shesterkin      | 0.614 | Jonathan Quick    | 0.260 |          3 |
| OTT  | Linus Ullmark        | 0.559 | James Reimer      | 0.208 |          3 |
| PHI  | Dan Vladar           | 0.366 | Samuel Ersson     | 0.364 |          4 |
| PIT  | Stuart Skinner       | 0.565 | Arturs Silovs     | 0.248 |          3 |
| SEA  | Joey Daccord         | 0.566 | Philipp Grubauer  | 0.332 |          5 |
| SJS  | Alexandar Georgiev   | 0.398 | Alex Nedeljkovic  | 0.256 |          4 |
| STL  | Jordan Binnington    | 0.570 | Joel Hofer        | 0.430 |          0 |
| TBL  | Andrei Vasilevskiy   | 0.670 | Jonas Johansson   | 0.249 |          2 |
| TOR  | Joseph Woll          | 0.349 | Anthony Stolarz   | 0.264 |          4 |
| UTA  | Karel Vejmelka       | 0.665 | Vitek Vanecek     | 0.274 |          2 |
| VAN  | Kevin Lankinen       | 0.492 | Thatcher Demko    | 0.337 |          2 |
| VGK  | Adin Hill            | 0.308 | Ilya Samsonov     | 0.290 |          3 |
| WPG  | Connor Hellebuyck    | 0.738 | Eric Comrie       | 0.250 |          1 |
| WSH  | Logan Thompson       | 0.596 | Charlie Lindgren  | 0.370 |          1 |

`STARTER_GATE = unknown` remains register-only — **no** goalie PLAY tags in this PR.

---

## Gates

| Gate                                         | Result   |
| -------------------------------------------- | -------- |
| 32 teams · 18 skaters · Σ share/min identity | **PASS** |
| Goalie Σ GS share = 1                        | **PASS** |
| Ch1 shrink still 0.85 / prior pack untouched | **PASS** |
| KEINHL still blank                           | **PASS** |
| NBA / WNBA / CFB untouched                   | **PASS** |
| No board emit / no xG / no situation         | **PASS** |

**Stop.** Not emit. Later chapters: situation → KEI → props.
