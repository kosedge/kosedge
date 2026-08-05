/**
 * Web-side port of model-service nfl_fantasy_draft_rankings pure ranking.
 * Used for preseason-fallback boards when Railway draft rankings are empty.
 */

export const POSITION_TIER_BOUNDARIES: Record<
  string,
  Array<[number, string]>
> = {
  QB: [
    [3, "elite"],
    [8, "QB1"],
    [16, "QB2"],
    [24, "streamer"],
    [10_000, "bench"],
  ],
  RB: [
    [3, "elite"],
    [12, "RB1"],
    [24, "RB2"],
    [36, "flex"],
    [10_000, "bench"],
  ],
  WR: [
    [3, "elite"],
    [12, "WR1"],
    [24, "WR2"],
    [36, "flex"],
    [10_000, "bench"],
  ],
  TE: [
    [3, "elite"],
    [8, "TE1"],
    [16, "streamer"],
    [10_000, "bench"],
  ],
  K: [
    [3, "elite"],
    [12, "K1"],
    [24, "streamer"],
    [10_000, "bench"],
  ],
  DST: [
    [3, "elite"],
    [12, "DST1"],
    [24, "streamer"],
    [10_000, "bench"],
  ],
};

const DEFAULT_TIER_BOUNDARIES: Array<[number, string]> = [
  [12, "starter"],
  [10_000, "bench"],
];

export const POSITION_REPLACEMENT_RANK: Record<string, number> = {
  QB: 12,
  TE: 12,
  RB: 30,
  WR: 30,
  K: 12,
  DST: 12,
};

const POSITIONS_APPENDED_TO_BOARD_END = new Set(["K", "DST"]);
const DEFAULT_REPLACEMENT_RANK = 24;

export function assignDraftTier(position: string, positionRank: number): string {
  const boundaries =
    POSITION_TIER_BOUNDARIES[position.toUpperCase()] ?? DEFAULT_TIER_BOUNDARIES;
  for (const [maxRank, label] of boundaries) {
    if (positionRank <= maxRank) return label;
  }
  return boundaries[boundaries.length - 1]![1];
}

export type RankablePlayer = {
  playerKey: string;
  position: string;
  totalPoints: number;
  [key: string]: unknown;
};

export function rankSeasonFantasyPlayers<T extends RankablePlayer>(
  players: T[],
): Array<
  T & {
    rankPosition: number;
    tier: string;
    replacementPoints: number;
    valueOverReplacement: number;
    rankOverall: number;
  }
> {
  const byPosition = new Map<string, Array<T & Record<string, unknown>>>();
  for (const player of players) {
    const position = String(player.position || "UNK").toUpperCase();
    const group = byPosition.get(position) ?? [];
    group.push({ ...player, position });
    byPosition.set(position, group);
  }

  const all: Array<
    T & {
      rankPosition: number;
      tier: string;
      replacementPoints: number;
      valueOverReplacement: number;
      rankOverall?: number;
    }
  > = [];

  for (const [position, group] of byPosition) {
    group.sort((a, b) => {
      const diff = Number(b.totalPoints) - Number(a.totalPoints);
      if (diff !== 0) return diff;
      return String(a.playerKey).localeCompare(String(b.playerKey));
    });
    const pointsDesc = group.map((p) => Number(p.totalPoints) || 0);
    const replacementRank =
      POSITION_REPLACEMENT_RANK[position] ?? DEFAULT_REPLACEMENT_RANK;
    const replacementPoints =
      pointsDesc.length === 0
        ? 0
        : pointsDesc[Math.min(replacementRank, pointsDesc.length) - 1]!;

    group.forEach((player, idx) => {
      const rankPosition = idx + 1;
      const totalPoints = Number(player.totalPoints) || 0;
      all.push({
        ...(player as T),
        rankPosition,
        tier: assignDraftTier(position, rankPosition),
        replacementPoints: Math.round(replacementPoints * 10000) / 10000,
        valueOverReplacement:
          Math.round((totalPoints - replacementPoints) * 10000) / 10000,
      });
    });
  }

  all.sort((a, b) => {
    const aEnd = POSITIONS_APPENDED_TO_BOARD_END.has(
      String(a.position).toUpperCase(),
    );
    const bEnd = POSITIONS_APPENDED_TO_BOARD_END.has(
      String(b.position).toUpperCase(),
    );
    if (aEnd !== bEnd) return aEnd ? 1 : -1;
    const vorDiff = b.valueOverReplacement - a.valueOverReplacement;
    if (vorDiff !== 0) return vorDiff;
    return String(a.playerKey).localeCompare(String(b.playerKey));
  });

  return all.map((player, idx) => ({
    ...player,
    rankOverall: idx + 1,
  }));
}
