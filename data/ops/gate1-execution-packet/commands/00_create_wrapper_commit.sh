#!/usr/bin/env bash
# 00_create_wrapper_commit.sh — certification-only wrapper on frozen parent
# Cursor executor: run from a clean kosedge worktree. Do NOT redesign model.
set -euo pipefail

PARENT_SHA="57347d888d2832a735bb826f6105c44b34d9cc72"
BRANCH="gate1-cert-wrapper-57347d888"
PACKET_DIR="${PACKET_DIR:-}"
if [[ -z "$PACKET_DIR" ]]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PACKET_DIR="$(git rev-parse --show-toplevel)/data/ops/gate1-execution-packet"
  else
    PACKET_DIR="/workspace/gate1-execution-packet"
  fi
fi

if [[ -n "${KOSEDGE_ROOT:-}" ]]; then
  REPO_ROOT="$KOSEDGE_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
else
  echo "FATAL: set KOSEDGE_ROOT to kosedge checkout" >&2
  exit 1
fi
cd "$REPO_ROOT"

echo "PARENT_SHA=$PARENT_SHA"
git fetch origin "$PARENT_SHA" 2>/dev/null || true
git checkout --detach "$PARENT_SHA"
git checkout -B "$BRANCH"

mkdir -p data/ops/nfl-clock-play-pre-entry-pass-rz
cp "$PACKET_DIR/commit/certification_thresholds.json" \
  data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json

git apply --check "$PACKET_DIR/commit/test_assert.patch"
git apply "$PACKET_DIR/commit/test_assert.patch"

git add \
  data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json \
  services/model-service/tests/test_nfl_clock_play_simulator.py

STAGED="$(git diff --cached --name-only)"
EXPECTED=$'data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json\nservices/model-service/tests/test_nfl_clock_play_simulator.py'
if [[ "$STAGED" != "$EXPECTED" ]]; then
  echo "FATAL: unexpected staged paths:" >&2
  echo "$STAGED" >&2
  exit 1
fi

git commit -m "$(cat <<'MSG'
certification-only wrapper for Gate 1 at 57347d888

Add data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json
(Alex Rourke CERT_CONTRACT_READY thresholds; NOT +/-0.05; NOT fitted to SHA).

Restore stale GO vs PUNT test expectation at clock_seconds=350.0:
test_rz_q4_trail3_regulation_clock_blocks_early_fg_range_field_goal
assert "go" -> "punt". Keep 300/240 -> field_goal.

Does NOT clear Gate 1. No model/simulator source changes.
MSG
)"

NEW_SHA="$(git rev-parse HEAD)"
echo "NEW_SHA=$NEW_SHA"
echo "BRANCH=$BRANCH"
echo "WRAPPER_COMMIT_OK"
