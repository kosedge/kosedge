import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineSurvivorShell from "@/components/pro/nfl/SeasonEngineSurvivorShell";
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

export const dynamic = "force-dynamic";

export default async function NflSurvivorPage() {
  const [status, slate] = await Promise.all([
    fetchSeasonEngineStatus(),
    loadSeasonEngineMatchups({ season: 2026, daysAhead: 14 }),
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
      title="Survivor"
      summary="Plan the full slate week-by-week with matchups, slate grade, path SOS, and suggested paths. Harder schedule ≠ weaker team — SOS moves outlook / E[wins] path grades only. Locked teams stay burned. Preseason: use future REG weeks — season-path planner, not a live weekly betting board."
      badge="Season engine · survivor"
      primaryHref="/pro/nfl/game-boxes"
      primaryLabel="Open Game Boxes"
      secondaryHref="/wall-chart/nfl-2026"
      secondaryLabel="Wall Chart"
    >
      <div className="mt-2 mb-4 flex flex-wrap items-center gap-3 text-xs">
        <Link
          href="/pro/nfl/model"
          className="font-medium text-kos-gold/90 hover:text-kos-gold"
        >
          ← Season Model
        </Link>
        <Link
          href="/wall-chart/nfl-2026"
          className="font-medium text-kos-text/65 hover:text-kos-text"
        >
          Wall Chart →
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
          {Array.isArray(status.capabilities) &&
          status.capabilities.includes("survivor_planner")
            ? " · planner ready"
            : ""}
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

      <SeasonEngineSurvivorShell
        defaultWeek={
          slate.currentWeek && slate.currentWeek >= 1 && slate.currentWeek < 18
            ? slate.currentWeek
            : 1
        }
        engineVersion={status.engine_version || undefined}
        depthSource={status.depth_source || status.roster_source}
        depthAsOf={status.depth_as_of || status.roster_as_of}
        defaultMode="planner"
      />
    </SportHubShell>
  );
}
