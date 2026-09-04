import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import DepthChartRenderer from "@/components/pro/DepthChartRenderer";
import InjuryStatusPanel from "@/components/pro/InjuryStatusPanel";
import TruePrTeamStrip from "@/components/pro/nfl/TruePrTeamStrip";
import TeamIntelFilterBar from "@/components/pro/TeamIntelFilterBar";
import TeamIntelSectionNav from "@/components/pro/TeamIntelSectionNav";
import TeamIntelStatCards from "@/components/pro/TeamIntelStatCards";
import TeamIntelTable from "@/components/pro/TeamIntelTable";
import TeamPreviewSlot from "@/components/pro/team-research/TeamPreviewSlot";
import TeamTendencyPanels, {
  type SituationTabKey,
} from "@/components/pro/TeamTendencyPanels";
import { buildMetricRankMaps } from "@/lib/intel-ranking";
import {
  coachingContinuityBadge,
  fetchNflCoachingStaff,
  fetchNflIntel,
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
} from "@/lib/nfl-intel";
import { fetchTruePrProductSurface } from "@/lib/nfl-true-pr";
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
import {
  nflActualRecordColumnLabel,
  resolveNflTruthLabel,
} from "@/lib/nfl-truth-label";
import NflTruthStateBadge from "@/components/pro/nfl/NflTruthStateBadge";
import { nflDepthPackFreshnessStamp } from "@/lib/nfl-surface-honesty";

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
  // Research filters always list the full 32-team directory on team routes.
  const teamCodes = NFL_TEAM_DIRECTORY.map((entry) => entry.code);
  const selectedTeam = resolveTeamCode(
    canonicalTeam,
    extractTeamCodes(standings.rows),
  );

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

  const [
    stats,
    statsComparison,
    depth,
    injuries,
    rosters,
    coaching,
    truePrSurface,
  ] = await Promise.all([
    fetchNflIntel("stats", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
    fetchNflIntel("stats", { season: filters.season, week: filters.week }),
    fetchNflIntel("depth-charts", {
      season: filters.season ?? 2026,
      week: filters.week ?? 1,
      team: selectedTeam,
    }),
    fetchNflIntel("injuries", {
      season: filters.season,
      week: filters.week,
      team: selectedTeam,
    }),
    fetchNflIntel("rosters", {
      season: filters.season ?? 2026,
      week: filters.week ?? 1,
      team: selectedTeam,
    }),
    fetchNflCoachingStaff({
      season: filters.season ?? 2026,
      team: selectedTeam,
    }),
    view === "overview"
      ? fetchTruePrProductSurface({
          season: filters.season ?? 2026,
          asOfWeek: 1,
          team: selectedTeam,
        })
      : Promise.resolve(null),
  ]);
  const truePrRow = truePrSurface?.teams?.[0] ?? null;
  const coachingRow = coaching.rows[0] ?? null;
  const coachingBadge = coachingContinuityBadge(coachingRow);

  const season = standings.season ?? stats.season ?? filters.season ?? null;
  const week = standings.week ?? stats.week ?? filters.week ?? null;
  const truth = resolveNflTruthLabel({
    season,
    week,
    fallbackApplied: Boolean(
      standings.selection?.fallback_applied ||
      stats.selection?.fallback_applied,
    ),
    latestSeason:
      standings.selection?.latest_available?.season ??
      stats.selection?.latest_available?.season,
    latestWeek:
      standings.selection?.latest_available?.week ??
      stats.selection?.latest_available?.week,
  });
  const recordDt = nflActualRecordColumnLabel(truth);
  const selectedFilters = {
    ...filters,
    season: season ?? undefined,
    week: truth.week ?? undefined,
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
        <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-kos-text/75">
          <NflTruthStateBadge state={truth.ui_state} />
          <span>
            {truth.period_line} · Premium team intel view for matchup prep and
            execution context.
          </span>
        </p>
        {truth.honesty_note ? (
          <p className="mt-1 text-xs text-kos-gold/80">{truth.honesty_note}</p>
        ) : null}
        <TeamIntelSectionNav
          activeView={view}
          team={selectedTeam}
          filters={{
            season: season ?? undefined,
            week: truth.week ?? undefined,
          }}
        />
        {directoryEntry ? (
          <p className="mt-3 text-xs text-kos-text/60">
            {directoryEntry.conference} {directoryEntry.division}
            {previewAssignment ? " · KosEdge preview" : ""}
          </p>
        ) : null}
      </section>

      {view === "overview" ? (
        <TruePrTeamStrip
          row={truePrRow}
          engineVersion={truePrSurface?.engine_version}
        />
      ) : null}

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
            {recordDt}{" "}
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
              empty="Roster hierarchy unavailable — packaged depth has no rows for this filter."
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
                    from the shared 2026 staff pack.
                  </p>
                </div>
                <span
                  className={
                    coachingBadge.tone === "live"
                      ? "rounded-full border border-emerald-400/35 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-100"
                      : coachingBadge.tone === "thin"
                        ? "rounded-full border border-amber-400/35 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-100"
                        : "rounded-full border border-white/20 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-kos-text/70"
                  }
                >
                  {coachingBadge.label}
                </span>
              </div>
              {coachingRow &&
              (coachingRow.hc_name ||
                coachingRow.oc_name ||
                coachingRow.dc_name) ? (
                <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                  {(
                    [
                      ["HC", coachingRow.hc_name, coachingRow.new_hc],
                      ["OC", coachingRow.oc_name, coachingRow.new_oc],
                      ["DC", coachingRow.dc_name, coachingRow.new_dc],
                    ] as const
                  ).map(([role, name, isNew]) => (
                    <div
                      key={role}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-3"
                    >
                      <dt className="text-[10px] font-semibold uppercase tracking-wide text-kos-text/55">
                        {role}
                        {isNew === true
                          ? " · new"
                          : isNew === false
                            ? " · returning"
                            : ""}
                      </dt>
                      <dd className="mt-1 text-sm font-medium text-kos-text">
                        {typeof name === "string" && name.trim()
                          ? name
                          : "Unknown"}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="mt-4 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-kos-text/70">
                  Coaching staff thin or unknown for this team — no invented
                  names.
                </p>
              )}
              {typeof coachingRow?.notes === "string" &&
              coachingRow.notes.trim() ? (
                <p className="mt-3 text-xs text-kos-text/60">
                  {coachingRow.notes}
                </p>
              ) : null}
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
          <div className="space-y-3">
            <p
              className="text-xs text-kos-gold/85"
              data-testid="nfl-depth-source-stamp"
            >
              {nflDepthPackFreshnessStamp()} See{" "}
              <Link
                href="/pro/nfl/camp"
                className="underline decoration-kos-gold/40 underline-offset-2 hover:decoration-kos-gold"
              >
                Camp Desk
              </Link>
              .
            </p>
            <DepthChartRenderer rows={depth.rows} />
          </div>
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
            filters={{
              season: season ?? undefined,
              week: truth.week ?? undefined,
            }}
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
