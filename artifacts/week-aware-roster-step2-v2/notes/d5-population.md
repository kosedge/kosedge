# D-5 — 2863 is schedule/export keys, not fold-n

`leakage/fixtures/dev_game_keys_le2023.json` counts **REG schedule keys**
for seasons 2013–2023 (the le2023 export game population). It is **not**
a fold-n, not a train/test split, and not the prior injury-fold set.

| season | n REG keys |
| --- | ---: |
| 2013–2020 | 256 each (16-game era) |
| 2021 | 272 |
| 2022 | **271** |
| 2023 | 272 |
| **total** | **2863** |

2021 and 2023 have 272 REG games (17-game season, 32 teams).
**2022 has 271** because BUF–CIN Week 17 was cancelled (not played).
That is a schedule fact in this export extract, not a fold exclusion.

Prior fold figures **F1=268 / F2=271 (539)** are a different population
(fold/exclusion set used in an earlier injury-track split). They must
not be compared 1:1 to these export keys. 2022=271 here is the
cancelled-game schedule count, not “fold F2=271”.

Holdout years 2024–25 are absent from the key file (`holdout_years: []`).
Contents of B2b W1 packs were not read.
