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
| Expertise Contract | `employee-expertise-contract.md` — mandatory; never miss QB battles / regression / role changes |
| Trusted Source Index | `docs/writers/TRUSTED_SOURCE_INDEX.md` · `data/writers/nfl-trusted-sources.json` — Tier 1 first |
| Beat registry | `data/writers/nfl-beat-writers.json` / `.md` |
| Beat lookup script | `scripts/writers/beat-lookup.py --team XYZ` |
| X / Twitter | Handles in trusted index + beat registry; use if available — never invent tweets |
| League breakers | Tier 1 (`@AdamSchefter`, `@RapSheet`, `@TomPelissero`, …) — confirm with second source when major |

If X tooling is unavailable, WebSearch + WebFetch of Athletic/ESPN/local URLs is sufficient — still cite the writer and outlet.

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
| Reese Quinn | AFC North |
| Morgan Hale | NFC West |
| Taylor Brooks | AFC East |
| Avery Cole | NFC South |
| Jordan Vale | NFC East |
| Drew Kessler | AFC South |
| Sam Ortiz | AFC West |

## Shared files (always load)

1. `employee-expertise-contract.md` ← **mandatory; wins on conflict**
2. `style-bible.md`
3. `research-standards.md`
4. `output-formatting.md`
5. `project-log.md`
6. `docs/writers/TRUSTED_SOURCE_INDEX.md` (Tier 1 / injury / market sources)
7. Writer prompt (`casey-voss.md` etc.)
8. Beat registry for relevant teams
