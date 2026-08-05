import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import DepthChartRenderer from "@/components/pro/DepthChartRenderer";
import InjuryStatusPanel from "@/components/pro/InjuryStatusPanel";
import TeamIntelFilterBar from "@/components/pro/TeamIntelFilterBar";
import TeamIntelSectionNav from "@/components/pro/TeamIntelSectionNav";
import TeamIntelStatCards from "@/components/pro/TeamIntelStatCards";
import TeamPreviewSlot from "@/components/pro/team-research/TeamPreviewSlot";
import TeamTendencyPanels, {
  type SituationTabKey,
} from "@/components/pro/TeamTendencyPanels";
import { buildMetricRankMaps } from "@/lib/intel-ranking";
import {
  fetchNflIntel,
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
  type NflIntelResponseRow,
} from "@/lib/nfl-intel";
import {
  buildTrendSnippets,
  extractTeamCodes,
  firstQueryValue,
  isNflDirectoryTeamCode,
  isNflTeamIntelView,
  NFL_TEAM_DIRECTORY,
  normalizeTeamCode,
  parseTeamIntelFilters,
  resolveTeamCode,
  teamDisplayName,
} from "@/lib/nfl-team-intel";
import {
  fetchNflQbSituationalSplits,
  fetchNflTeamTendencyProfileResolved,
  type QbSituationType,
  type TendencyPerspective,
} from "@/lib/nfl-tendencies";
import { assignTeamPreviewWriter } from "@/lib/team-research";

const SITUATION_TAB_KEYS: SituationTabKey[] = [
  "down_distance",
  "score_state",
  "field_position",
];
const QB_SITUATION_KEYS: QbSituationType[] = [
  "down_type",
  "pressure",
  "score_state",
  "field_position",
];

type TeamIntelTableProps = {
  title: string;
  rows: NflIntelResponseRow[];
  comparisonRows?: NflIntelResponseRow[];
  columns: Array<{ key: string; label: string }>;
  empty: string;
};

