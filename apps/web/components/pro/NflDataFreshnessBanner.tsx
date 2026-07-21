import { fetchNflDataFreshness } from "@/lib/nfl-data-freshness";

export async function NflDataFreshnessBanner() {
  const freshness = await fetchNflDataFreshness();
  if (freshness.status === "ok") {
    return null;
  }

  const blockers = freshness.blockers?.length
    ? freshness.blockers.slice(0, 4).join(" · ")
    : freshness.error || "owned data freshness check failed";

  return (
    <div
      role="status"
      className="border-b border-amber-500/40 bg-amber-500/10 px-6 py-3 text-sm text-amber-100"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="font-medium tracking-tight">
          Data freshness degraded
          {freshness.season != null && freshness.week != null
            ? ` · S${freshness.season} W${freshness.week}`
            : ""}
        </p>
        <p className="text-amber-100/80">
          Boards may use last owned snapshots. PLAY stake tags should be treated as research-only
          until freshness recovers. {blockers}
        </p>
      </div>
    </div>
  );
}
