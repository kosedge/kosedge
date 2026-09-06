# Desk ATS / ROI record — product contract

**Public path:** `/record/[sport]` (CFB first: `/record/cfb`)  
**Machine SoT:** `data/desk-record/<sport>/<season>/ledger.jsonl`  
**Rollup:** `data/desk-record/<sport>/<season>/summary.json` via `scripts/desk-record/rebuild_summary.py`  
**Segments:** `/record/cfb?view=play|lean|all` (default All) — each shows its own ATS (W–L–P) and ROI (PLAY 1.0u / LEAN 0.5u at stamped best pre-kick juice); ticket table filters with the same segment.

This is a **product record page**, not SEO acquisition (#13 faucet stays OFF). Soft destinations only.

---

## Eligibility (fail-closed)

| Counts                                                                                           | Does not count                                         |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| Desk **PLAY** / **LEAN** from writer packages / stamped desk SoT (`content/writers/desk-2026/…`) | Edge Board Tag PLAY/LEAN that never made the desk card |
| Desk-tagged **totals** only when the package tagged PLAY/LEAN total                              | Pass / context / board lag                             |

Stake convention until changed: **PLAY = 1.0u**, **LEAN = 0.5u**.

---

## Line + juice

- Line + American juice = **best available before kickoff** among designated Compare Odds books.
- Stamp `as_of` (and `book`) on the ticket.
- **Do not** default to flat −110 unless that was the actual best juice stamped.
- Missing pre-kick juice → `juice_status: "DATA_GAP"`; ticket still shows ATS W/L/P when the line is known; **ROI contribution omitted** (honest DATA GAP).

---

## Settlement math

| Result | Profit                        | Risked denominator     |
| ------ | ----------------------------- | ---------------------- |
| W      | `stake ×` American win payout | include stake          |
| L      | `−stake`                      | include stake          |
| P      | `0`                           | **exclude** stake      |
| OPEN   | null                          | excluded until settled |

Combined ROI = `sum(profit_u) / sum(risked_u)` over tickets with stamped juice and W/L only. If every settled W/L lacks juice → season ROI status **DATA_GAP**.

---

## Morning refresh (prior-day ET settles)

1. Grade prior-day ET finals against desk tickets (line known → W/L/P; juice only if stamped).
2. Append/update rows in `ledger.jsonl` (append-friendly; prefer stable `ticket_id` upserts when editing).
3. Rebuild summary:

```bash
python3 scripts/desk-record/rebuild_summary.py --sport cfb --season 2026
```

4. Commit + push to the production branch so `/record/cfb` reads fresh ledger.

### Cron stub

`GET /api/cron/desk-record-refresh?sport=cfb&season=2026`  
Auth: same `CRON_SECRET` Bearer pattern as `/api/cron/warm-page-data`.

The stub is **read-only on Vercel** (no durable FS write). It returns the computed summary for CoS/PA monitoring. Settlement + ledger edits remain a morning commit (or a future worker with durable storage). Do not invent additional cron secrets.

---

## CFB Week 1 seed (2026)

Source packages:

- `content/writers/desk-2026/cfb-week1-p4-20260831-jordan-ellison.md`
- `content/writers/desk-2026/cfb-week1-g5-20260831-sam-reyes.md`

Known through Sat 2026-09-05 ET: **PLAY 4–3–1**, **LEAN 0–1** (Marshall L); **WSU +23.5** left OPEN into Sun 2026-09-06. All Week 1 ROI rows are **DATA GAP** (juice not stamped on the desk cards).

---

## Copyable pattern (NFL / others)

- Empty ledger: `data/desk-record/nfl/2026/ledger.jsonl`
- Same route: `/record/nfl` renders honest empty state
- Do not invent NFL grades

---

## Out of scope

- PRs #490 / #491, NCAAM integrity Path A lake, P14 scaffolding
- Overloading `/pro/[sport]/stats` (NFL intel)
- Flat −110 invent for units
