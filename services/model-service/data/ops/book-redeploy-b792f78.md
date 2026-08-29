# Redeploy trigger — The Book #310

Commit `b792f78422e65e52028a1502e29d9a1f8507b0d7` built but Railway healthcheck
timed out (service unavailable during 2m window). Re-trigger deploy so e253
`/health` git_sha moves off da7d932 onto b792f78 (or later containing it).

No grader until that sha is live. No UI.
