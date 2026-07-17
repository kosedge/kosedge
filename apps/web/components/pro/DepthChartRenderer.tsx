import { buildMetricRankMaps } from "@/lib/intel-ranking";
import type { NflIntelResponseRow } from "@/lib/nfl-intel";
import { formatIntelValue, formatIntelValueWithRank } from "@/lib/nfl-intel";
import { formatIntelNumber } from "@/lib/intel-numeric";

type DepthRow = {
  position: string;
  player_name: string;
  depth_slot: string;
  depth_order: number;
  role_confidence?: number;
  pass_yards?: number;
  pass_touchdowns?: number;
  rush_yards?: number;
  receptions?: number;
  receiving_yards?: number;
  touchdowns_scored?: number;
  pass_yards_mean?: number;
  rush_yards_mean?: number;
  receiving_yards_mean?: number;
  receptions_mean?: number;
  pass_tds_mean?: number;
  rush_tds_mean?: number;
  rec_tds_mean?: number;
  anytime_td_prob?: number;
  fantasy_points_roy?: number;
  fantasy_floor_roy?: number;
  fantasy_ceiling_roy?: number;
  fantasy_rank_position_roy?: number;
  fantasy_tier_roy?: number;
};

const SKILL_POSITION_PRIORITY = ["QB", "RB", "WR", "TE"] as const;

function asFiniteNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function hasAny(...values: Array<number | undefined>): boolean {
  return values.some((value) => value !== undefined);
}

function formatMetric(value: number | undefined, rank?: number): string {
  if (value === undefined) return "—";
  const base = formatIntelNumber(value, true);
  if (typeof rank !== "number" || !Number.isFinite(rank)) return base;
  return `${base} (${rank})`;
}

function toDepthRow(row: NflIntelResponseRow): DepthRow | null {
  const position = typeof row.position === "string" ? row.position : null;
  const playerName = typeof row.player_name === "string" ? row.player_name : null;
  const slot = typeof row.depth_slot === "string" ? row.depth_slot : null;
  const order = typeof row.depth_order === "number" ? row.depth_order : null;
  if (!position || !playerName || !slot || order === null) return null;

  return {
    position,
    player_name: playerName,
    depth_slot: slot,
    depth_order: order,
    role_confidence: typeof row.role_confidence === "number" ? row.role_confidence : undefined,
    pass_yards: asFiniteNumber(row.pass_yards),
    pass_touchdowns: asFiniteNumber(row.pass_touchdowns),
    rush_yards: asFiniteNumber(row.rush_yards),
    receptions: asFiniteNumber(row.receptions),
    receiving_yards: asFiniteNumber(row.receiving_yards),
    touchdowns_scored: asFiniteNumber(row.touchdowns_scored),
    pass_yards_mean: asFiniteNumber(row.pass_yards_mean),
    rush_yards_mean: asFiniteNumber(row.rush_yards_mean),
    receiving_yards_mean: asFiniteNumber(row.receiving_yards_mean),
    receptions_mean: asFiniteNumber(row.receptions_mean),
    pass_tds_mean: asFiniteNumber(row.pass_tds_mean),
    rush_tds_mean: asFiniteNumber(row.rush_tds_mean),
    rec_tds_mean: asFiniteNumber(row.rec_tds_mean),
    anytime_td_prob: asFiniteNumber(row.anytime_td_prob),
    fantasy_points_roy: asFiniteNumber(row.fantasy_points_roy),
    fantasy_floor_roy: asFiniteNumber(row.fantasy_floor_roy),
    fantasy_ceiling_roy: asFiniteNumber(row.fantasy_ceiling_roy),
    fantasy_rank_position_roy: asFiniteNumber(row.fantasy_rank_position_roy),
    fantasy_tier_roy: asFiniteNumber(row.fantasy_tier_roy),
  };
}

function positionSortKey(position: string): number {
  const idx = SKILL_POSITION_PRIORITY.indexOf(position as (typeof SKILL_POSITION_PRIORITY)[number]);
  return idx >= 0 ? idx : SKILL_POSITION_PRIORITY.length + 1;
}

