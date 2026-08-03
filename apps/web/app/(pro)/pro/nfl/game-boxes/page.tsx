import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineGameBoxesClient from "@/components/pro/nfl/SeasonEngineGameBoxesClient";
import {
  fetchSeasonEngineStatus,
  loadSeasonEngineMatchups,
} from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

export default async function NflGameBoxesPage() {
  const [status, slate] = await Promise.all([
    fetchSeasonEngineStatus(),
    loadSeasonEngineMatchups({ season: 2026, daysAhead: 28 }),
  ]);

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Future Game Boxes"
      summary="Select a future matchup and read projected player box scores from the season engine — yards, TDs, receptions, INTs with p50 and p10–p90 ranges."
      badge="Season engine · game boxes"
      primaryHref="/pro/nfl/survivor"
      primaryLabel="Survivor Helper"
      secondaryHref="/pro/nfl/model"
      secondaryLabel="Season Model hub"
    >
      <div className="mt-2 mb-4 flex flex-wrap gap-3 text-xs">
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
      </div>

      {slate.error ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          Fair-lines slate unavailable ({slate.error}). Use team dropdowns
          below.
        </p>
      ) : slate.matchups.length === 0 ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          No upcoming fair-lines matchups in window — pick teams manually.
        </p>
      ) : null}

      <SeasonEngineGameBoxesClient
        matchups={slate.matchups}
        defaultWeek={slate.currentWeek ?? 1}
        engineVersion={status.engine_version || undefined}
      />
    </SportHubShell>
  );
}
