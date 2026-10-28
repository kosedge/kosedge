# C-2 — A6 pre-kickoff cites

INV-1 A6 general claim (v6 package freezes “pre-kickoff only”) is
**dropped** except where path:line exists.

## Cited (producer, deposited)

File: `cited/holdout_delta_producer.py` sha8 `ae8f9585`.

- L12: `5. pre-kickoff information only, with as_of <= kickoff`
- L78–81: `_pre_kickoff_only` refuses post-game score/total/close fields
- L84–99: `_assert_as_of_before_kickoff` compares `listing_as_of` to
  `kickoff_utc` only
- L130–131: both functions called on built games

Roster `week` / `availability_ts` are not checked (same as INV-1 A5).

## Searched, no Cursor claim

`rg -i 'pre-kickoff|pre_kickoff|as_of <= kickoff'` on:

- `run_injury_holdout_opening.py` — no match
- `t_expected/HOLDOUT_HAND_CHECK.md` — no match
- `t_expected/HOLDOUT_EXPECTED.json` — no match
- `gate-table.md` — no match
- `plans/`, `notes/`, `out/` — no match

No A6 runner / expected-answers cite remains.
