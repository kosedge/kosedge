#!/usr/bin/env bash
# 02_bind_hashes.sh — echo PARENT_SHA, NEW_SHA, and key content hashes
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

if [[ -n "${KOSEDGE_ROOT:-}" ]]; then
  cd "$KOSEDGE_ROOT"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
fi

hash_file() { sha256sum "$1" | awk '{print $1}'; }

CERT_PATH="data/ops/nfl-clock-play-pre-entry-pass-rz/certification_thresholds.json"
CONFIG_PATH="data/ops/nfl-clock-play-pre-entry-pass-rz/config.json"
INPUTS_PATH="data/ops/nfl-clock-play-baseline-v1/inputs.json"

echo "PARENT_SHA=$PARENT_SHA"
echo "NEW_SHA=$NEW_SHA"
echo "certification_thresholds.json sha256=$(hash_file "$CERT_PATH")"
echo "  packet_commit_copy_sha256=$(hash_file "$PACKET_DIR/commit/certification_thresholds.json")"
echo "config.json sha256=$(hash_file "$CONFIG_PATH")"
echo "  expected_config_sha256=2b3a8ac22569206b620ad5efe4d5dfb8c3b848894eae33b0ae934d4f242812b1"
echo "inputs.json sha256=$(hash_file "$INPUTS_PATH")"
echo "  expected_inputs_sha256=982a5a03e4e519cbdc8f9a344000f8391f3a17a8a71e61dc8e4a8ce21afacf30"
echo "pbp_sha256_expected=823304baa68961187307c1d08774bee80a58d9757ee57be01f6879b34c5bca2c"
echo "seed_manifest_sha256_expected=46de6deb6fde81d366aa8191e48e4e58e9938abe0be576fa9f60efe5c7cfcad2"
echo "HASH_BIND_OK"
