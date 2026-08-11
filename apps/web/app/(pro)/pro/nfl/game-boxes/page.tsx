import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineGameBoxesClient from "@/components/pro/nfl/SeasonEngineGameBoxesClient";
import NflLineageBadge from "@/components/pro/nfl/NflLineageBadge";
import {
  fetchSeasonEngineStatus,
  loadSeasonEngineMatchups,
  seasonEnginePackagedNotice,
} from "@/lib/nfl-season-engine";
import {
  nflLaunchResearchDeskNotice,
  resolveActiveNflLineage,
} from "@/lib/nfl-launch-research";
import { resolveNflProjectionDefaultWeek } from "@/lib/nfl-board-week-label";

export const dynamic = "force-dynamic";

export default async function NflGameBoxesPage() {
  const [status, slate] = await Promise.all([
    fetchSeasonEngineStatus(),
    loadSeasonEngineMatchups({ season: 2026, daysAhead: 28 }),
  ]);
  const packagedNotice = seasonEnginePackagedNotice(status);
  const launchResearchNotice = nflLaunchResearchDeskNotice();
  const lineage = resolveActiveNflLineage({
    engineVersionOverride: status.engine_version,
  });

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Game Boxes"
      summary="Projected skill-player boxes for a future matchup — yards, TDs, receptions, INTs as median with p10–p90 bands. Optional star-out scenario. Preseason: pick any upcoming REG week — this is a projection desk, not a live betting board."
      badge="Season engine · game boxes"
      primaryHref="/pro/nfl/survivor"
      primaryLabel="Open Survivor"
      secondaryHref="/pro/nfl/model"
      secondaryLabel="Season Model hub"
    >
      <div className="mt-2 mb-4 flex flex-wrap items-center gap-3 text-xs">
        <Link
          href="/pro/nfl/model"
          className="font-medium text-kos-gold/90 hover:text-kos-gold"
        >
          ← Season Model
        </Link>
        <Link
          href="/pro/nfl/props"
          className="font-medium text-kos-text/65 hover:text-kos-text"
        >
          Props board →
        </Link>
        {lineage ? <NflLineageBadge lineage={lineage} /> : null}
      </div>

      {!status.error ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          {packagedNotice ? `${packagedNotice} · ` : ""}
          {status.mode || "—"} · {status.schedule_source || "schedule"}
          {status.schedule_game_count != null
            ? ` · ${status.schedule_game_count} REG`
            : ""}
          {status.depth_source || status.roster_source
            ? ` · depth ${status.depth_source || status.roster_source}`
            : ""}
          {status.depth_as_of || status.roster_as_of
            ? ` (as of ${status.depth_as_of || status.roster_as_of})`
            : ""}
          {status.engine_version ? ` · ${status.engine_version}` : ""}
        </p>
      ) : (
        <p className="mb-4 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          Engine status unavailable: {status.error}
        </p>
      )}
      {launchResearchNotice ? (
        <p className="mb-4 rounded-lg border border-kos-gold/25 bg-kos-gold/10 px-3 py-2 text-xs text-kos-text/80">
          {launchResearchNotice}
        </p>
      ) : null}

      {slate.error ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          Fair-lines slate unavailable ({slate.error}). Use team dropdowns
          below — wall-chart weeks still work.
        </p>
      ) : slate.matchups.length === 0 ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          No upcoming fair-lines matchups in window — pick teams and week
          manually.
        </p>
      ) : null}

      <SeasonEngineGameBoxesClient
        matchups={slate.matchups}
        defaultWeek={resolveNflProjectionDefaultWeek(slate.currentWeek)}
        engineVersion={status.engine_version || undefined}
        depthSource={status.depth_source || status.roster_source}
        depthAsOf={status.depth_as_of || status.roster_as_of}
      />
    </SportHubShell>
  );
}
