import Link from "next/link";
import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { fetchNflIntel } from "@/lib/nfl-intel";
import { fetchEspnNflStandings } from "@/lib/nfl-espn-schedule";
import { resolveConferenceDivision } from "@/lib/nfl-team-intel";

export const dynamic = "force-dynamic";

export default async function StandingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams: Promise<{ season?: string; week?: string; team?: string }>;
}) {
  const { sport } = await params;
  const filters = await searchParams;
  if (sport !== "nfl") notFound();
  const parsedSeason = Number(filters.season);
  const season =
    Number.isFinite(parsedSeason) &&
    parsedSeason >= 2010 &&
    parsedSeason <= 2100
      ? parsedSeason
      : undefined;
  const parsedWeek = Number(filters.week);
  const week =
    Number.isFinite(parsedWeek) && parsedWeek >= 1 && parsedWeek <= 25
      ? parsedWeek
      : undefined;
  const team =
    typeof filters.team === "string" && filters.team.trim().length > 0
      ? filters.team.trim().toUpperCase()
      : undefined;

  const intel = await fetchNflIntel("standings", { season, week, team });
  if (intel.count > 0) {
    return (
      <NflIntelTablePage
        endpoint="standings"
        title="NFL Team Intel · Standings"
        description="Derived weekly standings from completed schedule results."
        emptyHint="Standings intel is not available yet for the selected season/week."
        season={season}
        week={week}
        team={team}
        columns={[
          { key: "team", label: "Team" },
          { key: "record", label: "Record" },
          { key: "win_pct", label: "Pct" },
          { key: "points_for", label: "PF" },
          { key: "points_against", label: "PA" },
          { key: "point_diff", label: "Diff" },
          { key: "conference", label: "Conf" },
          { key: "division", label: "Div" },
        ]}
      />
    );
  }

  // Offseason / empty intel: show prior-season final standings from ESPN.
  const priorSeason = season && season < 2026 ? season : 2025;
  const espnRows = await fetchEspnNflStandings(priorSeason);
  const filtered = team
    ? espnRows.filter((row) => row.team === team)
    : espnRows;

  const byDivision = new Map<string, typeof filtered>();
  for (const row of filtered) {
    const resolved = resolveConferenceDivision(row.team);
    const confDiv = resolved
      ? `${resolved.conference} ${resolved.division}`
      : row.conference || "League";
    const list = byDivision.get(confDiv) ?? [];
    list.push(row);
    byDivision.set(confDiv, list);
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
            NFL Standings
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-kos-text/75">
            <span className="font-semibold text-kos-gold/90">
              Offseason fallback · {priorSeason} final
            </span>
            . 2026 weekly intel tables are empty until games complete — this is
            not a live 2026 table. Use projections for race context.
          </p>
          <p className="mt-2 text-xs text-kos-text/60">
            Season {priorSeason} final · {filtered.length} teams · source ESPN ·
            switches to model intel automatically when rows exist
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            Back to NFL Overview
          </Link>
          <Link
            href="/pro/nfl/projections"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            2026 projections
          </Link>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
          Standings are temporarily unavailable from both model intel and ESPN
          fallback.
        </div>
      ) : (
        <div className="mt-8 space-y-6">
          {[...byDivision.entries()].map(([label, rows]) => (
            <section
              key={label}
              className="overflow-x-auto rounded-2xl border border-white/10 bg-black/30"
            >
              <div className="border-b border-white/10 px-4 py-3 text-sm font-semibold text-kos-gold">
                {label}
              </div>
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr>
                    <th className="px-4 py-2">Team</th>
                    <th className="px-4 py-2">Record</th>
                    <th className="px-4 py-2">Pct</th>
                    <th className="px-4 py-2">PF</th>
                    <th className="px-4 py-2">PA</th>
                    <th className="px-4 py-2">Diff</th>
                  </tr>
                </thead>
                <tbody>
                  {rows
                    .slice()
                    .sort((a, b) => b.win_pct - a.win_pct)
                    .map((row) => (
                      <tr
                        key={row.team}
                        className="border-t border-white/5 text-kos-text/85"
                      >
                        <td className="px-4 py-2 font-medium">
                          <Link
                            href={`/pro/nfl/teams/${row.team}/overview`}
                            className="hover:text-kos-gold"
                          >
                            {row.team}
                          </Link>
                        </td>
                        <td className="px-4 py-2">{row.record}</td>
                        <td className="px-4 py-2">
                          {row.win_pct.toFixed(3)}
                        </td>
                        <td className="px-4 py-2">{row.points_for}</td>
                        <td className="px-4 py-2">{row.points_against}</td>
                        <td className="px-4 py-2">
                          {row.point_diff > 0 ? "+" : ""}
                          {row.point_diff}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
