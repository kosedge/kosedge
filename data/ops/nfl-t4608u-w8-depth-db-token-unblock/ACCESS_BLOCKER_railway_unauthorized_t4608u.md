# ACCESS_BLOCKER — current_weekly_depth_db (t4608u)

Ticket: t4608u (parent t4605u)
Filed: 2026-10-28T14:34:19Z
CERT_CANDIDATE: 0
Classification: ACCESS_BLOCKED

Authority:
- DECISION_RYAN_t4608u sha256 5357266707b5555e96b746dce91435f862884db92b2124215f0d65d9ac435904
- COS_ORDER_CURSOR_t4608u sha256 889fd7643226953bb6bd7d0eb867a157abe840c45966b4df5537249f8c1f16ad
- Prior ACCESS_BLOCKER t4605u sha256 125b264a2456d2701924f01e44c8ea18c892775bd2e10eeadd93bbca979a6065
- Completeness sha256 02ba06ac819486d478acfdcd30fb2b0015d6101b9ddccf32153a462cde937c70 (sha8 02ba06ac)

## Verdict

`current_weekly_depth_db` remains ACCESS_BLOCKED.

RAILWAY_TOKEN is present in this cloud VM environment (Cloud Agent secret injected; SET; length 36; uuid-like shape). Railway CLI 5.71.0 rejects it: whoami, status, and run all Unauthorized.

No SET TRANSACTION READ ONLY session. No nfl_dp_* rows read. No rows invented. Option B not attempted.

## Observed (no secrets)

1. RAILWAY_TOKEN SET length=36
2. DATABASE_URL UNSET; DATABASE_PUBLIC_URL UNSET
3. CLOUD_AGENT_INJECTED_SECRET_NAMES includes RAILWAY_TOKEN (names only)
4. `railway whoami` → exit=1 Unauthorized
5. `railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production` → exit=1 Unauthorized
6. `railway run --project … --service Postgres -- python3 -c 'print(url_present …)'` → exit=1 Unauthorized
7. 127.0.0.1:5432 ConnectionRefused
8. Railway MCP still names-only (values hidden)

## Redacted repro

```bash
python3 -c "import os; t=os.environ.get('RAILWAY_TOKEN'); print('RAILWAY_TOKEN', 'SET' if t else 'UNSET', 'length', len(t or ''))"
railway whoami
railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production
railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres -- python3 -c "import os; print('url_present', bool(os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')))"
```

Expected on this VM: TOKEN SET length 36; all three railway commands Unauthorized; url_present never printed (run does not start).

## CLOSED vs remaining

CLOSED: depth_sot_week · injury_paths_current · inseason_efficiency_current · week_schedule_kickoffs
REMAINING: current_weekly_depth_db (this file)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen
No Odds · no merge · no deploy · no DML/DDL · no Option B
