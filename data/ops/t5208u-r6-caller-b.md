# t5218u R6 TIMING DELTA B — seal=cutoff=KO−60 (CERT=0)

OWNER 3130ee86 · Cos LAUNCH f7f9e5a4 · B ORDER 88bff537.
Preserve b587e548 tamper/provenance. Continue DRAFT #708 from 033a35e4.
SUPPORT only. No science EXEC.

A tip 54b08a30 artifacts: `data/ops/t5218u-r6-timing-delta/`

```
PYTHONPATH=services/model-service python3 scripts/nfl/t5208u-r6-caller-e2e.py
# EXIT 0
```

```
KICKOFF_AS_SEAL_REFUSED REFUSE_CUTOFF
TAMPER_READ_REFUSED REFUSE_TAMPER
TAMPER_SEAL_REFUSED REFUSE_TAMPER
ZERO_MODEL_CALLS_ON_REFUSE true
a_api call_r6_point_margin
a_tip 54b08a301cf824c79ee3203180a51e2d832bb6f9
means_source live call_r6_point_margin
a_calls 2
model_calls 2
replay_ok True
cutoff_utc 2018-10-14T16:00:00Z
seal_utc 2018-10-14T16:00:00Z
seal SYNTHETIC_2018_W05_KC_NE if=0.8675824382397918 q2=1.2472862060776504 c=1.057434322158721 seed=282632 id=0232c87d0c4d1a4422e7ed0c1f8b043ed31c0e9d45549d680df7ef7ca0ed10e2
INTEGRATION OK
```

assert seal_utc == cutoff_utc == kickoff−60 (`2018-10-14T16:00:00Z`). Kickoff-as-seal refused. Tamper/provenance kept.
