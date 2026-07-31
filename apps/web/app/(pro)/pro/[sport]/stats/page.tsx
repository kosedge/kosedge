import Link from "next/link";
import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { fetchNflIntel } from "@/lib/nfl-intel";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";
import { teamDisplayName } from "@/lib/nfl-team-intel";

export const dynamic = "force-dynamic";

export default async function StatsPage({
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

  const intel = await fetchNflIntel("stats", { season, week, team });
  if (intel.count > 0) {
    return (
      <NflIntelTablePage
        endpoint="stats"
        title="NFL Team Intel · Stats"
        description="Weekly situational team profile merged with derived standings context."
        emptyHint="Stats intel is not available yet for the selected season/week."
        season={season}
        week={week}
        team={team}
        columns={[
          { key: "team", label: "Team" },
          { key: "record", label: "Record" },
          { key: "pass_rate", label: "Pass Rate" },
          { key: "early_down_pass_rate", label: "Early Pass" },
          { key: "red_zone_td_rate", label: "RZ TD Rate" },
          { key: "epa_per_play_offense", label: "Off EPA/Play" },
          { key: "epa_per_play_defense_allowed", label: "Def EPA Allowed" },
        ]}
      />
    );
  }

  const bundle = loadLatestNflPreseasonBundle2026();
  let rows = bundle?.teamRows ?? [];
  if (team) rows = rows.filter((row) => row.team === team);
  rows = rows
    .slice()
    .sort((a, b) => b.expectedWins - a.expectedWins || b.playoffProb - a.playoffProb);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
            NFL League Stats
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-kos-text/75">
            Weekly EPA / pass-rate intel is empty in the offseason. Showing 2026
            preseason simulation strength table until in-season stats materialize.
          </p>
          <p className="mt-2 text-xs text-kos-text/60">
            Bundle {bundle?.bundleDirName ?? "unavailable"} · {rows.length}{" "}
            teams
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
            Full projections hub
          </Link>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
          League stats unavailable — neither intel tables nor the preseason
          simulation bundle loaded.
        </div>
      ) : (
        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
              <tr>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Conf / Div</th>
                <th className="px-4 py-3">Exp wins</th>
                <th className="px-4 py-3">Win p10–p90</th>
                <th className="px-4 py-3">Playoff %</th>
                <th className="px-4 py-3">Division %</th>
                <th className="px-4 py-3">SB %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.team}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-4 py-3 font-medium">
                    <Link
                      href={`/pro/nfl/teams/${row.team}/overview`}
                      className="hover:text-kos-gold"
                    >
                      {teamDisplayName(row.team)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-kos-text/65">
                    {row.conference} {row.division}
                  </td>
                  <td className="px-4 py-3">{row.expectedWins.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    {row.winsP10}–{row.winsP90}
                  </td>
                  <td className="px-4 py-3">
                    {(row.playoffProb * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {(row.divisionTitleProb * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {(row.superBowlWinProb * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
