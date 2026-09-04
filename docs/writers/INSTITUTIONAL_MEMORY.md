# Institutional Memory — Graded lesson ledger (SoT)

**Owner:** CoS (process) · Writers may file claim cards · Grades: CoS / Riley-assisted with evidence  
**Locked:** Ryan / CoS · **2026-09-03 night**  
**Status:** Foundation — schema + SOP + empty ledger. **No invented grades. Forward-only.**

**Ledger SoT:** `data/knowledge/` (in-repo). Chat memory may **point** here; it is **not** the source of truth.

**Complements** `docs/writers/EDITOR_FACT_GATE.md` — fact gate = facts at publish; this ledger = multi-season learning **after** outcomes.

---

## Locked product law (do not soft-pedal)

| #   | Law                         | Meaning                                                                                                                                                                                                   |
| --- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **In-repo SoT**             | Knowledge lives in `data/knowledge/`. Agents must read the ledger — not rely on chat memory alone.                                                                                                        |
| 2   | **Claim cards on NEW work** | Every material desk claim on **NEW** work should be loggable as a claim card (claim, sport/event, as-of, house/model/market, SoT class, writer, status).                                                  |
| 3   | **Grades are sacred**       | After the event/season: grade **right / wrong / mixed / void** + short lesson. **Never invent** grades. No evidence → leave `open` or mark `void` with reason — do not guess.                             |
| 4   | **Required-read on assign** | Before writing a **recurring product** (draft preview, season guide, week preview, futures, etc.), writer + CoS **must** read prior-year / prior-cycle graded lessons for that product. **Not optional.** |
| 5   | **No prior grades**         | If the product folder has no graded cards, note **`no prior grades`** in the assignment / filing note. **Do not hallucinate history.**                                                                    |
| 6   | **Forward-only**            | Logging starts from this lock. Backfill of 2024–2026 is a **later wave with real sources only**. Do not invent 2026 draft (or any) right/wrong grades tonight.                                            |
| 7   | **Voice stays unlocked**    | Riley gates facts at publish (`EDITOR_FACT_GATE.md`). CoS owns the lesson-ledger process. Grades do not rewrite published prose.                                                                          |

---

## Why this exists

Agents must not merely “write the 2027 NFL Draft preview.” They must know:

- What Kos Edge wrote before
- Which assumptions proved right / wrong / mixed
- What the **model** believed vs what the **market** believed
- What **lessons** were recorded afterward

Without this ledger, desks invent continuity. That is forbidden.

---

## Required-read on assignment (hard rule)

Before outline or draft on a recurring product:

1. Open `data/knowledge/<sport>/<product>/`.
2. Read all cards with `status: graded` for prior cycles (and open cards that still bind assumptions).
3. Read `GRADE_RUBRIC.md` if grading later in the cycle.
4. If the folder is empty or has only templates / EXAMPLE cards → record **`no prior grades`** and proceed without invented history.
5. CoS confirms the required-read happened before greenlighting the assignment.

Recurring products include (non-exhaustive): NFL draft preview, NFL season preview / guide, NFL week preview, NFL futures, CFB week preview, and any other product that repeats by season/week/cycle.

**Soft-pedaling required-read into optional is a process bug.**

---

## Claim card schema

File location: `data/knowledge/<sport>/<product>/<YYYY>-<slug>.md`  
(or `…/<cycle>-<slug>.md` when year alone is ambiguous)

YAML front matter + short body. Match `data/knowledge/claim-card-TEMPLATE.md`. Optional machine shape: `data/knowledge/claim-card.schema.json`.

