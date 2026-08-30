import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineGameBoxesClient from "@/components/pro/nfl/SeasonEngineGameBoxesClient";
import {
  fetchSeasonEngineStatus,
  loadSeasonEngineMatchups,
} from "@/lib/nfl-season-engine";
import { resolveNflProjectionDefaultWeek } from "@/lib/nfl-board-week-label";

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
      title="Game Boxes"
      summary="Projected skill-player boxes for a matchup — median with typical range."
      badge="Game Boxes"
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
        <Link
          href="/pro/nfl/survivor"
          className="font-medium text-kos-text/65 hover:text-kos-text"
        >
          Survivor →
        </Link>
      </div>

      {status.error ? (
        <p className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          Engine unavailable — retry.
        </p>
      ) : null}

      {slate.error ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          Fair-lines slate unavailable. Use team dropdowns below — wall-chart
          weeks still work.
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
      />
    </SportHubShell>
  );
}
