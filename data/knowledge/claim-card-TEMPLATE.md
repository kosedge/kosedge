# Claim card template

Copy to `data/knowledge/<sport>/<product>/<YYYY>-<slug>.md`.  
Fill real fields only. Leave `grade` / `lesson` / `evidence` empty while `status: open`.  
**Never invent grades.**

---

```yaml
---
id: sport-product-year-slug
status: open # open | graded | void | EXAMPLE
sport: nfl # nfl | cfb | …
product: draft # draft | season-preview | week-preview | futures | …
event: "YYYY Product label"
as_of: "YYYY-MM-DD" # America/New_York when time matters
claim: ""
house_view: "" # or "no house print"
model_view: "" # or "n/a"
market_view: "" # or "n/a"
sot_class: "" # Kos Edge SoT | street | status | attribution | other
writer: ""
filed_by: ""
grade: null # right | wrong | mixed | void — only when graded; never invent
lesson: ""
evidence: ""
graded_by: ""
graded_as_of: ""
related_paths: []
notes: ""
---
```

## Claim (one sentence)

>

## Context (optional)

-

## Grade / lesson (fill only after outcome)

- **Grade:**
- **Lesson:**
- **Evidence:**
