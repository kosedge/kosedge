# C-3 — raw `date_modified` / report-time format (8e2a15ac inputs)

Ruling `1ef1f0a7`: deposit evidence of the raw format (zone-bearing or not) from
`8e2a15ac` inputs, at least for the 4 games with kickoff − as_of < 5 h.
Frozen helper `parse_fit_report_time_utc` (W-4, L617–635) treats a **naive**
report time as UTC. If the raw values were naive ET, those 4 games could leak.

Holdout CLOSED. Listings inspected: `/tmp/injury-fit-raw-le2023/listings/`
seasons 2013–2023 only. No 2024/25 file was opened.

## Census (all 58,653 listing rows)

See `notes/d3-listing-row-reconcile.md` for 58653 vs fit `n_listing_rows=56537`
(2116 playoff rows: WC 1010, DIV 669, CON 324, SB 113).

| kind | n |
|---|---|
| trailing `Z` (ISO-8601 UTC) | **58653** |
| numeric offset | 0 |
| naive / zoneless | **0** |
| empty / other | 0 |

Header: `season,game_type,team,week,gsis_id,position,full_name,...,date_modified`.
Example first data row `listings_2023.csv`:
`2023,REG,ARI,1,...,2023-09-08T18:49:43Z`

File shas: `notes/c3-listings-sha256.txt`. Heads: `notes/c3-listings-2022-head.csv`,
`notes/c3-listings-2023-head.csv`. Matching rows for the 4 games:
`notes/c3-raw-short-lead-rows.csv` (8 rows: both sides).

## The 4 games with recorded gap < 5 h (from `a38a55bb`)

| game_id | gap_h | export as_of_ts | export kickoff_utc | raw date_modified (binding side) |
|---|---|---|---|---|
| `2023_15_LAC_LV` | 1.6786 | `2023-12-14T23:34:17+00:00` | `2023-12-15T01:15:00+00:00` | `2023-12-14T23:34:17Z` LAC |
| `2022_10_CLE_MIA` | 3.3222 | `2022-11-13T14:40:40+00:00` | `2022-11-13T18:00:00+00:00` | `2022-11-13T14:40:40Z` MIA |
| `2023_12_MIA_NYJ` | 3.5561 | `2023-11-24T16:26:38+00:00` | `2023-11-24T20:00:00+00:00` | `2023-11-24T16:26:38Z` MIA |
| `2023_14_HOU_NYJ` | 4.7642 | `2023-12-10T13:14:09+00:00` | `2023-12-10T18:00:00+00:00` | `2023-12-10T13:14:09Z` HOU |

Export timestamps match the raw `…Z` strings after `Z` → `+00:00`. The values
are **zone-bearing UTC**, not naive ET. The helper’s naive-as-UTC branch is
unused on these inputs. **No export correction. No exclude of these 4 games.**

A counterfactual “treat `Z` as ET wall clock” would move as_of 4–5 h later and
could leak; that is not the ISO meaning of `Z` and is not applied.

## Holdout export — same check (pre-declared)

After Ryan CLEAR and IMV review of the request only:

1. Census `date_modified` on the holdout listings **before** any outcome or close join.
2. If **every** non-empty value is zone-bearing (`Z` or numeric offset): proceed
   (same as le2023). Do not reinterpret `Z` as ET.
3. If **any** value is naive / zoneless: **STOP**. Then either correct the
   export with a zone-bearing parse, or exclude every game whose recorded
   kickoff − as_of < 5 h (DST-uncertain ET hypothesis) by this same
   pre-declared rule, identically in both arms, counted from the export
   before join.
4. Writer remains the frozen helpers. Sidecar convention remains a38a55bb-style
   (on-disk `.sha256.v2` is the pin; blob hash is not).