| Field           | Required    | Notes                                                                                           |
| --------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| `id`            | yes         | Stable slug, e.g. `nfl-draft-2027-qb1-tier`                                                     |
| `status`        | yes         | `open` \| `graded` \| `void` \| `EXAMPLE` (`EXAMPLE` = format demo only — **not** real history) |
| `sport`         | yes         | `nfl` \| `cfb` \| …                                                                             |
| `product`       | yes         | `draft` \| `season-preview` \| `week-preview` \| `futures` \| …                                 |
| `event`         | yes         | Human label (e.g. `2027 NFL Draft`, `2026 NFL Week 3`)                                          |
| `as_of`         | yes         | ISO date or datetime; timezone **America/New_York** when time matters                           |
| `claim`         | yes         | One material desk claim — precise, gradeable                                                    |
| `house_view`    | yes         | Kos Edge / KEI / projections view **or** `no house print`                                       |
| `model_view`    | yes         | Model belief / pack stamp **or** `n/a`                                                          |
| `market_view`   | yes         | Street / consensus at as-of **or** `n/a`                                                        |
| `sot_class`     | yes         | Same spirit as fact gate: Kos Edge SoT / street / status / attribution / other documented class |
| `writer`        | yes         | Filing writer (or desk)                                                                         |
| `filed_by`      | yes         | Who filed the card (writer or CoS)                                                              |
| `grade`         | when graded | `right` \| `wrong` \| `mixed` \| `void` — **omit or null while open**; never invent             |
| `lesson`        | when graded | Short lesson after outcome; empty while open                                                    |
| `evidence`      | when graded | What outcome / source closes the grade                                                          |
| `graded_by`     | when graded | CoS and/or Riley-assisted                                                                       |
| `graded_as_of`  | when graded | When graded                                                                                     |
| `related_paths` | no          | Paths to published copy / packs (pointers only — do not rewrite those files under this SOP)     |
| `notes`         | no          | Process notes                                                                                   |

### Status meanings

| Status    | Meaning                                                                 |
| --------- | ----------------------------------------------------------------------- |
| `open`    | Claim filed; outcome not graded yet                                     |
| `graded`  | Grade + lesson recorded with evidence                                   |
| `void`    | Claim vacated (event cancelled, market never posted, scope error, etc.) |
| `EXAMPLE` | **Not real.** Format watermark only. Do not cite as history.            |

---

## Grade rubric (summary)

Full rubric: `data/knowledge/GRADE_RUBRIC.md`.

| Grade   | Use when                                                               |
| ------- | ---------------------------------------------------------------------- |
| `right` | Outcome clearly supports the claim as filed                            |
| `wrong` | Outcome clearly contradicts the claim as filed                         |
| `mixed` | Partially right / wrong; material caveats — lesson must say what split |
| `void`  | Ungradeable honestly (no market, event voided, claim malformed, etc.)  |

**Never invent a grade to “complete” a season.** Prefer leaving `open` until evidence exists.

---

## Who does what

| Role       | May do                                                                                         | Must not                                      |
| ---------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Writer** | File claim cards on NEW material desk claims; complete required-read before recurring products | Invent grades; rewrite published articles     |
| **Riley**  | Assist grades with evidence (numbers / outcomes); keep fact gate at publish                    | Edit voice; invent fills; invent grades       |
| **CoS**    | Owns ledger process; confirms required-read; closes / approves grades; merges ledger PRs       | Soft-pedal required-read; authorize fake past |
| **Ryan**   | Only if CoS (or explicit instruction) says so                                                  | Default ops path                              |

---

## Relationship to Editor Fact Gate

| Doc                   | When                         | Job                                                                    |
| --------------------- | ---------------------------- | ---------------------------------------------------------------------- |
| `EDITOR_FACT_GATE.md` | At publish (NEW copy)        | Trace claims to SoT; CLEAR or KICK BACK; never invent facts            |
| **This file**         | Across seasons / after event | Log claims; grade after outcomes; force prior lessons into next assign |

Fact-gate CLEAR does **not** create a grade. Grading happens **after** the event/season with evidence.

---

## Forward-only + later backfill

- **Tonight / from this lock:** empty product folders + templates + SOP. File **new** claim cards going forward.
- **Do not** invent 2024–2026 (or any) right/wrong grades to seed the ledger.
- **Later wave:** backfill only from **real** published sources and documented outcomes — separate CoS-approved work.

---

## Do not

- Invent grades or lessons for past seasons
- Edit `content/writers/**` under this SOP
- Treat EXAMPLE cards as institutional history
- Skip required-read because “the model remembers”
- Build a UI / app for the ledger in this foundation wave

---

## Integration

- Ledger home: `data/knowledge/README.md`
- Template: `data/knowledge/claim-card-TEMPLATE.md`
- Rubric: `data/knowledge/GRADE_RUBRIC.md`
- Schema: `data/knowledge/claim-card.schema.json`
- CoS note: `docs/writers/COS_INSTITUTIONAL_MEMORY.md`
- Writer OS: `.cursor/rules/ai-writer-team.mdc`
- Product bible pointer: `style-bible.md`
- Fact gate: `docs/writers/EDITOR_FACT_GATE.md`
