export const OWNERSHIP_CONTRACT_VERSION = "nfl-dfs-ownership-v1";
export const OWNERSHIP_UNAVAILABLE_REASON = "no_defensible_source";

export type OwnershipProjection = {
  site: string;
  season: number;
  week: number;
  slateId: string;
  playerUid: string;
  status: "unavailable" | "projected" | "rejected";
  projectedOwn: number | null;
  leverage: number | null;
  source: string | null;
  reason: string;
  contractVersion: string;
};

export function unavailableOwnership(input: {
  site: string;
  season: number;
  week: number;
  slateId: string;
  playerUid: string;
}): OwnershipProjection {
  return {
    site: input.site,
    season: input.season,
    week: input.week,
    slateId: input.slateId,
    playerUid: input.playerUid,
    status: "unavailable",
    projectedOwn: null,
    leverage: null,
    source: null,
    reason: OWNERSHIP_UNAVAILABLE_REASON,
    contractVersion: OWNERSHIP_CONTRACT_VERSION,
  };
}

/** Exact production formula must be validated before this returns a number. */
export function leverageFromUpsideAndOwn(input: {
  upsideProbability: number | null;
  expectedOwnership: number | null;
}): number | null {
  void input;
  return null;
}
