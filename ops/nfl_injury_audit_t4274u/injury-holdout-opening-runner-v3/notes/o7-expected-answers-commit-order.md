# Expected-answers commit order (opening-runner v3)

IMV `77d9c00a` shortest path item 1: file expected answers v3 first.
This package files expected answers (folds, producer, PASS rule, receipt
fields, rounding) plus the method and producer modules in a commit that
precedes the runner file. The commit hash is written to
`inputs/expected_answers_commit.txt` before the runner is added.

Git remains out of IMV method; this note is secondhand for IMV unless the
log embeds the expected-answers commit.
