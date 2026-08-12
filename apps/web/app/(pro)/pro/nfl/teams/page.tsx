import Link from "next/link";
import TeamIntelFilterBar from "@/components/pro/TeamIntelFilterBar";
import { buildMetricRankMaps } from "@/lib/intel-ranking";
import {
  fetchNflIntel,
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
} from "@/lib/nfl-intel";
import {
  buildTeamIntelHref,
  extractTeamCodes,
  filterTeamDirectory,
  NFL_TEAM_DIRECTORY,
  parseTeamIntelFilters,
  teamDisplayName,
} from "@/lib/nfl-team-intel";
import { assignTeamPreviewWriter } from "@/lib/team-research";
import { nflActualRecordColumnLabel, resolveNflTruthLabel } from "@/lib/nfl-truth-label";
import NflTruthStateBadge from "@/components/pro/nfl/NflTruthStateBadge";

export default async function NflTeamsIndexPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const rawSearch = await searchParams;
  const filters = parseTeamIntelFilters(rawSearch);
  const standings = await fetchNflIntel("standings", {
    season: filters.season,
    week: filters.week,
  });
  const stats = await fetchNflIntel("stats", {
    season: filters.season,
    week: filters.week,
  });

  const filteredDirectory = filterTeamDirectory(filters);
  const filteredSet = new Set(filteredDirectory.map((team) => team.code));
  const availableCodes = extractTeamCodes(standings.rows);
  const selectedCodes = availableCodes.filter((code) => filteredSet.has(code));
  const standingsRanks = buildMetricRankMaps(standings.rows, [
    "win_pct",
    "point_diff",
  ]);
  const statsRanks = buildMetricRankMaps(stats.rows, [
    "pass_rate",
    "epa_per_play_offense",
  ]);
  const standingsIndexByTeam = new Map(
    standings.rows
      .map((entry, index) => ({
        index,
        team: typeof entry.team === "string" ? entry.team : null,
      }))
      .filter((entry): entry is { index: number; team: string } =>
        Boolean(entry.team),
      )
      .map((entry) => [entry.team, entry.index] as const),
  );
  const statsIndexByTeam = new Map(
    stats.rows
      .map((entry, index) => ({
        index,
        team: typeof entry.team === "string" ? entry.team : null,
      }))
      .filter((entry): entry is { index: number; team: string } =>
        Boolean(entry.team),
      )
      .map((entry) => [entry.team, entry.index] as const),
  );
  const fallbackCodes =
    selectedCodes.length > 0
      ? selectedCodes
      : filteredDirectory.map((team) => team.code);

  const season = standings.season ?? filters.season ?? null;
  const week = standings.week ?? filters.week ?? null;
  const truth = resolveNflTruthLabel({
    season,
    week,
    fallbackApplied: Boolean(standings.selection?.fallback_applied),
    latestSeason: standings.selection?.latest_available?.season,
    latestWeek: standings.selection?.latest_available?.week,
  });
  const recordDt = nflActualRecordColumnLabel(truth);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <TeamIntelFilterBar
        title="NFL Team Intel"
        subtitle="Premium team intelligence index with fast lookup controls for week, conference, and division."
        basePath="/pro/nfl/teams"
        filters={filters}
        teamOptions={filteredDirectory.map((team) => ({
          code: team.code,
          name: team.name,
        }))}
      />

      <section className="mt-6 rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-6">
        <p className="text-xs uppercase tracking-[0.15em] text-kos-gold">
          Premium Team Intel Hub
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          Team Directory & Market Context
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-kos-text/75">
          Navigate from league context into team-level depth, availability, and
          split signals. Cards route directly to the team hub with selected
          season/week preserved.
        </p>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
          <NflTruthStateBadge state={truth.ui_state} />
          <span>
            {truth.period_line} · {fallbackCodes.length} teams in current filter
          </span>
        </p>
        {truth.honesty_note ? (
          <p className="mt-1 text-xs text-kos-gold/80">{truth.honesty_note}</p>
        ) : null}
      </section>

      {standings.error ? (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-200">
          {standings.error}
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {fallbackCodes.map((teamCode) => {
          const row = standings.rows.find((entry) => entry.team === teamCode);
          const statRow = stats.rows.find((entry) => entry.team === teamCode);
          const standingsIndex = standingsIndexByTeam.get(teamCode) ?? -1;
          const statsIndex = statsIndexByTeam.get(teamCode) ?? -1;
          const href = buildTeamIntelHref(teamCode, "overview", {
            season: season ?? undefined,
            week: truth.week ?? undefined,
          });
          const directoryEntry = NFL_TEAM_DIRECTORY.find(
            (entry) => entry.code === teamCode,
          );
          const previewAssignment = directoryEntry
            ? assignTeamPreviewWriter("nfl", {
                slug: directoryEntry.code.toLowerCase(),
                code: directoryEntry.code,
                name: directoryEntry.name,
                conference: directoryEntry.conference,
                division: directoryEntry.division,
              })
            : null;

          return (
            <Link
              key={teamCode}
              href={href}
              className="group rounded-2xl border border-white/10 bg-black/35 p-4 transition hover:border-kos-gold/45 hover:bg-black/45"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-kos-gold">
                    {teamCode}
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-kos-text">
                    {teamDisplayName(teamCode)}
                  </h2>
                  {directoryEntry ? (
                    <p className="mt-1 text-xs text-kos-text/55">
                      {directoryEntry.conference} {directoryEntry.division}
                      {previewAssignment ? " · KosEdge preview" : ""}
                    </p>
                  ) : null}
                </div>
                <span className="rounded-full border border-kos-gold/30 bg-kos-gold/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
                  Research
                </span>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-2 text-sm text-kos-text/80">
                <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                  <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                    {recordDt}
                  </dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {formatTeamRecordWithRank(
                      row,
                      standingsRanks.win_pct?.get(standingsIndex),
                    )}
                  </dd>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                  <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                    Point Diff
                  </dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {formatIntelValueWithRank(
                      row?.point_diff,
                      standingsRanks.point_diff?.get(standingsIndex),
                    )}
                  </dd>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                  <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                    Pass Rate
                  </dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {formatIntelValueWithRank(
                      statRow?.pass_rate,
                      statsRanks.pass_rate?.get(statsIndex),
                    )}
                  </dd>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                  <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                    Off EPA / Play
                  </dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {formatIntelValueWithRank(
                      statRow?.epa_per_play_offense,
                      statsRanks.epa_per_play_offense?.get(statsIndex),
                    )}
                  </dd>
                </div>
              </dl>
            </Link>
          );
        })}
      </section>

      {fallbackCodes.length === 0 ? (
        <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
          No teams match the selected filters yet. Clear
          conference/division/search constraints or switch season/week.
        </div>
      ) : null}
    </main>
  );
}
