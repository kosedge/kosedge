import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import TruePrDriversBoard from "@/components/pro/nfl/TruePrDriversBoard";
import NflLineageBadge from "@/components/pro/nfl/NflLineageBadge";
import {
  fetchSeasonEngineStatus,
  isSeasonEngineReady,
  seasonEnginePackagedNotice,
} from "@/lib/nfl-season-engine";
import { nflLaunchResearchDeskNotice, resolveActiveNflLineage } from "@/lib/nfl-launch-research";
import { fetchTruePrProductSurface } from "@/lib/nfl-true-pr";

export const dynamic = "force-dynamic";

const TOOLS = [
  {
    href: "/pro/nfl/game-boxes",
    title: "Game Boxes",
    body: "Projected QB/RB/WR/TE boxes for a selected matchup — median with typical range (low–high), optional star-out scenario.",
  },
  {
    href: "/pro/nfl/survivor",
    title: "Survivor",
    body: "Enter used teams, pick a future week, and rank remaining picks from season-path win rates (byes respected).",
  },
] as const;

export default async function NflSeasonModelHubPage() {
  const [status, truePr] = await Promise.all([
    fetchSeasonEngineStatus(),
    fetchTruePrProductSurface({ season: 2026, asOfWeek: 1 }),
  ]);
  const ready = isSeasonEngineReady(status);
  const packagedNotice = seasonEnginePackagedNotice(status);
  const deskNotice = nflLaunchResearchDeskNotice();
  const lineage = resolveActiveNflLineage({
    engineVersionOverride: status.engine_version || truePr.engine_version,
  });

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Season Model"
      summary="True PR, Game Boxes, and Survivor on one engine."
      badge="NFL season engine"
      primaryHref="/pro/nfl/game-boxes"
      primaryLabel="Open Game Boxes"
      secondaryHref="/pro/nfl/survivor"
      secondaryLabel="Open Survivor"
    >
      {lineage ? (
        <div className="-mt-2 mb-4">
          <NflLineageBadge lineage={lineage} />
          {deskNotice ? (
            <p className="mt-1.5 text-[11px] leading-snug text-kos-text/45">{deskNotice}</p>
          ) : null}
        </div>
      ) : null}

      <TruePrDriversBoard surface={truePr} />

      <section className="mt-6 grid gap-3 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="min-h-11 rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50 active:border-kos-gold/50"
          >
            <h2 className="text-sm font-semibold text-kos-gold">{tool.title}</h2>
            <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
              {tool.body}
            </p>
          </Link>
        ))}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 px-4 py-4 text-sm text-kos-text/70">
        <div className="flex flex-wrap items-center gap-2">
          <p>
            Live engine:{" "}
            <span className="font-semibold text-kos-text">
              {status.engine_version || "unreachable"}
            </span>
          </p>
          {status.error ? (
            <span className="rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-xs text-red-200">
              {status.error}
            </span>
          ) : ready ? (
            <span className="rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-200/90">
              Ready for use
            </span>
          ) : (
            <span className="rounded-md border border-amber-500/25 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-100/90">
              Check status details
            </span>
          )}
          {packagedNotice && !status.error ? (
            <span className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-kos-text/70">
              {packagedNotice}
            </span>
          ) : null}
        </div>
        {!status.error ? (
          <dl className="mt-3 grid gap-2 text-xs text-kos-text/65 sm:grid-cols-2">
            <div>
              <dt className="text-kos-text/45">Schedule</dt>
              <dd className="mt-0.5 text-kos-text/80">
                {status.mode || "—"} · {status.schedule_source || "—"}
                {status.schedule_game_count != null
                  ? ` · ${status.schedule_game_count} REG`
                  : ""}
                {status.schedule_as_of ? ` · as of ${status.schedule_as_of}` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-kos-text/45">Depth / roster</dt>
              <dd className="mt-0.5 text-kos-text/80">
                {status.depth_source || status.roster_source || "—"}
                {status.depth_as_of || status.roster_as_of
                  ? ` · as of ${status.depth_as_of || status.roster_as_of}`
                  : ""}
                {status.depth_named_skill_teams != null
                  ? ` · ${status.depth_named_skill_teams}/32 named skill`
                  : ""}
              </dd>
            </div>
          </dl>
        ) : null}
        <p className="mt-3 text-xs text-kos-text/50">
          Proxied through Next.js BFF — browser never calls Railway with secrets.
          Full-season simulate and raw diagnostics remain API/CLI only for now.
        </p>
      </section>
    </SportHubShell>
  );
}
