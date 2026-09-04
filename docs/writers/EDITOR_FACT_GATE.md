# Editor Fact Gate — Hard gate for NEW writer copy

**Owner:** Riley Nash (Editor)  
**Locked:** Ryan / CoS · **2026-09-03**  
**Status:** Product law — docs / rules only. Does **not** rewrite live archive cards or published articles.

**Primary SOP for all NEW writer copy going forward.** The Monday market-numbers pass (`docs/writers/EDITOR_WEEKLY_FACTCHECK.md` + `preview-market-factcheck.py`) remains in force and is **nested under** this gate.

---

## Locked product law (do not soft-pedal)

| #   | Law                                          | Meaning                                                                                                                                                                                                           |
| --- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Voice UNLOCKED**                           | Riley does **not** edit prose, tone, rhythm, warmth, clinical voice, or lede style. Do **not** make Casey / Reese / Morgan / Taylor / Avery (or CFB bylines) sound the same. Distinct writer voices stay product. |
| 2   | **Forward-only**                             | Gate **NEW** filings from this lock forward. Existing live cards / previews stay as stamped. **No** mass re-factcheck of the archive tonight (or as a standing mandate).                                          |
| 3   | **Hard gates**                               | Every market number, KEI / house print, model output, player/team status, injury, transaction, attribution, and date is gated. Fail → **KICK BACK**. Never invent.                                                |
| 4   | **Trace or kick**                            | Every factual claim must trace to an **approved source class** **or** Kos Edge authoritative data. If it cannot be verified → **KICK BACK** to the writer / CoS. Do **not** fill holes with something plausible.  |
| 5   | **KEI gate unchanged**                       | No KEI / KEICMB / KEINHL stamp without a real pull. **Never mint.** No print → **no house print**.                                                                                                                |
| 6   | **Filed stamps stay**                        | Do not chase live line moves after file time unless CoS restamps. Flag drift; stamp stays.                                                                                                                        |
| 7   | **Thin edge / Model↔market conflict → Pass** | Existing Edge Threshold Discipline. Do not average into a fake lean.                                                                                                                                              |
| 8   | **Desks in scope**                           | **NFL + CFB** desks, and other sports writers **when they file**.                                                                                                                                                 |

Riley is a **fact gate**, not a prose editor. Kickback is loud and explicit — never “fix quietly.”

---

## Scope

### In scope (forward-only)

- New NFL / CFB (and other sports when filed) previews, matchups, desk cards, updates, and projections that carry gated claims
- New market chrome: Fair / Market / Lean or Pass / Confidence / house + street
- New status, injury, transaction, attribution, and date claims in that copy
- Monday market-number pass (unchanged script flow)

### Out of scope

- Mass re-audit of already-stamped live archive
- Voice / prose / rhythm edits
- Taggers, KEI mint pipelines, PLAY flags, model code
- Paywall / tile hide / product chrome beyond fact stamps
- Inventing Circa / Bet365 / Betr / unauthorized theScore lines to “complete” a board

---

## Hard-gate checklist (every NEW filing)

Run before **CLEAR**. Any fail → **KICK BACK** (do not invent a fix).

### A. Market numbers

- [ ] Primary street number matches an approved street SoT at stamp time
- [ ] House / KEI (or projections / fantasy / futures as relevant) is a **real pull** or chrome says **no house print**
- [ ] Fair / Market / Lean or Pass / Confidence consistent with Edge Threshold Discipline
- [ ] Thin `|fair − market|` or material Model↔market conflict → **Pass** (not a soft lean)
- [ ] As-of stamp present; timezone **America/New_York**

### B. KEI / house

- [ ] Live pull exists for any stamped KEI / house figure
- [ ] No minted KEI / KEICMB / KEINHL
- [ ] Missing print → **no house print** (numbers bug if chrome claims otherwise)

### C. Model outputs

- [ ] Model figures trace to Kos Edge pack / bundle / expected_wins (or sport-equivalent SoT already used by the desk)
- [ ] No invented Model “fair” to rescue a lean

### D. Status / injury / transactions

- [ ] Official team/league release, named beat on the desk’s trusted list, or RotoWire / official IR-style wire
- [ ] **Never** anonymous aggregator rumor as SoT
- [ ] Screenshot alone is not confirmation

### E. Attribution

- [ ] Unique reports credited **name + outlet**
- [ ] No fake beat invent; NFL trusted list only where it exists (`data/writers/nfl-beat-writers.md` + `.json`)
- [ ] Do not invent non-NFL trusted-X lists

### F. Dates

- [ ] Every gated number has an **as-of**
- [ ] Stamp timezone **America/New_York**
- [ ] Date claims match the filing window (no silent “today” drift)

---

## CLEAR vs KICKBACK

