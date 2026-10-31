#!/usr/bin/env bash
# U3 / C1 — paid Odds host may appear only in apps/web/lib/odds-acquire.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v git >/dev/null 2>&1; then
  echo "git required for odds-acquire choke scan" >&2
  exit 1
fi
hits="$(
  git grep -n -I -e 'the-odds-api\.com' -- \
    'apps/web' \
    ':!apps/web/lib/odds-acquire/' \
    ':!apps/web/scripts/' \
    ':!*.md' \
    ':!apps/web/.env.example' \
    ':!apps/web/__tests__/' \
    || true
)"
if [ -n "$hits" ]; then
  echo "the-odds-api.com must live only in apps/web/lib/odds-acquire:" >&2
  echo "$hits" >&2
  exit 1
fi
echo "Odds acquire choke scan passed."
