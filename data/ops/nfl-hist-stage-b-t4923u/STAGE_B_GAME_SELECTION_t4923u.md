# STAGE_B_GAME_SELECTION_t4923u

**Step 0 seal — written BEFORE any 5g rebuild / PBP remount.**

| pin | value |
|---|---|
| Ticket | t4923u Stage B (SUPERSEDES t4921u / ce807d95) |
| Order | `COS_ORDER_CURSOR_t4923u_STAGE_B_EXEC.md` tip **62ca041c** (full `62ca041cf6289b2fc12b2964eaedee613cf5a0363f8f66ee75753c1feaf9c17a`) |
| Labels | **RETRO_FIT** / **DEV_RESEARCH** |
| CERT | 0 · NFL NO-GO |
| Stage C | **NOT authorized** (not auto-authorized after this seal) |
| After this seal | Alex RO **ba1c89f5** |
| Sealed at UTC | 2026-10-31T15:10:13Z |
| PBP at seal | **ABSENT** (`play_by_play_2016.parquet` and `2017` not on box) |
| Machine JSON | `SELECTION_HASH_SEAL.json` (same facts) |

Index **1ee90fac** is **PILOT-ONLY** (gate **83646d78**).

## 1. Frozen sample (do not enlarge)

| Slice | Role | Source N (games.csv 4fe1cdd7) | Eligible N | MISSING retained | selection_hash |
|---|---|---:|---:|---:|---|
| 2017 REG W2 | parity vs RECON **708513db** | 16 | 14 | 2 | `96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640` |
| 2017 REG W7 | pilot coverage | 15 | 15 | 0 | `6030f79c2a9690b818c7ae2b4b9ac9edd0c5c47741b222f715429753d6b29856` |
| 2017 REG W8 | pilot coverage | 13 | 13 | 0 | `3bf4a0dc29237f0b97ef6a4bf12396385f4564e4f7cd3470aeccbc1f7ecdc58e` |
| 2016 REG W8 | season-hardcode check | 13 | 13 | 0 | `58b9c650cdc69216454981501b84d8a122b9c1a5fac1e3ce8c69447c15790eca` |
| **Combined eligible** | — | **57** | **55** | **2** | `448946a2a825f82f238bff0aea04a740c7a03c363b17f1e17e4452df0486e915` |

W2 14 is the **sealed t4893u list** (not a new “first 14 by game_id” slice). Re-derived here only to confirm identity vs `96a13176`.

## 2. Eligibility rule (fixed; copied from t4893u 7e77c57f)

Transforms used (pandas-free; no PBP): `load_games`, `load_oos_2016_2017`, `build_completed`, `record_asof`, `selection_hash` — verbatim from `data/ops/nfl-hist-bt-stage1b-w3w6-t4893u/seal_selection_t4893u.py` (W2 port).

1. Source universe = every `games.csv` row with `(season, week)` in the frozen slices. Week ≤ 17. Season ≥ 2024 abort.
2. Completed-game as-of = same-season rows that join OOS **1ee90fac** on `(season, week, home, away)` with both scores present, kickoff **strictly before** the candidate’s `kickoff_utc`.
3. **Ineligible / MISSING** if either side has **0** completed same-season games as-of kickoff.
4. **Retain MISSING.** Do not replace, fill, or substitute another game. Do not pull a different week to keep N.
5. Cell-level `MISSING_RECORD` (exact `rating_week` T2 miss, e.g. bye) is **not** a selection exclusion. Those games stay eligible; missing cells stay missing at rebuild.
6. Hash recipe (unchanged): `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`.

## 3. Input pins (reuse owned; no new acquisition)

