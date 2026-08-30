import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import TruePrDriversBoard from "@/components/pro/nfl/TruePrDriversBoard";
import { fetchSeasonEngineStatus } from "@/lib/nfl-season-engine";
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
    body: "Enter used teams, pick a future week, and rank remaining picks. This week % is KEI; path / save uses the season engine.",
  },
] as const;

export default async function NflSeasonModelHubPage() {
  const [status, truePr] = await Promise.all([
    fetchSeasonEngineStatus(),
    fetchTruePrProductSurface({ season: 2026, asOfWeek: 1 }),
  ]);

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Season Model"
      summary="True PR, Game Boxes, and Survivor on one engine."
      badge="Season Model"
      primaryHref="/pro/nfl/game-boxes"
      primaryLabel="Open Game Boxes"
      secondaryHref="/pro/nfl/survivor"
      secondaryLabel="Open Survivor"
    >
      {status.error ? (
        <p className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          Engine unavailable — retry.
        </p>
      ) : null}

      <TruePrDriversBoard surface={truePr} />

      <section className="mt-6 grid gap-3 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="min-h-11 rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50 active:border-kos-gold/50"
          >
            <h2 className="text-sm font-semibold text-kos-gold">
              {tool.title}
            </h2>
            <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
              {tool.body}
            </p>
          </Link>
        ))}
      </section>
    </SportHubShell>
  );
}
