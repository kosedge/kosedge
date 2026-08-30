# Training Camp Desk — Kos Edge AI Writers

How to assign and ship NFL training-camp news breaks and camp notebooks without breaking Edge Threshold Discipline.

**Desk OS (2026-08-30):** Handicapping product is **LOCKED**; body prose is **UNLOCKED** per writer voice pack. See `style-bible.md` and `.cursor/rules/ai-writer-team.mdc`. Do not flatten writers into one house voice. **HOUSE vs STREET** (pull KEI before outline; never mint; stamp at pull; chrome shows both) is LOCKED — Ryan 2026-08-30. **Cadence** (weekday vs Monday) is LOCKED below — execution only, not a new product. CFB is off this desk. NFL trusted X list only (`data/writers/nfl-beat-writers.*`).

## Mission

Expert researchers who move fast when camp news breaks. Product chrome and thresholds are shared; **voice is not**. Each writer keeps their pack (Casey freeze, Reese conversational, Morgan clinical, Taylor patient, Avery crisp).

Brand still applies: no hype, no locks, process over results. Thin edges → **Pass**.

## Cadence (LOCKED — weekday vs Monday)

Ryan confirmed **2026-08-30**. Writers ship on NFL also-covers (Casey NFC North; Avery NFC East + South; Reese AFC North + West; Morgan NFC West; Taylor AFC East + South).

| Slot                  | What ships                                                                                             | What does **not**                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **Weekday (Tue–Fri)** | Only clubs with **real** news. Quiet clubs **skip** or get a short **pulse** line. Cutoff **~6pm ET**. | **NEVER** a 32-card hero dump. Daily ≠ 32 essays.     |
| **Monday**            | Full-32 camp package (news cards + pulse for quiet) **plus** the weekly team-preview **NUMBER** pass.  | Voice rewrites of previews; chasing later line moves. |
| **Injury day**        | Same-day weekday file — do not wait for Monday.                                                        | Holding material news for the Monday package.         |

**Monday NUMBER pass:** Riley Nash gates **numbers only** (not voice). HOUSE vs STREET already locked — pull live KEI if a print exists, **never mint**, stamp at pull, do not chase. Full SoT: `style-bible.md` House vs Street.

**Byline rules:** Camp cards stay **date-only** (no writer byline). Season-preview bylines follow the coverage matrix — **PHI going forward is Avery Cole** (not Jordan Vale). Do not rewrite locked preview bodies just to flip a byline; Monday’s number pass owns the pointer.

**Shipping:** “Desk updating” on an empty shelf is honest **UI fallback**, not a substitute for shipping the weekday news package or Monday full-32 + number pass.

## When to use which format

| Format                     | When                                                          | Length               |
| -------------------------- | ------------------------------------------------------------- | -------------------- |
| **News break**             | Injury, cut, starter change, practice DNP that moves a number | 120–280 words        |
| **Camp notebook**          | Day’s practice themes, battles, bubble notes                  | 400–700 words        |
| **Full preview / matchup** | Season win totals, Week 1 cards, futures packages             | Per `style-bible.md` |

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

| Tool                        | Use                                                                                                                  |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `WebSearch`                 | Fresh headlines before every piece                                                                                   |
| `WebFetch`                  | Read full beat articles / camp notebooks                                                                             |
| **Trusted X contact index** | `data/writers/nfl-beat-writers.json` / `.md` — **primary** fast-update source for Camp Desk + Monday preview refresh |
| Beat lookup script          | `scripts/writers/beat-lookup.py --team XYZ`                                                                          |
| X / Twitter                 | Handles in registry; use if available in environment — never invent tweets                                           |
| League breakers             | `@AdamSchefter`, `@RapSheet`, `@TomPelissero`, `@MikeGarafolo` — supplement only                                     |
| Also ok                     | Team official, credible local beat, RotoWire / VSiN-class when relevant                                              |

