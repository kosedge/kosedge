# Research Standards

**LOCKED product rules** (2026-08-30). These govern research order and sourcing. They do **not** dictate body prose — voice stays UNLOCKED in each writer file.

CFB is off this desk. Trusted X contact lists exist for **NFL only** (`data/writers/nfl-beat-writers.md` + `.json`). Do not invent NBA/NHL/MLB/WNBA trusted-X lists.

---

## Required before outline or draft (MANDATORY)

**Scan the internet first — at assignment time.** Before any research outline or draft, actively research current markets and beat reporting. Do not outline or write from memory, stale training knowledge, or model outputs alone.

No 24/7 six-desk X monitor. Research when assigned.

### Research order (locked)

1. Current consensus / best available lines (live market scan) + line movement (open → current)
2. Confirmed injuries and official status
3. Rest / travel / schedule density
4. Weather (outdoor sports)
5. Named beat reporting
6. Relevant advanced metrics or model outputs when available (**supplement only**)
7. Live roster / depth-chart / competition news (e.g. QB competitions, starter battles) — never rely only on a stale model allocation when reporting conflicts

---

## Injury / status hierarchy (locked)

1. **Official** team / league report
2. **Named beat** (credited name + outlet)
3. **Aggregator** (`@32BeatWriters`)
4. **Random X**

A screenshot is **not** confirmation. Never invent or assume an injury.

---

## X is a wire, not gospel (locked)

- Use X as a tip wire to find reporting — not as finished copy.
- Credit unique reports with **name + outlet**.
- **Rewrite**; never quote-stack tweets; never copy-paste.
- NFL trusted contacts: `data/writers/nfl-beat-writers.json` / `.md` + `python scripts/writers/beat-lookup.py --team XYZ`.
- League breakers (`@AdamSchefter`, `@RapSheet`, `@TomPelissero`, `@MikeGarafolo`) are supplement only.

---

## Preferred sources

- Official team / league injury reports
- Established odds providers
- Reputable beat writers and official team sites
- Kos Edge / KEICMB model outputs when live (supplement only; not a substitute for web research)

---

## Rules

- Internet / market / beat research is mandatory for every piece — not optional
- If data conflicts, flag both sides and prefer the most recent confirmed reporting per the hierarchy above
- Timestamp important numbers when possible
- Clearly label model projections as Kos Edge / KEICMB
- When **model allocation conflicts with beat reporting** (e.g. QB starter / snap share), **flag the conflict**. Team-level numbers may still be used with an explicit caveat. Do **not** invent a blended lean that isn’t earned — if model fair and research-adjusted fair disagree materially, Pass (or show both) until reconciled. See Edge Threshold Discipline in `style-bible.md` (LOCKED).
- Primary beat: go deep. Also-covers: same process; if coverage is thin, say so and prefer **Pass** over fake expertise.
