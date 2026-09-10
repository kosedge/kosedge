/**
 * DK Classic / FD Classic scoring of football production.
 * Not Half-PPR. Never Ceiling = projection × 1.35.
 */

import { canonicalDfsSite } from "@/lib/nfl-dfs-identity";

export const DFS_SCORING_VERSION = "nfl-dfs-scoring-v1";
export const DK_CLASSIC = "dk_classic";
export const FD_CLASSIC = "fd_classic";

export type DfsProduction = {
  passYards: number;
  passTds: number;
  rushYards: number;
  rushTds: number;
  receivingYards: number;
  receptions: number;
  recTds: number;
  passYardsStd?: number | null;
  rushYardsStd?: number | null;
  receivingYardsStd?: number | null;
};

export type DfsOutcome = {
  pass_yards?: number;
  rush_yards?: number;
  receiving_yards?: number;
  receptions?: number;
  touchdowns?: number;
};

export type DfsScoredPoints = {
  scoringSystem: string;
  projection: number;
  median: number | null;
  floor: number | null;
  ceiling: number | null;
  distributionAvailable: boolean;
  bonusExpectation: number;
  unavailableReason: string | null;
};

function scoringSystemForSite(site: string): string {
  return canonicalDfsSite(site) === "FD" ? FD_CLASSIC : DK_CLASSIC;
}

function normalSf(threshold: number, mean: number, std: number): number {
  if (!(std > 0)) return mean >= threshold ? 1 : 0;
  const z = (threshold - mean) / std;
  return 0.5 * erfc(z / Math.SQRT2);
}

function erfc(x: number): number {
  const z = Math.abs(x);
  const t = 1 / (1 + 0.5 * z);
  const ans =
    t *
    Math.exp(
      -z * z -
        1.26551223 +
        t *
          (1.00002368 +
            t *
              (0.37409196 +
                t *
                  (0.09678418 +
                    t *
                      (-0.18628806 +
                        t *
                          (0.27886807 +
                            t *
                              (-1.13520398 +
                                t *
                                  (1.48851587 +
                                    t * (-0.82215223 + t * 0.17087277)))))))),
    );
  return x >= 0 ? ans : 2 - ans;
}

export function scoreCountingLine(input: {
  scoringSystem: string;
  passYards?: number;
  passTds?: number;
  rushYards?: number;
  rushTds?: number;
  receivingYards?: number;
  receptions?: number;
  recTds?: number;
  applyThresholdBonuses?: boolean;
}): number {
  const system = input.scoringSystem.trim().toLowerCase();
  const passYards = input.passYards ?? 0;
  const rushYards = input.rushYards ?? 0;
  const receivingYards = input.receivingYards ?? 0;
  const recBonus = system === FD_CLASSIC ? 0.5 : 1;
  let pts =
    passYards * 0.04 +
    (input.passTds ?? 0) * 4 +
    rushYards * 0.1 +
    (input.rushTds ?? 0) * 6 +
    receivingYards * 0.1 +
    (input.receptions ?? 0) * recBonus +
    (input.recTds ?? 0) * 6;
  if (system === DK_CLASSIC && input.applyThresholdBonuses !== false) {
    if (passYards >= 300) pts += 3;
    if (rushYards >= 100) pts += 3;
    if (receivingYards >= 100) pts += 3;
  }
  return Math.round(pts * 10000) / 10000;
}

function stdsSourceBacked(prod: DfsProduction): boolean {
  const stds = [
    prod.passYardsStd,
    prod.rushYardsStd,
    prod.receivingYardsStd,
  ].filter((n): n is number => typeof n === "number" && n > 0);
  return stds.length >= 2;
}

function outcomeHasStats(outcome?: DfsOutcome | null): boolean {
  if (!outcome) return false;
  return (
    outcome.pass_yards != null ||
    outcome.rush_yards != null ||
    outcome.receiving_yards != null ||
    outcome.receptions != null ||
    outcome.touchdowns != null
  );
}

