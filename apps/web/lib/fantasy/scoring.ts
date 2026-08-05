import type { FantasyScoringProfile } from "@/lib/fantasy/types";

/** Canonical fantasy scoring — mirrors model-service fantasy_points_from_projection. */
export function fantasyPointsFromBox(input: {
  scoringProfile: FantasyScoringProfile;
  passYards?: number;
  passTds?: number;
  rushYards?: number;
  rushTds?: number;
  receivingYards?: number;
  receptions?: number;
  recTds?: number;
}): number {
  const pprBonus =
    input.scoringProfile === "ppr"
      ? 1
      : input.scoringProfile === "half_ppr"
        ? 0.5
        : 0;
  return (
    (input.passYards ?? 0) / 25 +
    (input.passTds ?? 0) * 4 +
    (input.rushYards ?? 0) / 10 +
    (input.rushTds ?? 0) * 6 +
    (input.receivingYards ?? 0) / 10 +
    (input.receptions ?? 0) * pprBonus +
    (input.recTds ?? 0) * 6
  );
}

/**
 * Position-aware uncertainty band when season quantiles are unavailable.
 * Wider for skill positions with more usage volatility; rookies/committee widen further.
 */
export function uncertaintyBand(input: {
  position: string;
  isRookie?: boolean;
  committeeRisk?: boolean;
}): number {
  const pos = input.position.toUpperCase();
  let band =
    pos === "QB"
      ? 0.12
      : pos === "RB"
        ? 0.22
        : pos === "WR"
          ? 0.2
          : pos === "TE"
            ? 0.18
            : 0.15;
  if (input.isRookie) band += 0.05;
  if (input.committeeRisk) band += 0.04;
  return band;
}

export function floorMedianCeilingFromMean(input: {
  medianPoints: number;
  position: string;
  isRookie?: boolean;
  committeeRisk?: boolean;
}): { floorPoints: number; medianPoints: number; ceilingPoints: number } {
  const band = uncertaintyBand(input);
  const median = Math.max(0, input.medianPoints);
  return {
    floorPoints: round1(median * (1 - band)),
    medianPoints: round1(median),
    ceilingPoints: round1(median * (1 + band)),
  };
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
