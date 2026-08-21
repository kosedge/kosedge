import { Suspense } from "react";
import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import SeasonEngineSurvivorShell from "@/components/pro/nfl/SeasonEngineSurvivorShell";
import NflLineageBadge from "@/components/pro/nfl/NflLineageBadge";
import {
  fetchSeasonEngineStatus,
  seasonEnginePackagedNotice,
} from "@/lib/nfl-season-engine";
import {
  nflLaunchResearchDeskNotice,
  resolveActiveNflLineage,
} from "@/lib/nfl-launch-research";

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

async function SurvivorStatusStrip() {
  const status = await withTimeout(
    fetchSeasonEngineStatus(),
    4000,
    {
      engine_version: "",
      error: "Engine warming — status timed out. Planner is still usable.",
    },
  );
  const packagedNotice = seasonEnginePackagedNotice(status);
  const lineage = resolveActiveNflLineage({
    engineVersionOverride: status.engine_version,
  });

  return (
    <>
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
        <p className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          {status.error}
        </p>
      )}
    </>
  );
}

export default function NflSurvivorPage() {
  const launchResearchNotice = nflLaunchResearchDeskNotice();

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
      <Suspense
        fallback={
          <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/55">
            Loading engine status…
          </p>
        }
      >
        <SurvivorStatusStrip />
      </Suspense>
      {launchResearchNotice ? (
        <p className="mb-4 rounded-lg border border-kos-gold/25 bg-kos-gold/10 px-3 py-2 text-xs text-kos-text/80">
          {launchResearchNotice}
        </p>
      ) : null}

      <SeasonEngineSurvivorShell defaultWeek={1} defaultMode="planner" />
    </SportHubShell>
  );
}
