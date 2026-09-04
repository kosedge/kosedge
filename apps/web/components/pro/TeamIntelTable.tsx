import { buildMetricRankMaps } from "@/lib/intel-ranking";
import { formatCompetitionAwareIntelCell } from "@/lib/nfl-depth-pack-freshness";
import {
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
  type NflIntelResponseRow,
} from "@/lib/nfl-intel";

export type TeamIntelTableProps = {
  title: string;
  rows: NflIntelResponseRow[];
  comparisonRows?: NflIntelResponseRow[];
  columns: Array<{ key: string; label: string }>;
  empty: string;
};

function formatTeamIntelCell(
  columnKey: string,
  row: NflIntelResponseRow,
  rank?: number,
): string {
  const competitionAware = formatCompetitionAwareIntelCell(
    columnKey,
    row[columnKey],
  );
  if (competitionAware != null) return competitionAware;
  if (columnKey === "record") {
    return formatTeamRecordWithRank(row, rank);
  }
  return formatIntelValueWithRank(row[columnKey], rank);
}

/**
 * Shared team-hub intel table (Roster Pulse, stats, splits).
 * Competition / depth_slot snake_case is humanized via the depth-pack helper.
 */
export default function TeamIntelTable({
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
              {rows.map((row, idx) => {
                const byRef = rowIndexByRef.get(row);
                const byTeam =
                  typeof row.team === "string"
                    ? rowIndexByTeam.get(row.team)
                    : undefined;
                const rankingIndex = byRef ?? byTeam ?? -1;
                return (
                  <tr key={`${title}-${idx}`} className="odd:bg-white/3">
                    {columns.map((column) => {
                      const rankKey =
                        column.key === "record" ? "win_pct" : column.key;
                      return (
                        <td
                          key={column.key}
                          className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85"
                          data-testid={
                            column.key === "depth_slot"
                              ? "roster-pulse-depth-slot"
                              : undefined
                          }
                        >
                          {formatTeamIntelCell(
                            column.key,
                            row,
                            rankMaps[rankKey]?.get(rankingIndex),
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
