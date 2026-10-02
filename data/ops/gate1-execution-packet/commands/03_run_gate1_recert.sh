#!/usr/bin/env bash
# 03_run_gate1_recert.sh — exact Gate 1 recert sequence under CONTRACT thresholds
# Apply CONTRACT abs_delta_max (NOT +/-0.05). Do NOT clear Gate 1 if FG hard gate fails.
set -euo pipefail

PARENT_SHA="${PARENT_SHA:-57347d888d2832a735bb826f6105c44b34d9cc72}"
NEW_SHA="${NEW_SHA:?NEW_SHA required}"
PACKET_DIR="${PACKET_DIR:-}"
if [[ -z "$PACKET_DIR" ]]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PACKET_DIR="$(git rev-parse --show-toplevel)/data/ops/gate1-execution-packet"
  else
    PACKET_DIR="/workspace/gate1-execution-packet"
  fi
fi
RECEIPT_DIR="/tmp/gate1-recert-${NEW_SHA}"
mkdir -p "$RECEIPT_DIR"

if [[ -n "${KOSEDGE_ROOT:-}" ]]; then
  cd "$KOSEDGE_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
fi

export PYTHONPATH="${PYTHONPATH:-}:services/model-service"
CONFIG="data/ops/nfl-clock-play-pre-entry-pass-rz/config.json"
INPUTS="data/ops/nfl-clock-play-baseline-v1/inputs.json"
THRESHOLDS="data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json"
PBP_DEFAULT="${PBP_PATH:-}"

echo "=== 1) focused GO/PUNT pytest ==="
python3 -m pytest -q \
  services/model-service/tests/test_nfl_clock_play_simulator.py::test_rz_q4_trail3_regulation_clock_blocks_early_fg_range_field_goal \
  | tee "$RECEIPT_DIR/pytest-focused.txt"

echo "=== 2) full simulator pytest suite ==="
python3 -m pytest -q services/model-service/tests/test_nfl_clock_play_simulator.py \
  | tee "$RECEIPT_DIR/pytest-full.txt"

echo "=== 3) freeze via run_clock_play_baseline_v1.py ==="
python3 scripts/nfl/run_clock_play_baseline_v1.py \
  --config "$CONFIG" \
  --inputs "$INPUTS" \
  --output-dir "$RECEIPT_DIR/freeze" \
  --source-sha "$NEW_SHA" \
  | tee "$RECEIPT_DIR/freeze.log"

echo "=== 4) certify_clock_play_v1_1.py ==="
CERTIFY_ARGS=(
  --config "$CONFIG"
  --inputs "$INPUTS"
  --output "$RECEIPT_DIR/certify-v1_1.json"
)
if [[ -n "$PBP_DEFAULT" && -f "$PBP_DEFAULT" ]]; then
  CERTIFY_ARGS+=(--historical-pbp "$PBP_DEFAULT")
fi
python3 scripts/nfl/certify_clock_play_v1_1.py "${CERTIFY_ARGS[@]}" \
  | tee "$RECEIPT_DIR/certify.log"

echo "=== 5) denom receipt if script present ==="
if [[ -f scripts/nfl/build_clock_play_red_zone_denominator_receipt.py ]]; then
  DENOM_ARGS=(--output "$RECEIPT_DIR/train-denominator.json")
  if [[ -n "$PBP_DEFAULT" && -f "$PBP_DEFAULT" ]]; then
    DENOM_ARGS+=(--pbp "$PBP_DEFAULT")
  fi
  python3 scripts/nfl/build_clock_play_red_zone_denominator_receipt.py "${DENOM_ARGS[@]}" \
    | tee "$RECEIPT_DIR/denom.log" \
    || echo "WARN: denom script exited non-zero; see denom.log" | tee -a "$RECEIPT_DIR/denom.log"
else
  echo "denom script not present; skip" | tee "$RECEIPT_DIR/denom.log"
fi

echo "=== 6) apply CONTRACT thresholds (NOT +/-0.05) to hard-gate table ==="
python3 "$PACKET_DIR/commands/apply_contract_thresholds.py" \
  "$THRESHOLDS" \
  "$PACKET_DIR/hard_gate_precompute.json" \
  "$RECEIPT_DIR"

echo "RECEIPT_DIR=$RECEIPT_DIR"
echo "RECERT_SEQUENCE_COMPLETE"
ls -la "$RECEIPT_DIR"
