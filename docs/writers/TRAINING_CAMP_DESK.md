# Training Camp Desk — Kos Edge AI Writers

How to assign and ship NFL training-camp news breaks and camp notebooks without breaking Edge Threshold Discipline.

## Mission

Expert researchers who move fast when camp news breaks. Style serves the fact pattern — never the reverse.

Brand still applies: no hype, no locks, process over results. Thin edges → **Pass**.

## When to use which format

| Format | When | Length |
|--------|------|--------|
| **News break** | Injury, cut, starter change, practice DNP that moves a number | 120–280 words |
| **Camp notebook** | Day’s practice themes, battles, bubble notes | 400–700 words |
| **Full preview / matchup** | Season win totals, Week 1 cards, futures packages | Per `style-bible.md` |

Default to news break / camp notebook during July–early September unless the assignment asks for a full preview.

## Assign a news break

1. **Pick the writer** from the coverage matrix (`ai-writer-team.mdc` / writer prompt files).
2. **Restate the assignment** (team, claim, market if any).
3. **Run beat lookup:**
   ```bash
   python scripts/writers/beat-lookup.py --team BUF
   ```
4. **Mandatory research** (see `research-standards.md`):
   - `WebSearch` — team + topic + “training camp” (last 24–72h)
   - Beat handles from registry — scan / fetch recent articles
   - Official injury / roster confirmation
   - Model conflict check vs Kos Edge / KEICMB
5. **Draft news break** using the template below.
6. **Handicapper’s Note** if a market number is involved; else omit lean or mark **Pass / N/A**.
7. Update `project-log.md`.

## Required tools

| Tool | Use |
|------|-----|
| `WebSearch` | Fresh headlines before every piece |
| `WebFetch` | Read full beat articles / camp notebooks |
| **Trusted X contact index** | `data/writers/nfl-beat-writers.json` / `.md` — **primary** fast-update source for Camp Desk + Monday preview refresh |
| Beat lookup script | `scripts/writers/beat-lookup.py --team XYZ` |
| X / Twitter | Handles in registry; use if available in environment — never invent tweets |
| League breakers | `@AdamSchefter`, `@RapSheet`, `@TomPelissero`, `@MikeGarafolo` — supplement only |
| Also ok | Team official, credible local beat, RotoWire / VSiN-class when relevant |

### Camp / Monday refresh — source doctrine (locked)

**Camp/Monday refresh uses the beat index + multi-source. X handles are a research contact list, not the product.**

1. Start with the team’s trusted contacts in `nfl-beat-writers.json` (primary + local + team_site). Use handles to *find* reporting — do not scrape or mirror tweets as copy.
2. Corroborate with at least one second source (official, Athletic/local, AP, club site).
3. ESPN may be *one* input. Never brand the desk as an ESPN wire mirror. Never invent quotes.
4. Attribute generically when a quote is not on hand (“per team report”, “multiple beat reports”). **No X profile links, no “follow @…” CTAs on Camp Desk.**
5. Team previews refresh **every Monday** in camp/season (`**Date:**` + Bottom line / What matters most at minimum).
6. **Daily Camp Desk:** write `content/writers/camp-desk-2026/YYYY-MM-DD.json` (see that folder’s README). Newest file always shows in preseason. Quiet clubs skip — no filler essays. Injury days ship same-day; do not wait for Monday.

If X tooling is unavailable, WebSearch + WebFetch of Athletic/local/official URLs is sufficient — still cite the writer and outlet, never paste a tweet as the card.

## Camp Desk product (preseason)

Camp Desk (`/pro/nfl/camp`) surfaces **KosEdge copy only**. Empty “No KosEdge camp notes” is a bug while camp is active.

| Slot | Spec |
|------|------|
| Daily | League wrap + every team with **real** news (`package: daily`) |
| Monday | Full 32 + wrap (`package: monday`, see `2026-08-17.json`) |
| Injury day | Same-day daily file |
| Freshness | Newest `desk_date` always on the shelf in preseason. Older than 72h → Archive |
| Empty pipeline | Honest **Desk updating** + last note date — never a dead shelf |

Expertise contract: consensus first, specific impact, thin edge = **Pass**. Date-only byline. Depth/roster claims flag SoT intel — do not invent starters.

How to add a day: `content/writers/camp-desk-2026/README.md`.

## News-break output template

```markdown
# [TEAM]: [What broke] — Camp News Break

**Timestamp:** YYYY-MM-DD HH:MM ET  
**Sources:** [@handle / Outlet](url); [second source](url)

[1–2 sentence lede: what happened and why it matters for markets or Week 1.]

- **Fact:** …
- **Context:** …
- **Market angle:** … (or “No actionable lean yet.”)

**Handicapper’s Note**  
Fair number: [X or N/A]  
Market number: [Y or N/A]  
Lean: [Over / Under / Side / Pass / N/A]  
Confidence: [1–5]  
Key risk: [one sentence]

This analysis is for informational and educational purposes only. Sports betting involves risk. Please bet responsibly. Past performance does not guarantee future results. Kos Edge Analytics is not responsible for any financial losses.
```

## Camp notebook template (short)

```markdown
# [TEAM] Camp Notebook — [Date]

**Sources:** … (handles + URLs)

**Participation / injuries**
- …

**Battles / depth chart**
- …

**Bubble / cuts watch**
- …

**Week 1 implication**
- …

**Model vs beat**
- Flag conflicts; Pass if unresolved.

**Handicapper’s Note** (if markets attached)
…
```

## Edge Threshold Discipline (non-negotiable)

- Thin edges (~half a win or less on season totals, or ~0.1 win dressed as “soft Over”) → **Pass**
- Never invent quotes or sources
- Model vs research conflict → Pass or present both — do not average into a fake lean

## Coverage owners (NFL slices)

| Writer | NFL primary / also |
|--------|--------------------|
| Casey Voss | NFC North |
| Reese Quinn | AFC North, AFC West |
| Morgan Hale | NFC West |
| Taylor Brooks | AFC East, AFC South |
| Avery Cole | NFC South, NFC East |

## Shared files (always load)

1. `style-bible.md`
2. `research-standards.md`
3. `output-formatting.md`
4. `project-log.md`
5. Writer prompt (`casey-voss.md` etc.)
6. Beat registry for relevant teams
