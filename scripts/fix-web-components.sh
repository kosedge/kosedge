#!/usr/bin/env bash
set -euo pipefail

WEB="apps/web"

echo "==> Ensure component folders exist"
mkdir -p "$WEB/components/edge-board" "$WEB/components/pro"

pick_and_move () {
  # Usage: pick_and_move <srcA> <srcB> <dest>
  # Picks whichever exists and is larger (bytes), then moves/copies into dest.
  local a="$1"
  local b="$2"
  local dest="$3"

  local size_a=0
  local size_b=0

  [[ -f "$a" ]] && size_a=$(wc -c <"$a" | tr -d ' ')
  [[ -f "$b" ]] && size_b=$(wc -c <"$b" | tr -d ' ')

  if [[ $size_a -eq 0 && $size_b -eq 0 ]]; then
    echo "!! Missing both: $a and $b"
    return 0
  fi

  local src="$a"
  if [[ $size_b -gt $size_a ]]; then
    src="$b"
  fi

  echo "==> Using: $src  ->  $dest"
  mkdir -p "$(dirname "$dest")"
  # copy then remove to avoid cross-device issues
  cp -f "$src" "$dest"
}

echo "==> Normalize EdgeBoard location"
pick_and_move \
  "$WEB/components/EdgeBoard.tsx" \
  "$WEB/components/edge-board/EdgeBoard.tsx" \
  "$WEB/components/edge-board/EdgeBoard.tsx"

echo "==> Normalize ProPricing location"
pick_and_move \
  "$WEB/components/ProPricing.tsx" \
  "$WEB/components/pro/ProPricing.tsx" \
  "$WEB/components/pro/ProPricing.tsx"

echo "==> Normalize ProWelcomeHub location"
pick_and_move \
  "$WEB/components/ProWelcomeHub.tsx" \
  "$WEB/components/pro/ProWelcomeHub.tsx" \
  "$WEB/components/pro/ProWelcomeHub.tsx"

echo "==> Remove duplicate root-level component files (single source of truth)"
rm -f \
  "$WEB/components/EdgeBoard.tsx" \
  "$WEB/components/ProPricing.tsx" \
  "$WEB/components/ProWelcomeHub.tsx" || true

echo "==> Write enterprise-grade barrel exports"

cat > "$WEB/components/edge-board/index.ts" <<'EOT'
export { default as EdgeBoard } from "./EdgeBoard";
export type { EdgeBoardRow } from "./EdgeBoard";
EOT

cat > "$WEB/components/pro/index.ts" <<'EOT'
export { default as ProPricing } from "./ProPricing";
export { default as ProWelcomeHub } from "./ProWelcomeHub";
EOT

cat > "$WEB/components/index.ts" <<'EOT'
export * from "./edge-board";
export * from "./pro";
EOT

echo "==> Fix imports (stop importing default from '@/components')"

# Home page: must import named EdgeBoard now
if rg -q 'import EdgeBoard from "@/components";' "$WEB/app/page.tsx"; then
  perl -0777 -i -pe 's/import EdgeBoard from "@\/components";/import { EdgeBoard } from "@\/components";/g' "$WEB/app/page.tsx"
fi

# If any file imports default from "@/components/EdgeBoard", normalize to "@/components"
# (this keeps it consistent long term)
rg -l 'from "@/components/EdgeBoard"' "$WEB/app" "$WEB/components" 2>/dev/null \
  | xargs -I{} perl -0777 -i -pe 's/from "@\/components\/EdgeBoard"/from "@\/components"/g; s/import EdgeBoard, \{ type EdgeBoardRow \}/import { EdgeBoard, type EdgeBoardRow }/g; s/import EdgeBoard \{ type EdgeBoardRow \}/import { EdgeBoard, type EdgeBoardRow }/g; s/import EdgeBoard/import { EdgeBoard }/g' {} || true

# Pro pages: normalize ProPricing/ProWelcomeHub imports to barrel
rg -l 'from "@/components/ProPricing"' "$WEB/app" 2>/dev/null \
  | xargs -I{} perl -0777 -i -pe 's/import ProPricing from "@\/components\/ProPricing";/import { ProPricing } from "@\/components";/g' {} || true

rg -l 'from "@/components/ProWelcomeHub"' "$WEB/app" 2>/dev/null \
  | xargs -I{} perl -0777 -i -pe 's/import ProWelcomeHub from "@\/components\/ProWelcomeHub";/import { ProWelcomeHub } from "@\/components";/g' {} || true

echo
echo "==> Sanity check: show component tree + key files"
find "$WEB/components" -maxdepth 2 -type f -name "*.ts" -o -name "*.tsx" | sed 's#^# - #'
echo
echo "✅ Components normalized. Next: restart dev server."
