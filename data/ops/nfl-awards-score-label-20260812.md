# Awards labeling — score vs probability — 2026-08-12

**Decision:** MVP / OPOY `award_score` is a relative 0–1 model index (team success + stats + prior). It is **not** a constrained award probability. Product label is **Award Score** (0–100, no `%`). Do not softmax/normalize in the UI. True P(award) only if a later sim picks exactly one winner per path and the field sums to ~100%.
