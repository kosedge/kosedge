#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEASONS="${SEASONS:-2023,2024,2025,2026}"
MODEL_SERVICE_URL="${MODEL_SERVICE_URL:-http://127.0.0.1:8000}"
MODEL_VERSION="${MODEL_VERSION:-nfl-v1.5-matchup-sim}"

echo "[preseason] Running data ownership hardening for seasons=${SEASONS}"
(
  cd "${ROOT_DIR}/services/data-platform-nfl"
  PYTHONPATH=./src python3 -m data_platform_nfl.cli \
    --seasons "${SEASONS}" \
    --run-launch-hardening \
    --backup-include-row-exports \
    --backup-export-dir "${ROOT_DIR}/data/ops"
)

# Seeds team + player priors for the *last* season in SEASONS with the real
# full-prior-season average (not a single-week snapshot), a Super Bowl
# futures market anchor, and real historical draft-tier baselines for
# rookies -- see services/data-platform-nfl/src/data_platform_nfl/
# preseason_hydration.py. Idempotent and safe to re-run every offseason;
# never touches a week once real games have been played for it.
echo "[preseason] Bootstrapping preseason team/player priors"
(
  cd "${ROOT_DIR}/services/data-platform-nfl"
  PYTHONPATH=./src python3 -m data_platform_nfl.cli \
    --seasons "${SEASONS}" \
    --run-preseason-bootstrap
)

# Downstream rolling/matchup/projection features are derived FROM the
# situational + usage tables just hydrated above, so they must be rebuilt
# afterward or they'll keep serving whatever was materialized before this
# run (stale flat placeholders, or nothing at all for newly-added players).
echo "[preseason] Rematerializing matchup + player projection features"
(
  cd "${ROOT_DIR}/services/data-platform-nfl"
  PYTHONPATH=./src python3 -m data_platform_nfl.cli \
    --seasons "${SEASONS}" \
    --materialize-matchup-features --replace-matchup-features
  PYTHONPATH=./src python3 -m data_platform_nfl.cli \
    --seasons "${SEASONS}" \
    --materialize-player-projection-features --replace-player-projection-features
)

echo "[preseason] Kicking off launch hardening cycle for model=${MODEL_VERSION}"
curl --fail --silent --show-error \
  --request POST \
  "${MODEL_SERVICE_URL}/api/jobs/run-nfl-launch-hardening?model_version=${MODEL_VERSION}&days_ahead=45&outcomes_lookback_days=180&backtest_lookback_days=365&tuning_lookback_days=365&simulations=7000"

echo "[preseason] Completed bootstrap trigger"