| Verdict       | Means                                                                                                                      | Riley does                                                                                                                                                                                   |
| ------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CLEAR**     | Every gated claim traces to an approved SoT or Kos Edge authoritative data; KEI honest; stamps valid; lean/Pass rules held | Stamp the gate (see ops template). Do **not** rewrite voice. Numbers-only fixes that are already verified SoT may ship with the CLEAR.                                                       |
| **KICK BACK** | Any gated claim is unverified, minted, thin-edge dressed as lean, post-stamp chase rewrite, or rumor-as-SoT                | Return to **writer** with a concrete defect list. Escalate to **CoS** when the writer cannot resolve, scope is desk-wide, or policy is unclear. **Do not invent.** **Do not quietly patch.** |

Kickback notes must name:

1. Claim (quote or locate)
2. Why it fails the gate
3. What SoT would clear it (class — not a guessed URL)
4. Whether the piece should **sit** until research lands

---

## Approved source classes (do not invent URLs)

Document classes only. Agents and writers must pull live — do not hardcode book URLs into the SOP.

| Class                              | What counts                                                                                                                                                     | What does **not**                                                                                                  |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Kos Edge SoT**                   | Live KEI / fair-lines / Edge Board pulls; model `expected_wins` / pack artifacts already used by `preview-market-factcheck.py`; stamped street at **file** time | Minted house figures; “what KEI would say”; request-time `now()` invent stamps                                     |
| **Street**                         | DraftKings and carried **Compare Odds** books — same honesty as the site                                                                                        | Invented Circa / Bet365 / Betr lines; theScore unless explicitly authorized; single-outlet ESPN copy as market SoT |
| **Status / injury / transactions** | Official team/league releases; named beat reporters on the desk’s trusted list; RotoWire / official IR-style wires                                              | Anonymous aggregator rumor; random X; screenshot-only “confirmation”                                               |
| **Dates**                          | America/New_York stamp; as-of on every gated number                                                                                                             | Undated “current” claims; chasing post-stamp board moves without CoS restamp                                       |

ESPN / single-outlet copy is **not** a market SoT. Use live sportsbook boards for street.

---

## Kickback rules (never invent)

1. **Cannot verify → KICK BACK.** Do not fill with a plausible number, status, or attribution.
2. **No KEI without a pull.** Clear the stamp or mark **no house print**.
3. **Do not chase** post-stamp street moves unless CoS restamps.
4. **Thin edge / Model conflict → Pass** — not a dressed lean.
5. **Voice stays untouched** on CLEAR and on KICK BACK. Kickback is facts only.
6. **Forward-only** — do not open a mass archive rewrite under this SOP.
7. Writers research **at assign**; if thin, they **sit**. Writers do **not** self-mint facts to pass the gate.

---

## Report path

| Who        | When                                                                                                                                               |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Writer** | First return on claim-level defects (missing SoT, minted KEI, thin lean, rumor status, undated number).                                            |
| **CoS**    | Escalation when writer cannot clear, policy conflict, desk-wide pattern, or restamp decision. Default report path for gate outcomes and ops notes. |
| **Ryan**   | **Only if CoS (or explicit instruction) says so.** Do not escalate to Ryan by default.                                                             |

Ops checklist template (blank): `data/ops/editor-fact-gate-TEMPLATE.md`  
Filled audits (when run): `data/ops/editor-fact-gate-YYYYMMDD.md` (or sport-prefixed equivalent).  
Monday numbers report path unchanged: `data/ops/nfl-preview-factcheck-YYYYMMDD.md`.

---

## Relationship to Monday numbers pass

| Doc                          | Role                                                                                                                                |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **This file**                | Broader hard fact gate for **all** NEW gated claims (markets + KEI + model + status + injury + transactions + attribution + dates). |
| `EDITOR_WEEKLY_FACTCHECK.md` | Nested **Monday market-number** pass; keep the script flow.                                                                         |

Running the numbers script does **not** waive status/injury/attribution/date gates on new copy.

## Relationship to institutional memory

| Doc                       | Role                                                                                          |
| ------------------------- | --------------------------------------------------------------------------------------------- |
| **This file**             | Facts at **publish** (CLEAR / KICK BACK).                                                     |
| `INSTITUTIONAL_MEMORY.md` | Multi-season learning **after** outcomes — claim cards + graded lessons in `data/knowledge/`. |

Fact-gate CLEAR does **not** create a grade. Required-read of prior graded lessons on recurring assignments is owned by CoS / writer OS — see `docs/writers/COS_INSTITUTIONAL_MEMORY.md`.

---

## Integration

- Writer OS: `.cursor/rules/ai-writer-team.mdc`
- Editor prompt: `riley-nash.md` · rule: `.cursor/rules/riley-nash.mdc`
- Product chrome / voice split: `style-bible.md`
- Research order: `research-standards.md`
- Institutional memory: `docs/writers/INSTITUTIONAL_MEMORY.md` · ledger `data/knowledge/`
