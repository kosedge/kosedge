import { headers } from "next/headers";
import {
  fetchNflProductionReadiness,
  shouldShowNflPreseasonReadinessBanner,
} from "@/lib/nfl-production-readiness";

/**
 * When production readiness is no-go (typical preseason sample=0), surface an
 * explicit PRESEASON banner and remind that PLAY/survivor locks are off.
 */
export async function NflProductionReadinessBanner() {
  const pathname = (await headers()).get("x-pathname") || "";
  if (!pathname.includes("/pro/nfl") && !pathname.includes("/edge-board/nfl")) {
    return null;
  }

  const readiness = await fetchNflProductionReadiness();
  if (!shouldShowNflPreseasonReadinessBanner(readiness)) {
    return null;
  }

  const reasons = readiness.reasons?.length
    ? readiness.reasons.slice(0, 4).join(" · ")
    : "sample_size_ok";

  return (
    <div
      role="status"
      data-testid="nfl-preseason-readiness-banner"
      className="border-b border-sky-500/35 bg-sky-500/10 px-6 py-3 text-sm text-sky-50"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="font-medium tracking-tight">PRESEASON · production readiness no-go</p>
        <p className="text-sky-50/80">
          PLAY stake tags and survivor locks stay research-only until readiness
          is go. {reasons}
        </p>
      </div>
    </div>
  );
}
