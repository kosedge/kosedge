#!/usr/bin/env bash
set -euo pipefail
BASE="${MODEL_SERVICE_URL:-https://model-service-production-e253.up.railway.app}"
curl -sS -m 90 "${BASE}/nfl/fair-lines?days_ahead=120&limit=500" -o /tmp/fair-before-full.json
python3 - <<'PY'
import json
items=json.load(open('/tmp/fair-before-full.json')).get('lines') or []
dates=sorted({it['game_date'] for it in items if it.get('game_date')})
print('unique_dates', len(dates))
open('/tmp/fair_dates.txt','w').write('\n'.join(dates))
sides={}
for it in items:
    key=(it.get('game_date'), it.get('away_abbr'), it.get('home_abbr'))
    s=it.get('spread_home'); ms=it.get('market_spread_home')
    if s is None or ms is None:
        continue
    model_side='HOME' if s<0 else ('AWAY' if s>0 else 'PICK')
    mkt_side='HOME' if ms<0 else ('AWAY' if ms>0 else 'PICK')
    sides[str(key)]=(model_side, mkt_side, s, ms)
json.dump(sides, open('/tmp/sides_before.json','w'))
print('snapshotted', len(sides))
PY

ok_n=0
fail_n=0
while IFS= read -r d; do
  [[ -z "$d" ]] && continue
  TASK=$(curl -sS -m 120 -X POST "${BASE}/api/jobs/run-nfl-simulations?game_date=${d}&simulations=4000")
  TID=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["task_id"])' "$TASK")
  ok=0
  for _ in $(seq 1 40); do
    sleep 5
    RES=$(curl -sS -m 30 "${BASE}/api/jobs/${TID}")
    STATE=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("state"))' "$RES")
    if [[ "$STATE" == "SUCCESS" ]]; then
      BID=$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("result") or {}).get("worker_build_id"))' "$RES")
      echo "OK $d build=$BID"
      ok=1
      ok_n=$((ok_n+1))
      break
    fi
    if [[ "$STATE" == "FAILURE" ]]; then
      echo "FAIL $d"
      fail_n=$((fail_n+1))
      ok=0
      break
    fi
  done
  if [[ "$ok" != "1" && "$STATE" != "FAILURE" ]]; then
    echo "TIMEOUT $d"
    fail_n=$((fail_n+1))
  fi
done < /tmp/fair_dates.txt
echo "DONE ok=$ok_n fail=$fail_n"
