# CoS note — t4902u IF compression diagnosis

**Assignment:** OWNER t4902u standing ops · read-only compression diagnosis  
**Product:** NFL Independent Fair vs current_post_seal market (W8)  
**Prior grades:** **no prior grades** in `data/knowledge/` for this IF-compression product. Forward-only. No invented history.

## One-screen

Sealed IF (`6ca03716`, blend=0, rating_week=7) is pulled toward pick'em vs DraftKings. TEN@CIN Δspread **+8.06**, IND@JAX **+6.36**, ARI@DAL **+4.62** (IF − market; positive = IF less home-bullish).

**Verdict:** **B primary** (designed W-L shrinkage + EPA attenuation + RZ regression + IF contract zeros) · **C secondary** (intact pipeline, low discrimination) · **A rejected** as causal (signs/units/HFA/blend clean) · **DATA_PARTIAL / week-7 rejected** as causal (correct vintage for W8).

Eng self-label `CONDITIONAL_DIAG`. Alex RO later. ≠edge ≠CLV ≠betting. NFL NO-GO CERT=0.

Math/feature/weight/blend change → **Ryan escalate only**. This PR does not implement any.

## Locks

- Do not merge as a model change.
- Do not ungate E1 / FREE_PUBLIC / CERT.
- Do not retune to a sportsbook.
