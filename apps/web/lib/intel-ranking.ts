export type RankDirection = "asc" | "desc";

// Competition ranking policy: ties share rank and next rank skips ahead (1, 1, 3).
const METRIC_RANK_DIRECTIONS: Record<string, RankDirection> = {
  wins: "desc",
  losses: "asc",
  ties: "desc",
  win_pct: "desc",
  points_for: "desc",
  points_against: "asc",
  point_diff: "desc",
  games_played: "desc",
  offensive_plays: "desc",
  defensive_plays: "desc",
  pass_rate: "desc",
  early_down_pass_rate: "desc",
  red_zone_td_rate: "desc",
  success_rate_offense: "desc",
  success_rate_defense_allowed: "asc",
  epa_per_play_offense: "desc",
  epa_per_play_defense_allowed: "asc",
  pressure_rate_allowed: "asc",
  pressure_rate_generated: "desc",
  depth_order: "asc",
  role_confidence: "desc",
  pass_yards: "desc",
  pass_touchdowns: "desc",
  rush_yards: "desc",
  receptions: "desc",
  receiving_yards: "desc",
  touchdowns_scored: "desc",
  pass_yards_mean: "desc",
  rush_yards_mean: "desc",
  receiving_yards_mean: "desc",
  receptions_mean: "desc",
  pass_tds_mean: "desc",
  rush_tds_mean: "desc",
  rec_tds_mean: "desc",
  anytime_td_prob: "desc",
  fantasy_points_roy: "desc",
  fantasy_floor_roy: "desc",
  fantasy_ceiling_roy: "desc",
  fantasy_rank_position_roy: "asc",
  fantasy_tier_roy: "asc",
};

export function getMetricRankDirection(
  metricKey: string,
): RankDirection | null {
  return METRIC_RANK_DIRECTIONS[metricKey] ?? null;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function computeMetricRanks(
  rows: object[],
  metricKey: string,
  direction = getMetricRankDirection(metricKey),
): Map<number, number> {
  const empty = new Map<number, number>();
  if (!direction) return empty;

  const sortable = rows
    .map((row, index) => ({
      index,
      value: toFiniteNumber((row as Record<string, unknown>)[metricKey]),
    }))
    .filter(
      (entry): entry is { index: number; value: number } =>
        entry.value !== null,
    );

  if (sortable.length === 0) return empty;

  sortable.sort((left, right) => {
    const byValue =
      direction === "desc"
        ? right.value - left.value
        : left.value - right.value;
    if (byValue !== 0) return byValue;
    return left.index - right.index;
  });

  let previousValue: number | null = null;
  let previousRank = 0;
  for (let sortedIndex = 0; sortedIndex < sortable.length; sortedIndex += 1) {
    const current = sortable[sortedIndex]!;
    if (previousValue === null || current.value !== previousValue) {
      previousRank = sortedIndex + 1;
      previousValue = current.value;
    }
    empty.set(current.index, previousRank);
  }

  return empty;
}

export function buildMetricRankMaps(
  rows: object[],
  metricKeys: string[],
): Record<string, Map<number, number>> {
  const uniqueKeys = Array.from(new Set(metricKeys));
  return uniqueKeys.reduce<Record<string, Map<number, number>>>((acc, key) => {
    acc[key] = computeMetricRanks(rows, key);
    return acc;
  }, {});
}
