# v2.6.5 — 81e3c5cb closures (runbook v2.4.7)

Frozen: everything in v2.6.4, including runbook v2.4.6 and
`nfl-imv-v2.6.3-e3ae3984-trace.md`. That v2.6.3 trace wrongly claims
`cd "$PRE_RETRO"` was already on the B-1 `-c` line. It was not. T-1
puts it on the command in v2.4.7:

`cd "$PRE_RETRO" && awk '/^EVERY_FILE/{f=1;next} f&&NF==2' "$DESK" | shasum -a 256 -c`

| Item | Where |
| --- | --- |
| B-3 | first line after `set -euo pipefail` is `: "${IMV_SEAL_ACK_W4:?IMV ack required}"` (W5/W6/W8 in the other seal blocks). Shared `IMV_STORE_ACK_OK` removed. |
| PIN | `SUMS="$SRC/SHA256SUMS"` full sha `3f8b33a2299b2a1f8554aaeff92e3769fabca95447dd2fcb7ba04ba64a92fb24`; sub-SUMS a63150b5 and 5d64a848; copy loop and `shasum -a 256 -c` over 3f8b33a2; check-pins `--sums "$SUMS" --sums-v25 "$SUMS_V25"` |
| E-1 | L7 at all 5 instances: `test -f ... \|\| exit 7; git ... --error-unmatch ... >/dev/null` |
| T-1 | `cd "$PRE_RETRO" &&` on the awk \| shasum -c line |
| W-1 | `nfl-imv-deviation-register-rd1-erratum.md` |
