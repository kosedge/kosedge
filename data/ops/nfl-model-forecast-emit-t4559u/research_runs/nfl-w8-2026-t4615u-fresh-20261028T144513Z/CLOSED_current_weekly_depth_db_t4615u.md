# CLOSED — current_weekly_depth_db (t4615u fresh VM Unblock A)

Ticket: t4615u (authority DECISION_RYAN_t4608u 53572667 · parent e65b9c77)
Filed: 2026-10-28T14:45:13Z
CERT_CANDIDATE: 0
Classification: CLOSED

Prior ACCESS_BLOCKER a79f58f8 tip d8356dcb (long-lived VM Unauthorized). This fresh VM: RAILWAY_TOKEN SET; railway status/run authorized; whoami Unauthorized is expected for a project-scoped token.

## Verdict

`current_weekly_depth_db` is CLOSED.

SET TRANSACTION READ ONLY session opened via `railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres`. SELECT only depth/injury nowcast tables. No DML/DDL. No invented nfl_dp_* rows. Option B not attempted.

## Warehouse rows read (counts only)

- nfl_dp_depth_chart_weekly: n=23256 teams=32 max_week=8 (W8 n=2907 / 32 teams)
- nfl_dp_official_depth_charts: n=3171 teams=32 max_week=1
- nfl_dp_injuries: n=734 teams=32 max_week=3
- warehouse_rows_read: 27161

Packaged injury_paths_current remains the W7 designated file. Warehouse injury nowcast is not invented forward from week 3.

## Observed (no secrets)

1. RAILWAY_TOKEN SET length 36 (uuid-like; alnum+hyphen)
2. DATABASE_URL UNSET in process env; DATABASE_PUBLIC_URL UNSET in process env
3. railway whoami → exit=1 Unauthorized (project token)
4. railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production → exit=0 (Postgres Online)
5. railway run … --service Postgres → exit=0 url_present True; RO SELECT used DATABASE_PUBLIC_URL host_kind=proxy
6. 127.0.0.1:5432 ConnectionRefused (unused)

## CLOSED vs remaining

CLOSED: depth_sot_week · injury_paths_current · current_weekly_depth_db · week_schedule_kickoffs · inseason_efficiency_current
REMAINING: none

Completeness sha256 675e1cf74341c53fb218d87715cb3441eff8196935531c713b1508ef9e8c8088 (sha8 675e1cf7)
RO probe sha256 f50ba2f07df9f92cba0ddf31fd5003f549d5e114eb3eddff0e245ef8f68c18ff (sha8 f50ba2f0)

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen
No Odds · no merge · no deploy · no DML/DDL · no Option B
