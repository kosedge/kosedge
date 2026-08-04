import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { fetchSeasonEngineStatus } from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

const TOOLS = [
  {
    href: "/pro/nfl/game-boxes",
    title: "Future Game Boxes",
    body: "Projected QB/RB/WR/TE boxes for a selected matchup — p50 with p10–p90 ranges.",
  },
  {
    href: "/pro/nfl/survivor",
    title: "Survivor Helper",
    body: "Enter used teams, pick a future week, and rank picks from season-path win rates.",
  },
] as const;

export default async function NflSeasonModelHubPage() {
  const status = await fetchSeasonEngineStatus();

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Season Model"
      summary="First UI exposure of the full-season engine — game-level player boxes and survivor path rankings. Edge Board and KEI stay unchanged."
      badge="NFL season engine"
      primaryHref="/pro/nfl/game-boxes"
      primaryLabel="Open Game Boxes"
      secondaryHref="/pro/nfl/survivor"
      secondaryLabel="Open Survivor"
    >
      <section className="mt-6 grid gap-3 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50"
          >
            <h2 className="text-sm font-semibold text-kos-gold">{tool.title}</h2>
            <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
              {tool.body}
            </p>
          </Link>
        ))}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 px-4 py-4 text-sm text-kos-text/70">
        <p>
          Live engine:{" "}
          <span className="font-semibold text-kos-text">
            {status.engine_version || "unreachable"}
          </span>
          {status.error ? (
            <span className="text-red-300"> — {status.error}</span>
          ) : null}
        </p>
        {!status.error ? (
          <p className="mt-2 text-xs text-kos-text/60">
            Mode: {status.mode || "—"}
            {status.schedule_source ? ` · ${status.schedule_source}` : ""}
            {status.schedule_game_count != null
              ? ` · ${status.schedule_game_count} REG games`
              : ""}
            {status.roster_source ? ` · roster ${status.roster_source}` : ""}
            {status.roster_as_of ? ` (as of ${status.roster_as_of})` : ""}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-kos-text/50">
          Proxied through Next.js BFF routes — browser never calls Railway with
          secrets. Full-season simulate and raw diagnostics remain API/CLI only
          for now.
        </p>
      </section>
    </SportHubShell>
  );
}