function scaleTd(meanTd: number, outcomeTd: number | undefined, total: number): number {
  if (outcomeTd == null || !(total > 0)) return meanTd;
  return Math.max(0, meanTd * (outcomeTd / total));
}

export function scoreProductionForSite(
  prod: DfsProduction,
  site: string,
  outcomes?: {
    floor?: DfsOutcome | null;
    median?: DfsOutcome | null;
    ceiling?: DfsOutcome | null;
  },
): DfsScoredPoints {
  const system = scoringSystemForSite(site);
  const stdsValid = stdsSourceBacked(prod);
  let bonus = 0;
  if (system === DK_CLASSIC) {
    if (stdsValid) {
      bonus +=
        3 * normalSf(300, prod.passYards, prod.passYardsStd ?? 0) +
        3 * normalSf(100, prod.rushYards, prod.rushYardsStd ?? 0) +
        3 * normalSf(100, prod.receivingYards, prod.receivingYardsStd ?? 0);
    } else {
      if (prod.passYards >= 300) bonus += 3;
      if (prod.rushYards >= 100) bonus += 3;
      if (prod.receivingYards >= 100) bonus += 3;
    }
    bonus = Math.round(bonus * 10000) / 10000;
  }
  const projection =
    scoreCountingLine({
      scoringSystem: system,
      passYards: prod.passYards,
      passTds: prod.passTds,
      rushYards: prod.rushYards,
      rushTds: prod.rushTds,
      receivingYards: prod.receivingYards,
      receptions: prod.receptions,
      recTds: prod.recTds,
      applyThresholdBonuses: false,
    }) + bonus;

  const hasDist =
    outcomeHasStats(outcomes?.floor) && outcomeHasStats(outcomes?.ceiling);
  if (!hasDist) {
    return {
      scoringSystem: system,
      projection: Math.round(projection * 10000) / 10000,
      median: null,
      floor: null,
      ceiling: null,
      distributionAvailable: false,
      bonusExpectation: bonus,
      unavailableReason: "distribution_unavailable",
    };
  }

  const totalTd = prod.passTds + prod.rushTds + prod.recTds;
  const scoreOutcome = (outcome: DfsOutcome, bonuses: boolean) =>
    scoreCountingLine({
      scoringSystem: system,
      passYards: outcome.pass_yards ?? prod.passYards,
      passTds: scaleTd(prod.passTds, outcome.touchdowns, totalTd),
      rushYards: outcome.rush_yards ?? prod.rushYards,
      rushTds: scaleTd(prod.rushTds, outcome.touchdowns, totalTd),
      receivingYards: outcome.receiving_yards ?? prod.receivingYards,
      receptions: outcome.receptions ?? prod.receptions,
      recTds: scaleTd(prod.recTds, outcome.touchdowns, totalTd),
      applyThresholdBonuses: bonuses,
    });

  const floorPts = scoreOutcome(outcomes?.floor ?? {}, system === DK_CLASSIC);
  const ceilingPts = scoreOutcome(outcomes?.ceiling ?? {}, system === DK_CLASSIC);
  const medianPts = outcomeHasStats(outcomes?.median)
    ? scoreOutcome(outcomes?.median ?? {}, false) + bonus
    : projection;

  return {
    scoringSystem: system,
    projection: Math.round(projection * 10000) / 10000,
    median: Math.round(medianPts * 10000) / 10000,
    floor: Math.round(Math.min(floorPts, medianPts) * 10000) / 10000,
    ceiling: Math.round(Math.max(ceilingPts, medianPts) * 10000) / 10000,
    distributionAvailable: true,
    bonusExpectation: bonus,
    unavailableReason: null,
  };
}

/** Guard: the old research-shell heuristic is forbidden. */
export function inventedCeilingFromMean(projection: number): number {
  return projection * 1.35;
}
