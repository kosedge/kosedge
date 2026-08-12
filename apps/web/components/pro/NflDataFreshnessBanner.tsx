import { headers } from "next/headers";
import {
  fetchNflDataFreshness,
  isNflSeasonEngineDeskPath,
  shouldShowNflDataFreshnessBanner,
} from "@/lib/nfl-data-freshness";
import { formatNflFreshnessPeriod } from "@/lib/nfl-truth-label";

export async function NflDataFreshnessBanner() {
  const pathname = (await headers()).get("x-pathname");
  // Season-engine desks key readiness off /nfl/season-engine/status (packaged OK).
  if (isNflSeasonEngineDeskPath(pathname)) {
    return null;
  }

  const freshness = await fetchNflDataFreshness();
  if (!shouldShowNflDataFreshnessBanner(freshness)) {
    return null;
  }

  const blockers = freshness.blockers?.length
    ? freshness.blockers.slice(0, 4).join(" · ")
    : freshness.error || "owned data freshness check failed";

  const period = formatNflFreshnessPeriod(
    freshness.season,
    freshness.week,
  );

  return (
    <div
      role="status"
      className="border-b border-amber-500/40 bg-amber-500/10 px-6 py-3 text-sm text-amber-100"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="font-medium tracking-tight">
          Data freshness degraded
          {period ? ` · ${period}` : ""}
        </p>
        <p className="text-amber-100/80">
          Boards may use last owned snapshots. PLAY stake tags should be treated
          as research-only until freshness recovers. {blockers}
        </p>
      </div>
    </div>
  );
}
