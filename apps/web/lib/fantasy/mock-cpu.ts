/**
 * Tunable CPU picker for KosEdge mock drafts.
 *
 * Mixes ADP urgency, model value, positional need/scarcity, and persona weights.
 * Uses model rank as a soft prior only when ADP is unmatched — never shown as ADP.
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
  if (pos === "QB" && qbCount >= 1 && round < 9) return -40;
  if (pos === "QB" && qbCount >= 2 && round < 13) return -60;
  if ((pos === "K" || pos === "DST") && round < 12) return -55;
  if ((pos === "K" || pos === "DST") && round < 14) return -20;

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
  const adpUrgency =
    market <= overall + 4
      ? 28
      : market <= overall + 12
        ? 18
        : market <= overall + 24
          ? 8
          : 0;
  const reachPenalty = market > overall + 35 ? -18 : market > overall + 22 ? -8 : 0;

  const valueRaw =
    row.valueDelta != null && Number.isFinite(row.valueDelta)
      ? Math.max(-12, Math.min(22, row.valueDelta * 0.65))
      : 0;

  const rankQuality = Math.max(0, 40 - row.rankOverall * 0.12);
  const need = needScore(row, roster, board, overall, teamCount);
  const scarcity = scarcityBonus(available, row.position, overall);

  const noise =
    (stableNoise(`${persona}|${teamIndex}|${overall}|${row.playerId}`) - 0.5) *
    6;

  return (
    weights.adp * (adpUrgency + reachPenalty) +
    weights.value * valueRaw +
    weights.need * need +
    weights.rank * rankQuality +
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
  const { available } = input;
  if (available.length === 0) return null;

  // Score a bounded pool for speed — top ~80 by model rank among remaining.
  const pool = [...available]
    .sort((a, b) => a.rankOverall - b.rankOverall)
    .slice(0, 80);

  let best: FantasyDeskRow | null = null;
  let bestScore = -Infinity;
  for (const row of pool) {
    const score = scoreCpuCandidate({ ...input, row, available: pool });
    if (score > bestScore) {
      bestScore = score;
      best = row;
    }
  }
  return best ?? pool[0] ?? null;
}
