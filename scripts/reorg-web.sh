#!/usr/bin/env bash
set -euo pipefail

WEB="apps/web"

if [[ ! -d "$WEB" ]]; then
  echo "❌ Expected $WEB to exist. Run this from repo root."
  exit 1
fi

echo "✅ Web app: $WEB"

mkdir -p "$WEB/components/ui" \
         "$WEB/components/pro" \
         "$WEB/components/edge-board" \
         "$WEB/components/layout" \
         "$WEB/lib/server" \
         "$WEB/lib/client" \
         "$WEB/lib/shared" \
         "$WEB/app/(marketing)" \
         "$WEB/app/(pro)" \
         "$WEB/app/(docs)"

# Move files if they exist (no-op otherwise)
[[ -f "$WEB/components/Container.tsx" ]]     && git mv "$WEB/components/Container.tsx"     "$WEB/components/layout/Container.tsx"     || true
[[ -f "$WEB/components/ArticleLayout.tsx" ]] && git mv "$WEB/components/ArticleLayout.tsx" "$WEB/components/layout/ArticleLayout.tsx" || true
[[ -f "$WEB/components/SiteHeader.tsx" ]]    && git mv "$WEB/components/SiteHeader.tsx"    "$WEB/components/layout/SiteHeader.tsx"    || true

[[ -f "$WEB/components/EdgeBoard.tsx" ]]     && git mv "$WEB/components/EdgeBoard.tsx"     "$WEB/components/edge-board/EdgeBoard.tsx" || true

[[ -f "$WEB/components/ProPricing.tsx" ]]    && git mv "$WEB/components/ProPricing.tsx"    "$WEB/components/pro/ProPricing.tsx"       || true
[[ -f "$WEB/components/ProWelcomeHub.tsx" ]] && git mv "$WEB/components/ProWelcomeHub.tsx" "$WEB/components/pro/ProWelcomeHub.tsx"    || true

# Route group move (URLs do NOT change)
[[ -d "$WEB/app/pro" && ! -d "$WEB/app/(pro)/pro" ]] && git mv "$WEB/app/pro" "$WEB/app/(pro)/pro" || true
[[ -d "$WEB/app/insights" && ! -d "$WEB/app/(docs)/insights" ]] && git mv "$WEB/app/insights" "$WEB/app/(docs)/insights" || true

# Fix imports (requires ripgrep)
command -v rg >/dev/null 2>&1 || { echo "❌ ripgrep (rg) not found. Install: brew install ripgrep"; exit 1; }

rg -l 'from "@/components/EdgeBoard"' "$WEB"      | xargs -I{} perl -pi -e 's@from "@/components/EdgeBoard"@from "@/components/edge-board/EdgeBoard"@g' {} 2>/dev/null || true
rg -l 'from "@/components/ProPricing"' "$WEB"     | xargs -I{} perl -pi -e 's@from "@/components/ProPricing"@from "@/components/pro/ProPricing"@g' {} 2>/dev/null || true
rg -l 'from "@/components/ProWelcomeHub"' "$WEB"  | xargs -I{} perl -pi -e 's@from "@/components/ProWelcomeHub"@from "@/components/pro/ProWelcomeHub"@g' {} 2>/dev/null || true

rg -l 'from "@/components/SiteHeader"' "$WEB"     | xargs -I{} perl -pi -e 's@from "@/components/SiteHeader"@from "@/components/layout/SiteHeader"@g' {} 2>/dev/null || true
rg -l 'from "@/components/Container"' "$WEB"      | xargs -I{} perl -pi -e 's@from "@/components/Container"@from "@/components/layout/Container"@g' {} 2>/dev/null || true
rg -l 'from "@/components/ArticleLayout"' "$WEB"  | xargs -I{} perl -pi -e 's@from "@/components/ArticleLayout"@from "@/components/layout/ArticleLayout"@g' {} 2>/dev/null || true

# Ensure ProPricing is client if it uses window/document/onClick
PR="$WEB/components/pro/ProPricing.tsx"
if [[ -f "$PR" ]]; then
  if ! head -n 3 "$PR" | rg -q 'use client'; then
    tmp="$(mktemp)"
    printf '%s\n\n' '"use client";' > "$tmp"
    cat "$PR" >> "$tmp"
    mv "$tmp" "$PR"
    git add "$PR" || true
  fi
fi

echo "✅ Reorg done."
echo "Run: pnpm -C apps/web dev"
