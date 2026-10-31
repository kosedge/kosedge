# t4838u — offline Independent Fair caller (DRAFT)

Engineering-only. Non-production. Fail-closed. **Not an E1 emit.**

Authority: DECISION_RYAN_t4838u `1aeb63ee926955109409bfbdb5cea79b7f940b50e5ddae6cf51bd1ccd4e9c17a`.

## Lineages (do not collapse)

| Identity | Token | Meaning |
|---|---|---|
| SOURCE ONLY | `52d9e909` @ `1b39f4e9` ratified `75d1b695` | `nfl_simulator.py` implementation reference. Not an operational caller authorization. Not the as-of identity. |
| ASOF | `PASS_ASOF_BOUNDARY cf514078` · tip `1010b86f` · module `7dc6afea` | Pregame lag rule. Distinct from `52d9e909`. |
| CONTRACT | `b41f4b43` / PASS_CONTRACT `1a53bbd3` | Input contract on file. **≠ DATA ACCEPT.** |
| W8 | DATA_PARTIAL 1/14 tip `ba9e8426` #663 | STANDBY. Do not invent. Do not delay that lane. |
| #666 ID repair | `ef209d35` | Acknowledged; out of scope here except as-of citation. |

## Invocation

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_caller_t4838u.py --dry-run --write-evidence
```

Operational `--invoke` consumes `b41f4b43` and fail-closes on missing through-W8 DATA ACCEPT, source pins, target-game ids, forecast cutoff, unavailable history, and incomplete required inputs. IF(blend=0). No sportsbook. No unapproved HL.

## Packet

`CALLER_PACKET.md` / `CALLER_PACKET.json` is **BLOCKED** until W8 DATA_READY + IMV through-W8 DATA ACCEPT + OWNER E1 CLEAR. Wiring success ≠ emit.

| Artifact | sha256 |
|---|---|
| CALLER_PACKET.md | `6ef4fae748cb2f93dc6ae141c1f1824f87f69308df91707f794a4b82d5887d80` |
| CALLER_PACKET.json | `d953f93f2bfb3da323b3f8e8f552f337b9504d47186eac9a1cd077b3019d76db` |
| DRY_RUN.json | `56759273fce688196f7436394d70bb834a05069f32acd687ba56063f626d8c3d` |

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10/Odds HOLD.

## t4850u EVAL_ONLY (same DRAFT)

Diagnostic W8 consume at rating_week=7 using through-W7 `c674da77` is sealed under `eval_w8_t4850u/`. That packet is **not** E1, **not** FREE_PUBLIC, and does **not** change through-W8 FAIL-CLOSED or this BLOCKED caller packet.