| Asset | sha8 | full sha256 | path / note |
|---|---|---|---|
| games.csv | **4fe1cdd7** | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` | `data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv` (PR #638 / tip 82ffb211) |
| OOS index | **1ee90fac** | `1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed` | `data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv` — **PILOT-ONLY**, gate 83646d78 |
| PBP restage receipt | **6ee24b44** | receipt `COS_RECEIPT` / `CURSOR_S1_PBP_RESTAGE_t4696u_v1` | 2012–2022 MATCH; **not opened at this seal** |
| RECON W2 content | **708513db** | `708513db885fe362aca9446578154d58e9d8265857ec2385e475323b24f24182` | `data/ops/nfl-hist-bt-stage1b-w2-t4893u/RECON_MATRIX.csv` (filename tip 440314e4 is **not** the content hash) |
| RECON W3–W6 content | **cdff0115** | `cdff011536a7cd9224b1238e08b707c36222243833f778f2df61b577e0c80235` | cited pin / lineage; **not** in this sample |
| Builder (W2) | **7e77c57f** | `7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64` | season hardcode to be generalized **only** as far as these weeks |

Do **not** touch control tip **02197f58** / `SCORE_RESULTS` **2b9f302e**.

## 4. Pre-registered tolerances (BEFORE rebuild; no post-hoc change)

Registered in this file and in `SELECTION_HASH_SEAL.json` at 2026-10-31T15:10:13Z, **before** PBP remount.

| Family | Compare | Tolerance | Rationale (pre-run) |
|---|---|---|---|
| Off/def W-L index | rebuilt vs sealed RECON / games.csv index | **\|Δ\| < 1e-6** | Stage A verified 296/296 RECON index cells at this bar; T5/record floats. |
| 5g EPA + success + matchup_diff EPA/success | rebuilt vs sealed RECON **708513db** on the W2 14 only | **\|Δ\| < 1e-9** | Same PBP pin + T1 port (7e77c57f / 5fc97157) must rematerialize near-exact. |

Applies to fields:

- Index: `offense_index_home/away`, `defense_index_home/away`
- 5g EPA/success: `home/away_off_epa_5g`, `home/away_def_epa_allowed_5g`, `home/away_success_offense_5g`, `home/away_success_defense_allowed_5g`, `matchup_diff_off_epa_5g`, `matchup_diff_success_rate_5g`

**2017 W7–W8 and 2016 W8 have no sealed 5g RECON.** Tolerances do **not** invent a compare target. Those slices are coverage + as-of + season-handling. Index vs populated finite `games.csv` 4fe1cdd7 cells uses \|Δ\| < 1e-6.

No loosening after residuals. Feature-semantics change ≠ mapping fix — stop and escalate.

## 5. Eligible game_ids (sorted)

### 2017 W2 parity (14) — hash `96a13176…`

2017_02_ARI_IND  
2017_02_BUF_CAR  
2017_02_CLE_BAL  
2017_02_DAL_DEN  
2017_02_DET_NYG  
2017_02_GB_ATL  
2017_02_HOU_CIN  
2017_02_MIN_PIT  
2017_02_NE_NO  
2017_02_NYJ_OAK  
2017_02_PHI_KC  
2017_02_SF_SEA  
2017_02_TEN_JAX  
2017_02_WAS_LA

### 2017 W7 (15) — hash `6030f79c…`

2017_07_ARI_LA  
2017_07_ATL_NE  
2017_07_BAL_MIN  
2017_07_CAR_CHI  
2017_07_CIN_PIT  
2017_07_DAL_SF  
2017_07_DEN_LAC  
2017_07_JAX_IND  
2017_07_KC_OAK  
2017_07_NO_GB  
2017_07_NYJ_MIA  
2017_07_SEA_NYG  
2017_07_TB_BUF  
2017_07_TEN_CLE  
2017_07_WAS_PHI

### 2017 W8 (13) — hash `3bf4a0dc…`

2017_08_ATL_NYJ  
2017_08_CAR_TB  
2017_08_CHI_NO  
2017_08_DAL_WAS  
2017_08_DEN_KC  
2017_08_HOU_SEA  
2017_08_IND_CIN  
2017_08_LAC_NE  
2017_08_MIA_BAL  
2017_08_MIN_CLE  
2017_08_OAK_BUF  
2017_08_PIT_DET  
2017_08_SF_PHI

### 2016 W8 (13) — hash `58b9c650…`

2016_08_ARI_CAR  
2016_08_DET_HOU  
2016_08_GB_ATL  
2016_08_JAX_TEN  
2016_08_KC_IND  
2016_08_MIN_CHI  
2016_08_NE_BUF  
2016_08_NYJ_CLE  
2016_08_OAK_TB  
2016_08_PHI_DAL  
2016_08_SD_DEN  
2016_08_SEA_NO  
2016_08_WAS_CIN

## 6. MISSING retained (do not substitute)

| game_id | slice | reason |
|---|---|---|
| 2017_02_CHI_TB | 2017 W2 | TB home — 0 completed 2017 games as-of kickoff (Irma postpone) |
| 2017_02_MIA_LAC | 2017 W2 | MIA away — 0 completed 2017 games as-of kickoff (Irma postpone) |

No W7 / W8 2017 / W8 2016 game failed the 0-completed-as-of rule. Bye weeks (source N 15/13 vs 16) are **schedule byes**, not selection MISSING.

Missing-retained combined hash: `sha256` of those two ids = see `selection_hash_missing_retained_combined` in JSON.

## 7. Prohibited (unchanged)

Outcome analysis · model scoring · fit/tune · new acquisition · 2024–25 · Stage C · Q2 Phase B · merge/deploy/publish · touch 02197f58 / SCORE_RESULTS 2b9f302e.

Rebuild after this seal may map existing five-game EPA/success fields to contract **b41f4b43**. Semantics changes stop and escalate.

NFL NO-GO · CERT=0
