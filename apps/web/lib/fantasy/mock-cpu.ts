/**
 * Tunable CPU picker for KosEdge mock drafts.
 *
 * Mixes ADP urgency, model value, positional need/scarcity, and persona weights.
 * Uses model rank as a soft prior only when ADP is unmatched — never shown as ADP.
 *
 * Hard guards (R1 especially): ADP reach caps and early-round value dampening so
 * lottery ADP + “value vs ADP” cannot steal the top of the draft.
 */

import type { MockCpuPersona } from "@/lib/fantasy/mock-types";
import { mockRosterNeeds } from "@/lib/fantasy/mock-roster";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

export type CpuWeights = {
  adp: number;
  value: number;
  need: number;
  rank: number;
};

function countPos(roster: FantasyDeskRow[], pos: string): number {
  return roster.filter((r) => r.position.toUpperCase() === pos).length;
}

function stableNoise(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 33 + seed.charCodeAt(i)) >>> 0;
  }
  return (hash % 1000) / 1000; // [0,1)
}

function marketPickNumber(row: FantasyDeskRow): number {
  if (row.adp != null && Number.isFinite(row.adp)) return row.adp;
  // Soft prior for CPU only when ADP unmatched.
  return row.rankOverall + 12;
}

/**
 * Max ADP ahead of the current overall pick the CPU may consider.
 * R1 is strict — lottery / late-round ADP never reaches the top of the board.
 */
export function maxAdpDeviationForRound(
  round: number,
  teamCount: number,
): number {
  const n = Math.max(2, teamCount);
  if (round <= 1) return Math.max(12, Math.floor(n * 1.25));
  if (round <= 2) return Math.floor(n * 2.5);
  if (round <= 4) return Math.floor(n * 4);
  if (round <= 8) return Math.floor(n * 6);
  return Math.floor(n * 10);
}

/** Hard reject absurd reaches (Gesicki-class ADP into R1, etc.). */
export function isCpuReachHardBlocked(opts: {
  marketAdp: number;
  overall: number;
  teamCount: number;
  position: string;
  round: number;
}): boolean {
  const { marketAdp, overall, teamCount, position, round } = opts;
  if (!Number.isFinite(marketAdp)) return false;

  const maxDev = maxAdpDeviationForRound(round, teamCount);
  if (marketAdp > overall + maxDev) return true;

  const pos = position.toUpperCase();
  if (round === 1) {
    // Absolute: nothing past the end of R2 belongs in Round 1.
    if (marketAdp > teamCount * 2) return true;
    // No lottery TE / deep QB into the top of R1.
    if (pos === "TE" && marketAdp > teamCount * 1.75) return true;
    if (pos === "QB" && marketAdp > teamCount * 2.5) return true;
  }
  return false;
}

function scarcityBonus(
  available: FantasyDeskRow[],
  position: string,
  overall: number,
): number {
  const pos = position.toUpperCase();
  const pool = available
    .filter((r) => r.position.toUpperCase() === pos)
    .sort((a, b) => a.rankOverall - b.rankOverall);
  if (pool.length === 0) return 0;
  const topLeft = pool.filter((r) => r.rankOverall <= overall + 40).length;
  if (topLeft <= 1) return 18;
  if (topLeft <= 3) return 10;
  if (pos === "TE" && topLeft <= 5) return 8;
  return 0;
}

function needScore(
  row: FantasyDeskRow,
  roster: FantasyDeskRow[],
  board: FantasyDeskRow[],
  overall: number,
  teamCount: number,
): number {
  const needs = mockRosterNeeds(roster, board);
  const pos = row.position.toUpperCase();
  const qbCount = countPos(roster, "QB");
  const round = Math.ceil(overall / teamCount);

  // Avoid brain-dead early QB stacking / early K-DST.
  // 1QB leagues rarely take QB in R1–R2 even when model VOR loves them.
  // Once a starter QB is rostered, heavily suppress QB2 until deep bench.
  if (pos === "QB" && qbCount >= 1 && round < 11) return -70;
  if (pos === "QB" && qbCount >= 1 && round < 14) return -48;
  if (pos === "QB" && qbCount >= 2) return -90;
  if ((pos === "K" || pos === "DST") && round < 12) return -55;
  if ((pos === "K" || pos === "DST") && round < 14) return -20;
  if (pos === "QB" && qbCount === 0) {
    if (round <= 2) return 2;
    if (round <= 4) return 10;
    if (round <= 6) return 20;
    return 34 + (needs.QB ?? 0) * 4;
  }

  if ((needs[pos] ?? 0) > 0) return 34 + (needs[pos] ?? 0) * 6;
  if (
    (needs.FLEX ?? 0) > 0 &&
    ["RB", "WR", "TE"].includes(pos)
  ) {
    return 20;
  }

  // Bench depth: mild preference for RB/WR after starters filled.
  if (["RB", "WR"].includes(pos) && round >= 8) return 10;
  if (pos === "TE" && countPos(roster, "TE") === 0) return 16;
  return 2;
}

