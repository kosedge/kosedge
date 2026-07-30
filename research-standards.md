# Research Standards

Writers are **expert researchers first**, stylists second. No outline or draft without fresh internet research.

## Mandatory pre-write checklist (run in order)

Before any research outline or draft, complete every step:

1. **Web search** — Current headlines for the team / game / prop (training camp, injuries, depth chart, cuts, QB competition). Prefer results from the last 24–72 hours.
2. **Beat-writer scan** — Load `data/writers/nfl-beat-writers.json` (or the `.md` index). Check primary X/Twitter handles and recent reporting for every relevant team. Fetch / open recent articles when a news break depends on them.
3. **Official injury / roster** — Team site, league injury report, or confirmed official statements. Do not invent or assume injuries.
4. **Model conflict check** — Compare Kos Edge / KEICMB allocation and fair numbers to beat reporting. If they disagree materially, **flag the conflict** and default **Pass** (or show both) — never invent a blended lean. See Edge Threshold Discipline in `style-bible.md`.
5. **Then write** — Outline only after steps 1–4. Draft only after outline (or after an approved news-break path — see Training Camp Mode).

**Tools:** Prefer `WebSearch` + `WebFetch` for articles. Use X/Twitter handles from the beat registry when available. League-wide breakers (`@AdamSchefter`, `@RapSheet`) supplement beats — they do not replace team beat writers.

## Training Camp Mode (July–early September)

Prioritize signals that move Week 1 markets:

- Practice participation / PUP / NFI / limited vs full
- Depth chart battles and starting-job competitions (especially QB)
- Cut-down bubble players and projected 53
- Injury timelines → Week 1 availability
- Scheme / coordinator notes that change usage (snap share, target share, rush share)
- Joint-practice and preseason game observations — weight recent over OTAs

When speed matters, prefer **news-break** or **camp notebook** formats over long essays (see below and `docs/writers/TRAINING_CAMP_DESK.md`).

## News-break format

Use for breaking camp / roster / injury items:

- **Short** — usually 120–280 words (not a full preview)
- **Timestamped** — include date/time and timezone when known (e.g. `2026-07-30 14:10 ET`)
- **Source-linked** — cite outlet URLs and/or writer X handles; never invent quotes or sources
- **Speed over essay** — lede = what broke; 2–4 bullets of context; market implication if clear; Handicapper’s Note if a number is involved
- Still obey Edge Threshold Discipline — thin edges → **Pass**; no soft Over for ~0.1 win

## Preferred sources

- Official team / league injury reports and depth charts
- Established odds providers (live consensus + movement)
- Reputable beat writers (registry + Athletic / ESPN NFL Nation / major locals)
- Team sites and PR when confirming transactions
- Kos Edge / KEICMB model outputs when live (**supplement only** — not a substitute for web research)

## Rules

- Internet / market / beat research is **mandatory** for every piece — not optional
- Never invent quotes, sources, injuries, or practice observations
- Cite URLs and/or `@handles` for material claims
- If data conflicts, flag both sides and prefer the most recent confirmed reporting
- Timestamp important numbers when possible
- Clearly label model projections as Kos Edge / KEICMB
- When **model allocation conflicts with beat reporting** (e.g. QB starter / snap share), **flag the conflict**. Team-level numbers may still be used with an explicit caveat. Do **not** invent a blended lean that isn’t earned — if model fair and research-adjusted fair disagree materially, Pass (or show both) until reconciled.
- Confidence 1–2 on thin/uncertain edges; never 3+ below threshold

## Beat writer registry

- Machine-readable: `data/writers/nfl-beat-writers.json`
- Human index: `data/writers/nfl-beat-writers.md`
- Lookup: `python scripts/writers/beat-lookup.py --team BUF`
- Desk workflow: `docs/writers/TRAINING_CAMP_DESK.md`

Confidence labels in the registry:

- `high` — confirmed current beat via ESPN camp hub / outlet bio / recent bylines
- `medium` — strong candidates; verify before citing as sole source
- Never invent handles; if uncertain, list candidates and mark `medium`
