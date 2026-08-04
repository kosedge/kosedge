import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { fetchSeasonEngineStatus } from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

const TOOLS = [
  {
    href: "/pro/nfl/game-boxes",
    title: "Future Game Boxes",
    body: "Projected QB/RB/WR/TE boxes for a selected matchup — median with p10–p90 ranges, optional star-out scenario.",
  },
  {
    href: "/pro/nfl/survivor",
    title: "Survivor Helper",
    body: "Enter used teams, pick a future week, and rank remaining picks from season-path win rates (byes respected).",
  },
] as const;

export default async function NflSeasonModelHubPage() {
  const status = await fetchSeasonEngineStatus();
  const ready =
    !status.error &&
    status.mode === "real" &&
    (status.schedule_game_count ?? 0) >= 272 &&
    (status.depth_named_skill_teams ?? 0) >= 32;

  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Season Model"
      summary="Full-season engine for future game boxes and survivor path rankings. Edge Board and KEI stay on their own rails."
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
