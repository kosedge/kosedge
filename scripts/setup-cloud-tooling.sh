#!/usr/bin/env bash
# Install deploy CLIs for Cursor Cloud agents when tokens are present.
# Secrets are set in: https://cursor.com/dashboard/cloud-agents
set -euo pipefail

echo "==> Kos Edge cloud tooling setup"

# Prefer a user-writable npm prefix (cloud agents often lack root for /usr/lib).
NPM_GLOBAL_PREFIX="${NPM_GLOBAL_PREFIX:-$HOME/.npm-global}"
mkdir -p "$NPM_GLOBAL_PREFIX/bin"
npm config set prefix "$NPM_GLOBAL_PREFIX" >/dev/null
export PATH="$NPM_GLOBAL_PREFIX/bin:$PATH"

npm_install_global() {
  local pkg="$1"
  npm install -g "$pkg"
}

if [[ -n "${VERCEL_TOKEN:-}" ]]; then
  if ! command -v vercel >/dev/null 2>&1; then
    echo "Installing Vercel CLI..."
    npm_install_global "vercel@latest"
  fi
  echo "Vercel CLI ready (VERCEL_TOKEN present)"
else
  echo "Skipping Vercel CLI (set VERCEL_TOKEN in Cursor Cloud secrets)"
fi

if [[ -n "${RAILWAY_TOKEN:-}" ]]; then
  if ! command -v railway >/dev/null 2>&1; then
    echo "Installing Railway CLI..."
    npm_install_global "@railway/cli@latest"
  fi
  echo "Railway CLI ready (RAILWAY_TOKEN present)"
else
  echo "Skipping Railway CLI (set RAILWAY_TOKEN in Cursor Cloud secrets)"
fi

if command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI ready"
else
  echo "GitHub CLI not found on PATH"
fi

echo "==> Cloud tooling setup complete"
