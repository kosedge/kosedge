# CURSOR_S1_PBP_RESTAGE_t4696u_v1

| pin | value |
|---|---|
| Filed | 2026-10-29T13:14:00Z |
| Runner | Cursor cloud agent (`bc-4a5cc6e6-9ea0-56c0-b17c-791a7a46f4de`) |
| Authority | DECISION_RYAN_t4696u CONDITIONAL CLEAR (a) sha8 `6df94902` |
| Order | COS_ORDER_CURSOR_t4696u_S1_PBP_RESTAGE_v1 sha8 `98e73057` |
| Pins source | attached `SHA256SUMS.restored_pbp` (2012–2022 rows only; 2023 row unused / not fetched) |
| Attached SUMS sha256 | `5451fb17f50fc5766fe497661dfacc3ddb0f442925e499ab548c15c31ea772b6` |
| Order full sha256 | `98e7305736d0ce84c9e5b7a12112b37c0cb9587b5a9b857e244b27f7fa71ab11` |
| Decision full sha256 | `6df94902eee38bd7c61dfbcec31129c615c41bbd843f4f9b71ef0f948c8d9d12` |
| Result | **PASS** — 11/11 seasons MATCH pinned sha256 |
| 2023 | **untouched** (not downloaded, not opened, not hashed from the network) |

Report sha256 is in the sibling sidecar `CURSOR_S1_PBP_RESTAGE_t4696u_v1.md.sha256` (computed after this body was frozen).

## Durable paths (Alex consume)

Primary (workspace disk):

```
/workspace/data/raw/nfl/pbp/t4696u_s1_restage/
```

Agent-store copy (same 11 files, independently re-hashed MATCH):

```
/cursor/stores/self/artifacts/t4696u-s1-pbp-restage/
```

Alias (symlink): `/opt/cursor/artifacts/t4696u-s1-pbp-restage/`

Consume only:

- `play_by_play_2012.parquet` … `play_by_play_2022.parquet` (11 files)
- `SHA256SUMS.matched` — hashes of the persisted MATCH set
- `receipt.tsv` — per-season URL / bytes / sha256 / MATCH
- `CONSUME.txt`

Do **not** look for or fetch `play_by_play_2023.parquet`. It is not in either directory.

## Method

1. URL template only: `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet`
2. Download seasons **2012–2022 only**. No alt URL. No “latest”. No reconstruction.
3. `sha256sum` on raw bytes **before any parse**. No pandas / pyarrow / nflreadpy open.
4. Compare to exact pins from attached `SHA256SUMS.restored_pbp` 2012–2022 rows (identical to COS_ORDER full pins).
5. MATCH → persist to both durable paths. Mismatch → ABORT whole job.
6. Independent re-hash of both persisted copies after the job: 11/11 MATCH.

## Per-season results

| season | URL | bytes | sha256 | status |
|---|---|---:|---|---|
| 2012 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2012.parquet | 19322039 | `447b90789104aac70427ec9d3b51df7247234029d0ecabd269279369b1cc6278` | MATCH |
| 2013 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2013.parquet | 19521610 | `f454605a1983b3946baf0ffadf3a0b9f5e04735c4b84732e0483f2049a780d00` | MATCH |
| 2014 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2014.parquet | 19360792 | `54c01408d8f0ff9e013a4ea51428b91d610101f72545d082e932f5710e2fb4f7` | MATCH |
| 2015 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2015.parquet | 19545842 | `01b5ae7d06633a2e66b418404461a3d4ff055ad2f3a87d453cebcc8d3fda7ed9` | MATCH |
| 2016 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2016.parquet | 19344382 | `95eba04e2145e3c1c8ca502f2a3a76cfb0a5990680c3fb480f02a74a45f54a3b` | MATCH |
| 2017 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2017.parquet | 19050401 | `84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710` | MATCH |
| 2018 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2018.parquet | 19072097 | `2e6f2dce7c7ebd46e985cabe0c17eb72b39a77f98cb4478409294f50b5820150` | MATCH |
| 2019 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2019.parquet | 19119729 | `60c3067017db2d28a78f66a79b657268be8578d9a5288e6a827efdcd7fe42540` | MATCH |
| 2020 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2020.parquet | 19286459 | `8889f5d8782b5c5dce3c3644acdc0322b228a7e9cb13fa36cbac250e260e9f60` | MATCH |
| 2021 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2021.parquet | 20249925 | `333ad34378e5339d5172717cc83378e908daf02c8699416ab3e17c2ec10f78d8` | MATCH |
| 2022 | https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2022.parquet | 20426548 | `931121d8897779d7944e2a293e92ed8799c8e5cceef84096ac42339003fedc09` | MATCH |

All HTTP statuses were 200. No ABORT seasons.

## Coverage

- Present: 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022 (11 files).
- Absent by design: 2023. Attached SUMS contains a 2023 row (`bd348473…`); it was **not** downloaded, opened, or used as a pin for this job.
- No other seasons fetched.

## Not done (locked)

- S1 model / protocol v2 `414d36a0` **not run** (gated on CoS RECEIPT of this PASS, then Alex).
- #650 / #653 untouched.
- No merge. No deploy. No Odds API. No CERT/F2 change.
- No invented or reconstructed data.

## Hard locks (unchanged)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen.

## CoS handoff

(a) **PASS**. Files are pin-matched and persisted at the durable paths above. CoS may file RECEIPT and gate Alex execute (b).
