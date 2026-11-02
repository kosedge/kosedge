# v2.6.7 — RD-4 PY pin (runbook v2.4.9)

Frozen: everything in v2.6.6, including runbook v2.4.8 and
`nfl-imv-v2.6.6-a3e80242-trace.md`. Do not edit them.

RD-4: Python interpreter is pinned out-of-band. IMV_PY,
IMV_PY_VERSION and IMV_PY_FREEZE_SHA are IMV-filed, same as
IMV_BUNDLE_SUMS_SHA. Never hardcoded.

| Item | Where |
| --- | --- |
| PY | `PY="${IMV_PY:?IMV pinned python required}"` immediately before each builder (P-5) |
| RD-4 | `test -x "$PY"`; version; pandas/pyarrow/numpy; pip-freeze sha |