### Camp / Monday refresh — source doctrine (locked)

**Camp/Monday refresh uses the beat index + multi-source. X handles are a research contact list, not the product.**

1. Start with the team’s trusted contacts in `nfl-beat-writers.json` (primary + local + `team_site`). Use handles to find reporting — do not scrape or mirror tweets as copy.
2. Corroborate with at least one second source (official, Athletic/local, AP, club site).
3. ESPN may be _one_ input. Never brand the desk as an ESPN wire mirror. Never invent quotes.
4. Attribute generically when a quote is not on hand (“per team report”, “multiple beat reports”). **No X profile links, no “follow @…” CTAs on Camp Desk.**
5. Team previews get a **NUMBER** pass **every Monday** in camp/season (`**Date:**` + Bottom line / What matters most at minimum). Riley gates numbers; HOUSE vs STREET — pull KEI if printed, never mint.
6. **Camp Desk day files:** write `content/writers/camp-desk-2026/YYYY-MM-DD.json` (see that folder’s README). Newest file always shows in preseason. **Weekday** = real-news clubs only (quiet skip/pulse). **Monday** = full 32. Injury days ship same-day.

If X tooling is unavailable, WebSearch + WebFetch of Athletic/local/official URLs is sufficient — still cite the writer and outlet, never paste a tweet as the card.

## Camp Desk product (preseason)

Camp Desk (`/pro/nfl/camp`) surfaces **KosEdge copy only**. Empty “No KosEdge camp notes” is a bug while camp is active — ship the cadence package; do not leave the shelf on “Desk updating” as a substitute for writing.

| Slot              | Spec                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Weekday (Tue–Fri) | League wrap + clubs with **real** news only (`package: daily`). Quiet = skip or pulse. **Not** 32 essays. ~6pm ET cutoff. |
| Monday            | Full 32 (news + pulse for quiet) + wrap (`package: monday`) **and** weekly preview NUMBER pass                            |
| Injury day        | Same-day weekday file                                                                                                     |
| Freshness         | Newest `desk_date` always on the shelf in preseason. Older than 72h → Archive                                             |
| Empty pipeline    | Honest **Desk updating** + last note date is UI only — never a dead shelf, **never** an excuse to skip ship               |

Expertise contract: consensus first, specific impact, thin edge = **Pass**. Camp cards = **date-only** (no writer byline). Depth/roster claims flag SoT intel — do not invent starters.

**Schema note — `preview_delta` (singular):** `apps/web/lib/nfl-camp-desk-daily.ts` collects **`preview_delta` only**. Plural `preview_deltas` is ignored (Aug 26 used the plural key — those 15 deltas never collected). Monday packages must use the singular key; copy that field’s shape from `2026-08-17.json`, not `2026-08-26.json`.

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

Also-covers for Camp Desk + Monday NUMBER pass (LOCKED matrix):

| Writer        | NFL also-covers     |
| ------------- | ------------------- |
| Casey Voss    | NFC North           |
| Reese Quinn   | AFC North, AFC West |
| Morgan Hale   | NFC West            |
| Taylor Brooks | AFC East, AFC South |
| Avery Cole    | NFC East, NFC South |

**PHI** season-preview byline going forward: **Avery Cole** (NFC East). Coverage pointer only until Monday’s pass owns the file — do not rewrite `PHI.md` solely for the byline flip.

## Shared files (always load)

1. `style-bible.md` (LOCKED product + UNLOCKED voice pointer)
2. `research-standards.md` (LOCKED)
3. `output-formatting.md` (LOCKED chrome)
4. `project-log.md`
5. Writer prompt voice pack (`casey-voss.md` etc. — UNLOCKED)
6. Beat registry for relevant NFL teams only (`nfl-beat-writers.json`)

Riley Nash fact-checks **numbers** only — see `docs/writers/EDITOR_WEEKLY_FACTCHECK.md`.
