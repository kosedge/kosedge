import { buildMetricRankMaps } from "@/lib/intel-ranking";
import type { NflIntelResponseRow } from "@/lib/nfl-intel";
import {
  formatIntelValueWithRank,
  formatTeamRecordWithRank,
} from "@/lib/nfl-intel";

const CARD_FIELDS: Array<{ key: string; label: string }> = [
  { key: "record", label: "Record" },
  { key: "win_pct", label: "Win %" },
  { key: "point_diff", label: "Point Diff" },
  { key: "pass_rate", label: "Pass Rate" },
  { key: "red_zone_td_rate", label: "RZ TD Rate" },
  { key: "epa_per_play_offense", label: "Off EPA / Play" },
  { key: "epa_per_play_defense_allowed", label: "Def EPA Allowed" },
];

function resolveRowIndex(
  row: NflIntelResponseRow,
  comparisonRows: NflIntelResponseRow[],
): number {
  const byRef = comparisonRows.indexOf(row);
  if (byRef >= 0) return byRef;
  const teamCode = typeof row.team === "string" ? row.team : null;
  if (teamCode) {
    return comparisonRows.findIndex((candidate) => candidate.team === teamCode);
  }
  return -1;
}

export default function TeamIntelStatCards({
  row,
  comparisonRows,
}: {
  row?: NflIntelResponseRow;
  comparisonRows?: NflIntelResponseRow[];
}) {
  const rankingRows = comparisonRows ?? (row ? [row] : []);
  const rankMaps = buildMetricRankMaps(
    rankingRows,
    CARD_FIELDS.map((field) =>
      field.key === "record" ? "win_pct" : field.key,
    ),
  );
  const rowIndex = row ? resolveRowIndex(row, rankingRows) : -1;

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {CARD_FIELDS.map((field) => (
        <article
          key={field.key}
          className="rounded-xl border border-white/10 bg-white/5 p-4"
        >
          <p className="text-xs uppercase tracking-[0.14em] text-kos-text/60">
            {field.label}
          </p>
          <p className="mt-2 text-xl font-semibold text-kos-text">
            {row
              ? field.key === "record"
                ? formatTeamRecordWithRank(row, rankMaps.win_pct?.get(rowIndex))
                : formatIntelValueWithRank(
                    row[field.key],
                    rankMaps[field.key]?.get(rowIndex),
                  )
              : "—"}
          </p>
        </article>
      ))}
    </section>
  );
}
