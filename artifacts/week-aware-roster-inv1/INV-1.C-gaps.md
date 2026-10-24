# INV-1.C — gap list

## Cannot reconstruct without new evidence

Certifiable G-PIT week-aware membership/depth for approved pre-2024
development weeks **2–18** (and week 1 if capture-time is required):

| gap | seasons / weeks | why |
| --- | --- | --- |
| G1 archived weekly rosters | FIT_YEARS 2013–2023, REG weeks 1–18 | owned files are season snapshots (B1) or W1 week-label packs (B2) |
| G2 archived weekly depth with capture-time | 2013–2023, weeks 1–18 | W1 packs have `as_of: YYYY-W1-REG` only; no non-W1 packs on box |
| G3 `availability_ts` provenance | all of the above | ingest `updated_at` is not as-of (B4); week-label is not capture-time (B2) |
| G4 transactions / PS promotions / QB changes | pre-2024 | no owned announcement-timestamp archive found |
| G5 register entry | n/a | `DATA_ASSETS.md` week-aware row not on this box |
| G6 T-PIT suite | n/a | plan only (F); not implemented |

Weeks that **can** be marked ineligible today (no invention): all
pre-2024 residual-fit games that would need B1/B2 as membership/depth.
That is the honest default until G1–G3 are filled.

W1 2019–2023 packs exist but fail capture-time PIT. They must not be
quietly promoted to SoT.

## Needs-Ryan (no spend authorized)

Cursor does not authorize spend. IMV does not either.

| id | flag | ask | spend |
| --- | --- | --- | --- |
| NR-1 | Needs-Ryan | Confirm whether `/Volumes/KosEdgeData` or the research-store already holds archived weekly nflverse roster/depth (or capture-time dumps) for 2013–2023. This box could not see them. | none |
| NR-2 | Needs-Ryan | Point at `DATA_ASSETS.md` / `INVENTORY_v1.md` if they live off-box (IMV cited sha8 `8ca7c553` / sha12 `cf9ebb2ffb27`). | none |

**Not proposed:** Odds API purchase (ON HOLD). No vendor, no cost
line, no "buy weekly depth" request. If NR-1 returns empty, *IMV/Ryan*
may later consider acquisition. That is not this filing.

## What we will not do with the gap

- Invent week-1 depth from week-19 snapshots
- Pin B1/B2 as SoT
- Open 2024–25 to "see if weekly files exist there"
- Start a refit on ineligible weeks
