# ACCESS_BLOCKER — current_weekly_depth_db (t4605u)

Ticket: t4605u P1 W8 pipeline restore
Filed: 2026-10-28T13:47:00Z
CERT_CANDIDATE: 0
Label: RESEARCH_ENG
Classification: ACCESS_BLOCKED

Authority:
- DECISION_RYAN_t4605u sha256 e65b9c7781a2f120dc6b6c0c1d171cce3b5daae31577edfcbc4a99eccff3d69a
- COS_ORDER_CURSOR_t4605u sha256 43d1702a1d26a649f2707dd3fcafe8174bd547bf617970decff8dfbfff267bc6
- PR shared-box blocker sha256 3bf02785b08e90565ccedddfdcd4ffde57ab840cd67df93fb072817834183f63 (CoS ACCEPT)
- Prior GAP-1 e9434b58 (198.18.0.1 transparent HTTP proxy)

## Verdict

`current_weekly_depth_db` remains ACCESS_BLOCKED.

Shared Grok Bot box: do not retry DATABASE_URL (PR 3bf02785 ACCEPTED).
This Cursor cloud VM: Unblock A attempted; warehouse RO query did not complete.
No warehouse rows invented.

## Shared box (do not retry)

PR_T4605U_RO_DATABASE_URL_ACCESS_BLOCKER 3bf02785:
- DATABASE_URL unset on emit VM
- 127.0.0.1:5432 ConnectionRefused
- railway run injects URLs but TCP lands on 198.18.0.1 (HTTP proxy); handshake times out or receives `H`
- Same root as GAP-1 e9434b58

## Unblock A on this Cursor cloud VM (2026-10-28T13:46Z)

Facts (no secrets printed):

1. Process env: DATABASE_URL unset; DATABASE_PUBLIC_URL unset; LAUNCH_RESEARCH_DATABASE_URL unset.
2. DNS: `maglev.proxy.rlwy.net` → `66.33.22.251` (NOT 198.18.0.1). `postgres.railway.internal` NXDOMAIN.
3. TCP from this VM:
   - maglev.proxy.rlwy.net:10880 OPEN (no banner)
   - maglev.proxy.rlwy.net:15432 OPEN (no banner)
   - maglev.proxy.rlwy.net:24747 OPEN (no banner)
   - maglev.proxy.rlwy.net:5432 TimeoutError
   - 198.18.0.1:5432 TimeoutError
4. railway CLI 5.71.0 installed. `RAILWAY_TOKEN` present. `railway whoami` / `railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres -- python3 probe.py` → Unauthorized.
5. Railway MCP `list-variables` is OAuth connected-app: names only, values hidden. Did not print or persist secrets.
6. No SET TRANSACTION READ ONLY session opened. No `nfl_dp_depth_chart_weekly` / injury nowcast rows read.

Implication: this VM has real public TCP to `*.proxy.rlwy.net` (unlike the shared box). The remaining wall is credential injection (`railway run` token unauthorized + no DATABASE_PUBLIC_URL in process env). Handshake was not completed.

## Repro (redacted)

```bash
echo "DATABASE_URL=${DATABASE_URL:-UNSET}"
echo "DATABASE_PUBLIC_URL=${DATABASE_PUBLIC_URL:-UNSET}"
getent hosts maglev.proxy.rlwy.net
python3 -c "import socket; s=socket.create_connection(('maglev.proxy.rlwy.net',10880),6); print('tcp_open'); s.close()"
railway whoami
railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres -- python3 -c 'print("url_present", bool(__import__("os").environ.get("DATABASE_PUBLIC_URL") or __import__("os").environ.get("DATABASE_URL")))'
```

Expected on this VM: DNS public IP; TCP 10880 open; railway Unauthorized; URLs unset.

## What is NOT claimed

- No warehouse weekly depth book for W8
- No invented nfl_dp_* rows
- No Odds · no merge · no F2 · no deploy · no CERT

## Escalation

Option B (box egress allowlist) is Needs Ryan for the shared box.
For this cloud VM: authorized `railway run` token (or injected DATABASE_PUBLIC_URL) is required to finish Unblock A. CoS / Platform Reliability.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen
