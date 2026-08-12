import Link from "next/link";
import NflTruthStateBadge from "@/components/pro/nfl/NflTruthStateBadge";
import {
  fetchNflIntel,
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
  groupStandingsRows,
  type NflIntelResponseRow,
} from "@/lib/nfl-intel";
import { buildMetricRankMaps } from "@/lib/intel-ranking";
import { resolveNflTruthLabel } from "@/lib/nfl-truth-label";

type IntelEndpoint =
  | "rosters"
  | "stats"
  | "standings"
  | "depth-charts"
  | "injuries";

type ColumnSpec = {
  key: string;
  label: string;
};

export default async function NflIntelTablePage({
  endpoint,
  title,
  description,
  columns,
  emptyHint,
  season,
  week,
  team,
}: {
  endpoint: IntelEndpoint;
  title: string;
  description: string;
  columns: ColumnSpec[];
  emptyHint: string;
  season?: number;
  week?: number;
  team?: string;
}) {
  const data = await fetchNflIntel(endpoint, { season, week, team });
  const rows = data.rows as NflIntelResponseRow[];
  const standingsGroups =
    endpoint === "standings" ? groupStandingsRows(rows) : [];
  const tableRows =
    endpoint === "standings"
      ? standingsGroups.flatMap((group) => group.rows)
      : rows;
  const rankMetricKeys = columns.map((column) => column.key);
  if (
    columns.some((column) => column.key === "record") &&
    !rankMetricKeys.includes("win_pct")
  ) {
    rankMetricKeys.push("win_pct");
  }
  const rankMaps = buildMetricRankMaps(tableRows, rankMetricKeys);
  const tableRowIndexByRef = new Map(
    tableRows.map((row, index) => [row, index] as const),
  );
  const latest = data.selection?.latest_available;
  const latestSeason =
    typeof latest?.season === "number" ? latest.season : null;
  const latestWeek = typeof latest?.week === "number" ? latest.week : null;
  const truth = resolveNflTruthLabel({
    season: data.season,
    week: data.week,
    fallbackApplied: Boolean(data.selection?.fallback_applied),
    latestSeason,
    latestWeek,
  });
  const requestedHadNoData =
    data.selection?.requested_availability?.has_data === false;
  const showFallbackHint = Boolean(truth.honesty_note);
  const showRequestedEmptyHint = Boolean(
    rows.length === 0 && requestedHadNoData && truth.honesty_note,
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
            {title}
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-kos-text/75">
            {description}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <NflTruthStateBadge state={truth.ui_state} />
            <p className="text-xs text-kos-text/60">
              {truth.period_line}
              {` · ${data.count} rows`}
              {truth.is_current ? "" : " · not current"}
            </p>
          </div>
          {showFallbackHint && truth.honesty_note ? (
            <p className="mt-1 text-xs text-kos-gold/80">{truth.honesty_note}</p>
          ) : null}
        </div>
        <Link
          href="/pro/nfl/overview"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm text-kos-text transition hover:border-kos-gold/40"
        >
          Back to NFL Overview
        </Link>
      </div>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl sm:p-6">
        {data.error ? (
          <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-200">
            {data.error}
          </div>
        ) : null}
        {tableRows.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/2 p-4 text-sm text-kos-text/70">
            {emptyHint}
            {showRequestedEmptyHint ? (
              <p className="mt-2 text-xs text-kos-text/60">
                No data for selected period. {truth.honesty_note}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="overflow-x-auto">
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
                {endpoint === "standings"
                  ? standingsGroups.flatMap((group, groupIndex) => [
                      <tr
                        key={`group-${group.conference}-${group.division}-${groupIndex}`}
                        className="bg-kos-gold/8"
                      >
                        <td
                          colSpan={columns.length}
                          className="border-b border-kos-gold/25 px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-kos-gold"
                        >
                          {group.conference} · {group.division}
                        </td>
                      </tr>,
                      ...group.rows.map((row, rowIndex) => (
                        <tr
                          key={`${endpoint}-${groupIndex}-${rowIndex}`}
                          className="odd:bg-white/2"
                        >
                          {columns.map((column) => (
                            <td
                              key={column.key}
                              className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85"
                            >
                              {column.key === "record"
                                ? formatTeamRecordWithRank(
                                    row,
                                    rankMaps.win_pct?.get(
                                      tableRowIndexByRef.get(row) ?? -1,
                                    ),
                                  )
                                : formatIntelValueWithRank(
                                    row[column.key],
                                    rankMaps[column.key]?.get(
                                      tableRowIndexByRef.get(row) ?? -1,
                                    ),
                                  )}
                            </td>
                          ))}
                        </tr>
                      )),
                    ])
                  : tableRows.map((row, rowIndex) => (
                      <tr
                        key={`${endpoint}-${rowIndex}`}
                        className="odd:bg-white/2"
                      >
                        {columns.map((column) => (
                          <td
                            key={column.key}
                            className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85"
                          >
                            {column.key === "record"
                              ? formatTeamRecordWithRank(
                                  row,
                                  rankMaps.win_pct?.get(rowIndex),
                                )
                              : formatIntelValueWithRank(
                                  row[column.key],
                                  rankMaps[column.key]?.get(rowIndex),
                                )}
                          </td>
                        ))}
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
