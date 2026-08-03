import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineSurvivorClient from "@/components/pro/nfl/SeasonEngineSurvivorClient";
import {
  fetchSeasonEngineStatus,
  loadSeasonEngineMatchups,
} from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

export default async function NflSurvivorPage() {
  const [status, slate] = await Promise.all([
    fetchSeasonEngineStatus(),
    loadSeasonEngineMatchups({ season: 2026, daysAhead: 14 }),
  ]);

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Survivor Helper"
      summary="Mark teams already used, choose a future week, and rank remaining picks from path-coherent season sims."
      badge="Season engine · survivor"
      primaryHref="/pro/nfl/game-boxes"
      primaryLabel="Game Boxes"
      secondaryHref="/wall-chart/nfl-2026"
      secondaryLabel="Wall Chart"
    >
      <div className="mt-2 mb-4 flex flex-wrap gap-3 text-xs">
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
      </div>

      <SeasonEngineSurvivorClient
        defaultWeek={slate.currentWeek && slate.currentWeek >= 1 ? slate.currentWeek : 1}
        engineVersion={status.engine_version || undefined}
      />
    </SportHubShell>
  );
}