export function scoreCpuCandidate(input: {
  row: FantasyDeskRow;
  roster: FantasyDeskRow[];
  board: FantasyDeskRow[];
  available: FantasyDeskRow[];
  overall: number;
  teamCount: number;
  persona: MockCpuPersona;
  weights: CpuWeights;
  teamIndex: number;
}): number {
  const {
    row,
    roster,
    board,
    available,
    overall,
    teamCount,
    persona,
    weights,
    teamIndex,
  } = input;

  const market = marketPickNumber(row);
  const round = Math.ceil(overall / teamCount);
  const pos = row.position.toUpperCase();

  if (
    isCpuReachHardBlocked({
      marketAdp: market,
      overall,
      teamCount,
      position: pos,
      round,
    })
  ) {
    return -Infinity;
  }

  const adpUrgency =
    market <= overall + 4
      ? 28
      : market <= overall + 12
        ? 18
        : market <= overall + 24
          ? 8
          : 0;
  const reachPenalty = market > overall + 35 ? -18 : market > overall + 22 ? -8 : 0;

  const qbCount = countPos(roster, "QB");

  let valueRaw =
    row.valueDelta != null && Number.isFinite(row.valueDelta)
      ? Math.max(-12, Math.min(22, row.valueDelta * 0.65))
      : 0;
  // Don't let model-vs-ADP QB "value" force early QBs in 1QB mocks.
  if (pos === "QB" && round <= 5) {
    valueRaw *= 0.25;
  }
  if (pos === "QB" && qbCount >= 1) {
    valueRaw *= 0.05;
  }
  // Early rounds: positional VORP / need must beat pure ADP-value.
  if (round <= 2) {
    valueRaw *= 0.15;
  } else if (round <= 4) {
    valueRaw *= 0.4;
  }

  let rankQuality = Math.max(0, 40 - row.rankOverall * 0.12);
  if (pos === "QB" && round <= 5) {
    rankQuality *= 0.4;
  }
  if (pos === "QB" && qbCount >= 1) {
    rankQuality *= 0.15;
  }

  // Prefer real positional surplus over ADP-value mirages early.
  let vorpRaw = 0;
  if (
    round <= 4 &&
    row.valueOverReplacement != null &&
    Number.isFinite(row.valueOverReplacement)
  ) {
    vorpRaw = Math.min(20, Math.max(0, row.valueOverReplacement * 0.1));
  }

  // Scarcity on QB2+ is noise in 1QB — don't chase the next name.
  let scarcity = scarcityBonus(available, row.position, overall);
  if (pos === "QB" && qbCount >= 1) {
    scarcity = 0;
  }
  const need = needScore(row, roster, board, overall, teamCount);

  const noise =
    (stableNoise(`${persona}|${teamIndex}|${overall}|${row.playerId}`) - 0.5) *
    6;

  return (
    weights.adp * (adpUrgency + reachPenalty) +
    weights.value * valueRaw +
    weights.need * need +
    weights.rank * (rankQuality + vorpRaw) +
    scarcity +
    noise
  );
}

export function chooseCpuPlayer(input: {
  available: FantasyDeskRow[];
  roster: FantasyDeskRow[];
  board: FantasyDeskRow[];
  overall: number;
  teamCount: number;
  persona: MockCpuPersona;
  weights: CpuWeights;
  teamIndex: number;
}): FantasyDeskRow | null {
  const { available, overall, teamCount } = input;
  if (available.length === 0) return null;

  const round = Math.ceil(overall / teamCount);

  // Score a bounded pool for speed — top ~80 by model rank among remaining.
  // Hard-filter absurd ADP reaches before scoring so lottery names never win ties.
  const pool = [...available]
    .sort((a, b) => a.rankOverall - b.rankOverall)
    .slice(0, 80)
    .filter(
      (row) =>
        !isCpuReachHardBlocked({
          marketAdp: marketPickNumber(row),
          overall,
          teamCount,
          position: row.position,
          round,
        }),
    );

  const scoringPool = pool.length > 0 ? pool : [...available]
    .sort((a, b) => a.rankOverall - b.rankOverall)
    .slice(0, 20);

  let best: FantasyDeskRow | null = null;
  let bestScore = -Infinity;
  for (const row of scoringPool) {
    const score = scoreCpuCandidate({
      ...input,
      row,
      available: scoringPool,
    });
    if (score > bestScore) {
      bestScore = score;
      best = row;
    }
  }
  return best ?? scoringPool[0] ?? null;
}
