# ACCESS_BLOCKER — current_weekly_depth_db (t4615u re-kick)

Ticket: t4615u (authority DECISION_RYAN_t4608u 53572667 · parent e65b9c77 · order sha8 5b804203)
Filed: 2026-10-28T14:40:18Z
CERT_CANDIDATE: 0
Classification: ACCESS_BLOCKED

Prior STILL_BLOCKED fc9c97a8 tip 6bc1cf3f (wrong secret value). This re-kick: token still SET; CLI still Unauthorized.

## Verdict

`current_weekly_depth_db` remains ACCESS_BLOCKED.

Not RUNTIME_SECRET_MISSING: RAILWAY_TOKEN is SET (length 36, uuid-like). Railway CLI 5.71.0 still rejects it.

whoami / status / run all Unauthorized. No SET TRANSACTION READ ONLY session. No nfl_dp_* rows read. No rows invented. Option B not attempted.

This process still sees length=36 uuid-like — the same shape as the prior wrong value. If Ryan saved a replacement project token in Runtime Secrets after this VM booted, this long-running agent may not have received the new value (Cloud Agent secrets inject at start).

## Observed (no secrets)

1. RAILWAY_TOKEN SET length=36 (uuid-like; alnum+hyphen)
2. CLOUD_AGENT_INJECTED_SECRET_NAMES includes RAILWAY_TOKEN
3. DATABASE_URL UNSET; DATABASE_PUBLIC_URL UNSET
4. railway whoami → exit=1 Unauthorized
5. railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production → exit=1 Unauthorized
6. railway run --project … --service Postgres → exit=1 Unauthorized (child never started)
7. 127.0.0.1:5432 ConnectionRefused

## Redacted repro

```bash
python3 -c "import os; t=os.environ.get('RAILWAY_TOKEN'); print('RAILWAY_TOKEN', 'SET' if t else 'UNSET', 'length', len(t or ''))"
railway whoami
railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production
railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres -- python3 -c "import os; print('url_present', bool(os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')))"
```

Expected on this VM: TOKEN SET length 36; all three railway commands Unauthorized.

## CLOSED vs remaining

CLOSED: depth_sot_week · injury_paths_current · inseason_efficiency_current · week_schedule_kickoffs
REMAINING: current_weekly_depth_db (this file)

Completeness sha256 02ba06ac819486d478acfdcd30fb2b0015d6101b9ddccf32153a462cde937c70 (sha8 02ba06ac)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen
No Odds · no merge · no deploy · no DML/DDL · no Option B