function TeamIntelTable({
  title,
  rows,
  comparisonRows,
  columns,
  empty,
}: TeamIntelTableProps) {
  const rankingRows = comparisonRows ?? rows;
  const rankMetricKeys = columns.map((column) => column.key);
  if (
    columns.some((column) => column.key === "record") &&
    !rankMetricKeys.includes("win_pct")
  ) {
    rankMetricKeys.push("win_pct");
  }
  const rankMaps = buildMetricRankMaps(rankingRows, rankMetricKeys);
  const rowIndexByRef = new Map(
    rankingRows.map((row, index) => [row, index] as const),
  );
  const rowIndexByTeam = new Map(
    rankingRows
      .map((row, index) => ({
        index,
        team: typeof row.team === "string" ? row.team : null,
      }))
      .filter((entry): entry is { index: number; team: string } =>
        Boolean(entry.team),
      )
      .map((entry) => [entry.team, entry.index] as const),
  );

  return (
    <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
      <h3 className="text-lg font-semibold text-kos-text">{title}</h3>
      {rows.length === 0 ? (
        <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-kos-text/70">
          {empty}
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={`${title}-${idx}`} className="odd:bg-white/3">
                  {columns.map((column) => {
                    const byRef = rowIndexByRef.get(row);
                    const byTeam =
                      typeof row.team === "string"
                        ? rowIndexByTeam.get(row.team)
                        : undefined;
                    const rankingIndex = byRef ?? byTeam ?? -1;
                    return (
                      <td
                        key={column.key}
                        className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85"
                      >
                        {column.key === "record"
                          ? formatTeamRecordWithRank(
                              row,
                              rankMaps.win_pct?.get(rankingIndex),
                            )
                          : formatIntelValueWithRank(
                              row[column.key],
                              rankMaps[column.key]?.get(rankingIndex),
                            )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default async function NflTeamIntelViewPage({
  params,
  searchParams,
}: {
  params: Promise<{ team: string; view: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { team: requestedTeam, view } = await params;
  const rawSearch = await searchParams;
  if (!isNflTeamIntelView(view)) notFound();

  const canonicalTeam = normalizeTeamCode(requestedTeam);
  if (!canonicalTeam || !isNflDirectoryTeamCode(canonicalTeam)) notFound();

  const filters = parseTeamIntelFilters(rawSearch);
  const standings = await fetchNflIntel("standings", {
    season: filters.season,
    week: filters.week,
  });
  const teamCodes = extractTeamCodes(standings.rows);
  const selectedTeam = resolveTeamCode(canonicalTeam, teamCodes);

  // Canonicalize aliases (WSH→WAS) and strip stale ?team= query params so
  // directory / ESPN codes never silently render as Bills.
  const queryTeam = firstQueryValue(rawSearch.team);
  const pathNeedsCanonical =
    requestedTeam.trim().toUpperCase() !== selectedTeam;
  if (queryTeam || pathNeedsCanonical) {
    const query = new URLSearchParams();
    if (filters.season) query.set("season", String(filters.season));
    if (filters.week) query.set("week", String(filters.week));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    redirect(`/pro/nfl/teams/${selectedTeam}/${view}${suffix}`);
  }

  const [stats, statsComparison, depth, injuries, rosters] = await Promise.all([
    fetchNflIntel("stats", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
    fetchNflIntel("stats", { season: filters.season, week: filters.week }),
    fetchNflIntel("depth-charts", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
    fetchNflIntel("injuries", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
    fetchNflIntel("rosters", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
  ]);

  const season = standings.season ?? stats.season ?? filters.season ?? null;
  const week = standings.week ?? stats.week ?? filters.week ?? null;
  const selectedFilters = {
    ...filters,
    season: season ?? undefined,
    week: week ?? undefined,
  };

  const perspective: TendencyPerspective =
    firstQueryValue(rawSearch.perspective) === "defense"
      ? "defense"
      : "offense";
  const situationParam = firstQueryValue(rawSearch.situation);
  const activeSituation: SituationTabKey = SITUATION_TAB_KEYS.includes(
    situationParam as SituationTabKey,
  )
    ? (situationParam as SituationTabKey)
    : "down_distance";
  const qbSituationParam = firstQueryValue(rawSearch.qbSituation);
  const activeQbSituation: QbSituationType = QB_SITUATION_KEYS.includes(
    qbSituationParam as QbSituationType,
  )
    ? (qbSituationParam as QbSituationType)
    : "pressure";

  const tendencyData =
    view === "tendencies"
      ? await (async () => {
          const profile = await fetchNflTeamTendencyProfileResolved({
            season: season ?? 2026,
            team: selectedTeam,
            perspective,
          });
          const qbSplits = await fetchNflQbSituationalSplits({
            season: profile.season,
            team: selectedTeam,
            minDropbacks: 10,
            limit: 200,
          });
          return { profile, qbSplits };
        })()
      : null;

  const standingsRow = standings.rows.find((row) => row.team === selectedTeam);
  const statsRow = stats.rows.find((row) => row.team === selectedTeam);
  const statsRankMaps = buildMetricRankMaps(statsComparison.rows, [
    "pass_rate",
    "red_zone_td_rate",
    "epa_per_play_offense",
    "epa_per_play_defense_allowed",
  ]);
  const statsIndex = statsComparison.rows.findIndex(
    (row) => row.team === selectedTeam,
  );
  const trends = buildTrendSnippets(statsRow, {
    pass_rate: statsRankMaps.pass_rate?.get(statsIndex),
    red_zone_td_rate: statsRankMaps.red_zone_td_rate?.get(statsIndex),
    epa_per_play_offense: statsRankMaps.epa_per_play_offense?.get(statsIndex),
    epa_per_play_defense_allowed:
      statsRankMaps.epa_per_play_defense_allowed?.get(statsIndex),
  });
  const standingsRankMaps = buildMetricRankMaps(standings.rows, [
    "point_diff",
    "win_pct",
    "points_for",
    "points_against",
  ]);
  const standingsIndex = standings.rows.findIndex(
    (row) => row.team === selectedTeam,
  );
  const directoryEntry =
    NFL_TEAM_DIRECTORY.find((entry) => entry.code === selectedTeam) ?? null;
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
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-3 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/nfl/overview" className="hover:text-kos-gold">
          NFL Overview
        </Link>
        <span>/</span>
        <Link href="/pro/nfl/teams" className="hover:text-kos-gold">
          Team Intel
        </Link>
        <span>/</span>
        <span className="text-kos-text">{teamDisplayName(selectedTeam)}</span>
      </nav>

      <TeamIntelFilterBar
        title={`${teamDisplayName(selectedTeam)} (${selectedTeam})`}
        subtitle="Switch season/week context while keeping premium team intel navigation in place."
        basePath={`/pro/nfl/teams/${selectedTeam}/${view}`}
        filters={selectedFilters}
        teamOptions={teamCodes.map((code) => ({
          code,
          name: teamDisplayName(code),
        }))}
        selectedTeam={selectedTeam}
        showTeamSelect
        showLeagueFilters={false}
      />

      <section className="mt-6 rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/45 to-black/65 p-5 sm:p-6">
        <p className="text-xs uppercase tracking-[0.15em] text-kos-gold">
          Team Hub
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          {teamDisplayName(selectedTeam)}
        </h1>
        <p className="mt-2 text-sm text-kos-text/75">
          {season ? `Season ${season}` : "Season unavailable"}{" "}
          {week ? `· Week ${week}` : ""} · Premium team intel view for matchup
          prep and execution context.
        </p>
        <TeamIntelSectionNav
          activeView={view}
          team={selectedTeam}
          filters={{ season: season ?? undefined, week: week ?? undefined }}
        />
        {directoryEntry ? (
          <p className="mt-3 text-xs text-kos-text/60">
            {directoryEntry.conference} {directoryEntry.division}
            {previewAssignment ? " · KosEdge preview" : ""}
          </p>
        ) : null}
      </section>

      {view === "overview" && previewAssignment ? (
        <div className="mt-5">
          <TeamPreviewSlot
            teamName={teamDisplayName(selectedTeam)}
            teamCode={selectedTeam}
            writer={previewAssignment.writer}
            assignmentNote={previewAssignment.note}
            provisional={previewAssignment.provisional}
          />
        </div>
      ) : null}

      <section className="mt-5 grid gap-4 xl:grid-cols-[2fr_1fr]">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-5">
          <h2 className="text-lg font-semibold text-kos-text">
            Quick Market Context
          </h2>
          <p className="mt-2 text-sm text-kos-text/75">
            Record{" "}
            {formatTeamRecordWithRank(
              standingsRow,
              standingsRankMaps.win_pct?.get(standingsIndex),
            )}{" "}
            with point differential{" "}
            {formatIntelValueWithRank(
              standingsRow?.point_diff,
              standingsRankMaps.point_diff?.get(standingsIndex),
              true,
            )}
            . Use pass rate and efficiency splits to calibrate spread/total
            assumptions before pricing.
          </p>
          <div className="mt-4 space-y-2">
            {trends.map((snippet) => (
              <p
                key={snippet}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/80"
              >
                {snippet}
              </p>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-white/10 bg-black/30 p-5">
          <h2 className="text-lg font-semibold text-kos-text">
            Depth / Injury Impact
          </h2>
          <p className="mt-2 text-sm text-kos-text/75">
            {injuries.rows.length} reported injuries and {depth.rows.length}{" "}
            depth-chart records for this filter.
          </p>
          <div className="mt-4 rounded-lg border border-kos-gold/25 bg-kos-gold/10 p-3">
            <p className="text-xs uppercase tracking-wide text-kos-gold">
              Impact Badge
            </p>
            <p className="mt-1 text-sm text-kos-text">
              {injuries.rows.length >= 8
                ? "Elevated volatility"
                : injuries.rows.length >= 3
                  ? "Monitor active"
                  : "Stable availability"}
            </p>
          </div>
        </article>
      </section>

      <section className="mt-5">
        <TeamIntelStatCards
          row={statsRow}
          comparisonRows={statsComparison.rows}
        />
      </section>

      {(stats.error ||
        depth.error ||
        injuries.error ||
        rosters.error ||
        tendencyData?.profile.error) && (
        <section className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-200">
          {[
            stats.error,
            depth.error,
            injuries.error,
            rosters.error,
            tendencyData?.profile.error,
          ]
            .filter(Boolean)
            .join(" ")}
        </section>
      )}

      <section className="mt-6">
        {view === "overview" ? (
          <div className="grid gap-4 xl:grid-cols-2">
            <TeamIntelTable
              title="Situational Snapshot"
              rows={stats.rows.slice(0, 1)}
              comparisonRows={statsComparison.rows}
              empty="No situational stats available for this team and week."
              columns={[
                { key: "games_played", label: "Games" },
                { key: "offensive_plays", label: "Off Plays" },
                { key: "defensive_plays", label: "Def Plays" },
                { key: "pass_rate", label: "Pass Rate" },
                { key: "early_down_pass_rate", label: "Early Pass" },
                { key: "red_zone_td_rate", label: "RZ TD" },
              ]}
            />
            <TeamIntelTable
              title="Roster Pulse"
              rows={rosters.rows.slice(0, 8)}
              empty="Roster hierarchy is still populating for this period."
              columns={[
                { key: "position", label: "Pos" },
                { key: "player_name", label: "Player" },
                { key: "depth_slot", label: "Slot" },
                { key: "depth_order", label: "Order" },
                { key: "report_status", label: "Report" },
              ]}
            />
            <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5 xl:col-span-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold text-kos-text">
                    Coaching staff
                  </h3>
                  <p className="mt-1 text-sm text-kos-text/70">
                    Head coach, offensive coordinator, and defensive coordinator
                    for scheme context.
                  </p>
                </div>
                <span className="rounded-full border border-amber-400/35 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-100">
                  Data pending
                </span>
              </div>
              <p className="mt-4 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-kos-text/70">
                Coaching profile data pending — HC / OC / DC notes ship with the
                KosEdge research pass.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link
                  href="/edge-board/nfl"
                  className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
                >
                  Edge board →
                </Link>
                <Link
                  href="/pro/nfl/fair-lines"
                  className="inline-flex rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/35"
                >
                  KEI lines →
                </Link>
                <Link
                  href={`/pro/nfl/teams/${selectedTeam}/depth-chart`}
                  className="inline-flex rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/35"
                >
                  Depth chart →
                </Link>
              </div>
            </article>
          </div>
        ) : null}

        {view === "stats" ? (
          <TeamIntelTable
            title="Stats & Team Splits"
            rows={stats.rows}
            comparisonRows={statsComparison.rows}
            empty="No stat records available for this team in this period."
            columns={[
              { key: "games_played", label: "Games" },
              { key: "record", label: "Record" },
              { key: "pass_rate", label: "Pass Rate" },
              { key: "early_down_pass_rate", label: "Early Pass" },
              { key: "success_rate_offense", label: "Off Success" },
              {
                key: "success_rate_defense_allowed",
                label: "Def Success Allowed",
              },
              { key: "epa_per_play_offense", label: "Off EPA/Play" },
              { key: "epa_per_play_defense_allowed", label: "Def EPA Allowed" },
            ]}
          />
        ) : null}

        {view === "depth-chart" ? (
          <DepthChartRenderer rows={depth.rows} />
        ) : null}

        {view === "injuries" ? (
          <InjuryStatusPanel rows={injuries.rows} />
        ) : null}

        {view === "splits" ? (
          <div className="grid gap-4 xl:grid-cols-2">
            <TeamIntelTable
              title="Efficiency Splits"
              rows={stats.rows}
              comparisonRows={statsComparison.rows}
              empty="No split metrics available for this team in this period."
              columns={[
                { key: "pass_rate", label: "Pass Rate" },
                { key: "early_down_pass_rate", label: "Early Pass Rate" },
                { key: "red_zone_td_rate", label: "RZ TD Rate" },
                { key: "pressure_rate_allowed", label: "Pressure Allowed" },
                { key: "pressure_rate_generated", label: "Pressure Generated" },
              ]}
            />
            <TeamIntelTable
              title="Scoreboard Context"
              rows={standingsRow ? [standingsRow] : []}
              comparisonRows={standings.rows}
              empty="Standings context is unavailable for this team right now."
              columns={[
                { key: "record", label: "Record" },
                { key: "points_for", label: "Points For" },
                { key: "points_against", label: "Points Against" },
                { key: "point_diff", label: "Point Diff" },
                { key: "win_pct", label: "Win %" },
              ]}
            />
          </div>
        ) : null}

        {view === "tendencies" && tendencyData ? (
          <TeamTendencyPanels
            team={selectedTeam}
            season={tendencyData.profile.season}
            requestedSeason={tendencyData.profile.requestedSeason}
            usedFallback={tendencyData.profile.usedFallback}
            filters={{ season: season ?? undefined, week: week ?? undefined }}
            perspective={perspective}
            activeSituation={activeSituation}
            activeQbSituation={activeQbSituation}
            situational={tendencyData.profile.situational}
            direction={tendencyData.profile.direction}
            qbSplits={tendencyData.qbSplits.rows}
          />
        ) : null}
      </section>
    </main>
  );
}
