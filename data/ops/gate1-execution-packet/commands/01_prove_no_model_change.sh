#!/usr/bin/env bash
# 01_prove_no_model_change.sh — wrapper touches only the two certification paths
set -euo pipefail

PARENT_SHA="${PARENT_SHA:-57347d888d2832a735bb826f6105c44b34d9cc72}"
NEW_SHA="${NEW_SHA:?NEW_SHA required (from 00_create_wrapper_commit.sh)}"

if [[ -n "${KOSEDGE_ROOT:-}" ]]; then
  cd "$KOSEDGE_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
fi

echo "=== git diff PARENT..NEW --stat ==="
git diff "${PARENT_SHA}..${NEW_SHA}" --stat

CHANGED="$(git diff --name-only "${PARENT_SHA}..${NEW_SHA}")"
EXPECTED=$'data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json\nservices/model-service/tests/test_nfl_clock_play_simulator.py'
if [[ "$CHANGED" != "$EXPECTED" ]]; then
  echo "FATAL: diff touches unexpected paths:" >&2
  echo "$CHANGED" >&2
  exit 1
fi
echo "OK: only the two wrapper paths changed"

echo "=== git diff PARENT..NEW -- services/model-service/src (must be empty) ==="
SRC_DIFF="$(git diff "${PARENT_SHA}..${NEW_SHA}" -- services/model-service/src)"
if [[ -n "$SRC_DIFF" ]]; then
  echo "FATAL: simulator/model source changed" >&2
  echo "$SRC_DIFF" >&2
  exit 1
fi
echo "OK: services/model-service/src unchanged"

hash_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    sha256sum "$path" | awk '{print $1}'
  else
    echo "MISSING:$path"
  fi
}

echo "=== content hashes unchanged vs parent (config / inputs / simulator module) ==="
for rel in \
  data/ops/nfl-clock-play-pre-entry-pass-rz/config.json \
  data/ops/nfl-clock-play-baseline-v1/inputs.json \
  services/model-service/src/services/nfl_clock_play_simulator.py
do
  H_PARENT="$(git rev-parse "${PARENT_SHA}:${rel}" 2>/dev/null || echo MISSING)"
  H_NEW="$(git rev-parse "${NEW_SHA}:${rel}" 2>/dev/null || echo MISSING)"
  echo "$rel parent_blob=$H_PARENT new_blob=$H_NEW"
  if [[ "$H_PARENT" != "$H_NEW" ]]; then
    echo "FATAL: $rel changed between PARENT and NEW" >&2
    exit 1
  fi
done

if [[ -f data/ops/nfl-clock-play-pre-entry-pass-rz/config.json ]]; then
  echo "config.json sha256=$(hash_file data/ops/nfl-clock-play-pre-entry-pass-rz/config.json)"
  echo "  expected 2b3a8ac22569206b620ad5efe4d5dfb8c3b848894eae33b0ae934d4f242812b1"
fi
if [[ -f data/ops/nfl-clock-play-baseline-v1/inputs.json ]]; then
  echo "inputs.json sha256=$(hash_file data/ops/nfl-clock-play-baseline-v1/inputs.json)"
  echo "  expected 982a5a03e4e519cbdc8f9a344000f8391f3a17a8a71e61dc8e4a8ce21afacf30"
fi

echo "NO_MODEL_CHANGE_PROVEN"