function depthSlotSortKey(slot: string): number {
  const normalized = slot.toLowerCase();
  if (normalized === "starter") return 0;
  if (normalized === "backup") return 1;
  if (normalized === "rotation") return 2;
  if (normalized === "depth") return 3;
  return 4;
}

type RankMaps = Record<string, Map<number, number>>;

function renderFantasyStats(row: DepthRow, rowIndex: number, rankMaps: RankMaps): string {
  const isQb = row.position === "QB";
  const isRushRole = row.position === "QB" || row.position === "RB";
  const isReceiverRole = row.position === "WR" || row.position === "TE" || row.position === "RB";

  const segments: string[] = [];

  if (isQb && hasAny(row.pass_yards, row.pass_touchdowns)) {
    segments.push(
      `Pass ${formatMetric(row.pass_yards, rankMaps.pass_yards?.get(rowIndex))}y / ${formatMetric(
        row.pass_touchdowns,
        rankMaps.pass_touchdowns?.get(rowIndex),
      )} TD`,
    );
  }
  if (isRushRole && hasAny(row.rush_yards, row.touchdowns_scored)) {
    segments.push(
      `Rush ${formatMetric(row.rush_yards, rankMaps.rush_yards?.get(rowIndex))}y / ${formatMetric(
        row.touchdowns_scored,
        rankMaps.touchdowns_scored?.get(rowIndex),
      )} TD`,
    );
  }
  if (isReceiverRole && hasAny(row.receiving_yards, row.receptions)) {
    segments.push(
      `Rec ${formatMetric(row.receiving_yards, rankMaps.receiving_yards?.get(rowIndex))}y / ${formatMetric(
        row.receptions,
        rankMaps.receptions?.get(rowIndex),
      )} rec / ${formatMetric(row.touchdowns_scored, rankMaps.touchdowns_scored?.get(rowIndex))} TD`,
    );
  }

  return segments.length > 0 ? segments.join(" · ") : "No tracked production yet";
}

function renderProjection(row: DepthRow, rowIndex: number, rankMaps: RankMaps): { primary: string; secondary?: string; missing: boolean } {
  const projectionParts: string[] = [];
  if (hasAny(row.pass_yards_mean, row.pass_tds_mean) && row.position === "QB") {
    projectionParts.push(
      `Pass ${formatMetric(row.pass_yards_mean, rankMaps.pass_yards_mean?.get(rowIndex))}y / ${formatMetric(
        row.pass_tds_mean,
        rankMaps.pass_tds_mean?.get(rowIndex),
      )} TD`,
    );
  }
  if (hasAny(row.rush_yards_mean, row.rush_tds_mean) && (row.position === "QB" || row.position === "RB")) {
    projectionParts.push(
      `Rush ${formatMetric(row.rush_yards_mean, rankMaps.rush_yards_mean?.get(rowIndex))}y / ${formatMetric(
        row.rush_tds_mean,
        rankMaps.rush_tds_mean?.get(rowIndex),
      )} TD`,
    );
  }
  if (
    hasAny(row.receiving_yards_mean, row.receptions_mean, row.rec_tds_mean) &&
    (row.position === "WR" || row.position === "TE" || row.position === "RB")
  ) {
    projectionParts.push(
      `Rec ${formatMetric(row.receiving_yards_mean, rankMaps.receiving_yards_mean?.get(rowIndex))}y / ${formatMetric(
        row.receptions_mean,
        rankMaps.receptions_mean?.get(rowIndex),
      )} rec / ${formatMetric(row.rec_tds_mean, rankMaps.rec_tds_mean?.get(rowIndex))} TD`,
    );
  }

  const hasFantasy = row.fantasy_points_roy !== undefined;
  if (projectionParts.length === 0 && !hasFantasy) {
    return {
      primary: "Premium rest-of-year projection pending",
      secondary: "Refresh runs when player baseline model updates.",
      missing: true,
    };
  }

  const fantasyPart = hasFantasy
    ? `FPTS ${formatIntelValueWithRank(row.fantasy_points_roy, rankMaps.fantasy_points_roy?.get(rowIndex))}${
        row.fantasy_rank_position_roy !== undefined
          ? ` (#${formatIntelValueWithRank(
              row.fantasy_rank_position_roy,
              rankMaps.fantasy_rank_position_roy?.get(rowIndex),
            )})`
          : ""
      }`
    : undefined;

  return {
    primary: projectionParts.length > 0 ? projectionParts.join(" · ") : "Projection available",
    secondary: fantasyPart,
    missing: false,
  };
}

