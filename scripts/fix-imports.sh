#!/usr/bin/env bash
set -euo pipefail

echo "==> 1) Kill any running Next dev"
pkill -9 -f "next dev" || true

echo "==> 2) Remove broken barrel files that reference deleted folders"
rm -f apps/web/components/index.ts
rm -f apps/web/components/edge-board/index.ts
rm -f apps/web/components/pro/index.ts

echo "==> 3) Ensure canonical component files exist"
for f in apps/web/components/EdgeBoard.tsx apps/web/components/ProPricing.tsx apps/web/components/ProWelcomeHub.tsx; do
  if [ ! -f "$f" ]; then
    echo "MISSING: $f"
    exit 1
  fi
done

echo "==> 4) Fix imports to point directly to the real files"

# Home page: EdgeBoard
perl -0777 -i -pe 's@import\s+EdgeBoard\s+from\s+"@/components";@import EdgeBoard from "@/components/EdgeBoard";@g' apps/web/app/page.tsx

# Edge board page: EdgeBoard + type
perl -0777 -i -pe 's@import\s+EdgeBoard,\s*\{\s*type\s+EdgeBoardRow\s*\}\s+from\s+"@/components";@import EdgeBoard from "@/components/EdgeBoard";\nimport type { EdgeBoardRow } from "@/components/EdgeBoard";@g' apps/web/app/edge-board/page.tsx

echo "==> 5) Confirm no remaining barrel imports"
rg 'from "@/components"' apps/web/app -n || true

echo "==> 6) Clean caches"
rm -rf apps/web/.next apps/web/.turbo

echo "==> Done. Now run: pnpm dev:web"
