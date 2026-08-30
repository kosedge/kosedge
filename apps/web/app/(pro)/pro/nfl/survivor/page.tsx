import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineSurvivorShell from "@/components/pro/nfl/SeasonEngineSurvivorShell";
import { fetchSeasonEngineStatus } from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

async function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  fallback: T,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((resolve) => {
        timer = setTimeout(() => resolve(fallback), ms);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export default async function NflSurvivorPage() {
  const status = await withTimeout(fetchSeasonEngineStatus(), 4000, {
    engine_version: "",
    error: "Planner unavailable — retry.",
  });

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Survivor"
      summary="Plan remaining teams week-by-week. This week % is KEI; path / save uses the season engine."
      badge="Survivor"
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
        <Link
          href="/pro/nfl/game-boxes"
          className="font-medium text-kos-text/65 hover:text-kos-text"
        >
          Game Boxes →
        </Link>
      </div>
      {status.error ? (
        <p className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          {/timed out|warming/i.test(status.error)
            ? "Planner unavailable — retry."
            : status.error}
        </p>
      ) : null}

      <SeasonEngineSurvivorShell defaultWeek={1} defaultMode="planner" />
    </SportHubShell>
  );
}
