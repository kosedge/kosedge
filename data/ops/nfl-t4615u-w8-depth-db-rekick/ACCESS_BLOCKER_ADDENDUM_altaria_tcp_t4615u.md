# ACCESS_BLOCKER ADDENDUM — t4615u follow-up (same VM)

Filed: 2026-10-28T14:46:00Z
CERT_CANDIDATE: 0
Parent: ACCESS_BLOCKER a79f58f8 / tip d8356dcb
Classification: ACCESS_BLOCKED (unchanged)

User asked to unblock remaining `current_weekly_depth_db`. Additional authorized probes this turn; still no RO warehouse session.

## Still true

- RAILWAY_TOKEN SET length 36 uuid-like; railway whoami/status/run Unauthorized
- DATABASE_URL / DATABASE_PUBLIC_URL unset in process env
- Option B not attempted. No DML/DDL. No invented nfl_dp_* rows. No deploy.

## New facts (no secrets)

1. Railway MCP OAuth whoami OK (account kosedge). `list-variables` still names-only.
2. Production Postgres TCP proxy is `altaria.proxy.rlwy.net:10880` → 5432.
   DNS `66.33.22.220` (not 198.18.0.1). TCP OPEN from this VM.
3. railway-agent has no SQL execution tool; refused to open a DB session.
4. model-service public domain `model-service-production-e253.up.railway.app` returns HTTP 404
   (latest deployment FAILED 2026-08-29). Not redeployed (hard stop).
5. model-service-worker is live; no public domain / TCP proxy — cannot HTTP query from this VM.

Handshake still cannot start: public TCP is ready; credentials are not injectable via CLI token or MCP values.

## Remaining unblock (not executed here)

A new Cloud Agent boot after the replacement Runtime Secret is the process that can `railway run` with a CLI-accepted project token, then SET TRANSACTION READ ONLY.

NFL NO-GO · CERT=0 · no Odds · no merge · no F2 · no Option B
