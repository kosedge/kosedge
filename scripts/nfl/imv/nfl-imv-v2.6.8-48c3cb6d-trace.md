# v2.6.8 — 48c3cb6d F-1 / F-2 / F-3 (runbook v2.4.10)

Frozen: everything in v2.6.7, including runbook v2.4.9,
builder 2.4.1, sealer 2.4, and `nfl-imv-v2.6.7-rd4-trace.md`.
Do not edit them.

F-1/F-2: five RD-4 lines in every build and every seal block;
PATH pin puts `dirname` of IMV_PY first; `command -v python3`
resolves to it; version and freeze sha re-checked. Shells stay
frozen. F-3: `nfl-imv-deviation-register-rd4.md`.

| Item | Where |
| --- | --- |
| RD-4 | five lines after B-3 first line in each seal; already in each build |
| PATH | `PYBIN` + `export PATH` + `command -v` + version/freeze re-check |
| RD-4 register | W4 OUT `w4-20261022T184946Z` BUILD_BLOCKED; never reused |