export default function DepthChartRenderer({ rows }: { rows: NflIntelResponseRow[] }) {
  const mapped = rows.map(toDepthRow).filter(Boolean) as DepthRow[];
  const byPosition = mapped.reduce<Record<string, DepthRow[]>>((acc, row) => {
    acc[row.position] = acc[row.position] ?? [];
    acc[row.position].push(row);
    return acc;
  }, {});
  const positions = Object.keys(byPosition).sort((a, b) => {
    const byPriority = positionSortKey(a) - positionSortKey(b);
    return byPriority !== 0 ? byPriority : a.localeCompare(b);
  });

  if (positions.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-kos-text/70">
        Depth chart data is unavailable for this filter window.
      </div>
    );
  }

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {positions.map((position) => {
        const rowsForPosition = byPosition[position]!.sort((a, b) => {
          const bySlot = depthSlotSortKey(a.depth_slot) - depthSlotSortKey(b.depth_slot);
          if (bySlot !== 0) return bySlot;
          return a.depth_order - b.depth_order;
        });
        const rankMaps = buildMetricRankMaps(rowsForPosition, [
          "pass_yards",
          "pass_touchdowns",
          "rush_yards",
          "receptions",
          "receiving_yards",
          "touchdowns_scored",
          "pass_yards_mean",
          "rush_yards_mean",
          "receiving_yards_mean",
          "receptions_mean",
          "pass_tds_mean",
          "rush_tds_mean",
          "rec_tds_mean",
          "fantasy_points_roy",
          "fantasy_rank_position_roy",
          "role_confidence",
        ]);
        const rowIndexByRef = new Map(rowsForPosition.map((row, index) => [row, index] as const));
        return (
          <article key={position} className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-kos-text">{position}</h3>
              <span className="text-xs text-kos-text/60">{rowsForPosition.length} players</span>
            </div>
            <div className="mb-2 hidden grid-cols-[minmax(180px,1.2fr)_minmax(220px,1.7fr)_minmax(220px,1.7fr)] gap-3 px-1 text-[11px] font-semibold uppercase tracking-wide text-kos-text/55 md:grid">
              <span>Player</span>
              <span>Fantasy-Relevant Stats</span>
              <span>Rest-of-Year Projection</span>
            </div>
            <div className="space-y-2">
              {rowsForPosition.map((row) => {
                const rowIndex = rowIndexByRef.get(row) ?? -1;
                const projection = renderProjection(row, rowIndex, rankMaps);
                return (
                  <div
                    key={`${position}-${row.player_name}-${row.depth_order}`}
                    className="rounded-lg border border-white/10 bg-black/35 px-3 py-2"
                  >
                    <div className="grid gap-2 md:grid-cols-[minmax(180px,1.2fr)_minmax(220px,1.7fr)_minmax(220px,1.7fr)] md:items-center md:gap-3">
                      <div>
                        <p className="text-sm font-semibold text-kos-text">{row.player_name}</p>
                        <p className="mt-0.5 text-xs text-kos-text/60">
                          {row.depth_slot} · {formatIntelValue(row.depth_order)}
                        </p>
                        <p className="mt-1 text-[11px] text-kos-gold">
                          {row.role_confidence !== undefined
                            ? `${formatIntelValueWithRank(
                                row.role_confidence * 100,
                                rankMaps.role_confidence?.get(rowIndex),
                              )}% role confidence`
                            : "Confidence N/A"}
                        </p>
                      </div>
                      <p className="text-xs text-kos-text/80">{renderFantasyStats(row, rowIndex, rankMaps)}</p>
                      <div className="text-xs text-kos-text/80">
                        <p>{projection.primary}</p>
                        {projection.secondary ? <p className="mt-0.5 text-kos-text/60">{projection.secondary}</p> : null}
                        {projection.missing ? (
                          <span className="mt-1 inline-flex rounded-full border border-kos-gold/45 bg-kos-gold/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
                            Premium Pending
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </article>
        );
      })}
    </section>
  );
}
