# Selection-hash seal attestation — W3–W6 t4893u

**Sealed before PBP open.** File `SELECTION_HASH_SEAL.json` was written from `games.csv` pin **4fe1cdd7** + OOS **1ee90fac** as-of counts only.

At seal write (2026-10-31 03:37:40Z):

- Path `/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet` **did not exist** on this box.
- Seal script does not import pandas and does not read parquet.
- Recipe unchanged from W2: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`.

| Set | N source | N excl | N eligible | selection_hash |
|---|---|---|---|---|
| W3 | 16 | 0 | 16 | `4e93dfcca0e5da6b16f2479e126519624fbeb2fbbb874951b1f273c89a313420` |
| W4 | 16 | 0 | 16 | `14f45ee7074eaf5f9aef80dbb9f17eb729476b447583b5b6dd20e0cfdd30cdb3` |
| W5 | 14 | 0 | 14 | `e7cd7ec670d23d272743d5502454cace79f27a7561306f044f3b7642affa5a36` |
| W6 | 14 | 0 | 14 | `969de0507857629f185b842a4bc6b4f3417fcb6fc40ba22322926b6e03c9ba67` |
| Combined | 60 | 0 | 60 | `e03c962ee6a95ca62a25bf050e4775f44893c384c63a31baaead5f9c9f6c5ebf` |

Exclusion rule (fixed, same as W2): drop any game where either side has 0 completed same-season games as-of kickoff. **No W3–W6 game failed.** Irma TB/MIA had W2 completed before W3. No fills.

W2 lineage: tip `440314e4` · Alex PASS_RECON `91e2d7db` · W2 selection_hash `96a13176…` · PR #669.

PBP remount + matrix rebuild happen **after** this seal.

NFL NO-GO · CERT=0
