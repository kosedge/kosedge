# v2.6.3 — e3ae3984 closures (runbook v2.4.5)

Frozen: everything in v2.6.2, including runbook v2.4.4 and rd-p2.
No Mac run. No parity evidence. Items 1, 3, 5, 6, 7 stayed closed.

| Item | Where |
| --- | --- |
| B-1 | hash Desktop manifest vs `4c287d5b…`; quoted conversion `awk '/^EVERY_FILE/{f=1;next} f&&NF==2' "$DESK"`; `cd "$PRE_RETRO" && … \| shasum -a 256 -c`; `chmod -R a-w` |
| B-2 | seven checks verbatim; `WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3`; repeated before each build |
| B-3 | each build block ends at box copy; seal starts with `: "${IMV_SEAL_ACK_<WEEK>:?IMV ack required}"` |
| PIN | both SUMS full sha `a63150b5…` and `5d64a848…`; check-pins `--sums` (a63150b5) + `--sums-v25` |
| cond. 7 | `a BLOCKED build is not sealed; a BLOCKED seal still seals and is reported BLOCKED.` |
| RD-1 | runbook says **absent**; check is `test ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)"` |
| O-4 | W4 and W5 each get their own seal and tar, the same as W6 |
