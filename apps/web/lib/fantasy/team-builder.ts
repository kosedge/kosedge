import { boardHasPosition } from "@/lib/fantasy/mock-roster";
import {
  bestAvailableByNeedAware,
  bestAvailableByValueAware,
  type ValueAwareContext,
  type ValueAwareSuggestion,
} from "@/lib/fantasy/value-aware-recs";
import type { FantasyDeskRow, RosterSlot } from "@/lib/fantasy/types";

export type { ValueAwareContext, ValueAwareSuggestion };

export const STARTER_SLOTS: RosterSlot[] = [
  "QB",
  "RB1",
  "RB2",
  "WR1",
  "WR2",
  "TE",
  "FLEX",
  "K",
  "DST",
];

export const DEFAULT_ROSTER_NEEDS: Record<string, number> = {
  QB: 1,
  RB: 2,
  WR: 2,
  TE: 1,
  FLEX: 1,
  K: 1,
  DST: 1,
};

export type BuiltRoster = {
  playerIds: string[];
  byId: Map<string, FantasyDeskRow>;
};

/**
 * Roster holes for builder grade / suggestions.
 * When `board` is provided and omits K/DST (preseason path), those slots are
 * not required — scoring matches the “K/DST unavailable” UI copy.
 */
export function rosterNeeds(
  rows: FantasyDeskRow[],
  board?: FantasyDeskRow[],
): Record<string, number> {
  const counts: Record<string, number> = {
    QB: 0,
    RB: 0,
    WR: 0,
    TE: 0,
    K: 0,
    DST: 0,
  };
  for (const row of rows) {
    const pos = row.position.toUpperCase();
    if (pos in counts) counts[pos] = (counts[pos] ?? 0) + 1;
  }

  const wantK =
    board == null || boardHasPosition(board, "K") ? DEFAULT_ROSTER_NEEDS.K! : 0;
  const wantDst =
    board == null || boardHasPosition(board, "DST")
      ? DEFAULT_ROSTER_NEEDS.DST!
      : 0;

  const needs: Record<string, number> = {};
  needs.QB = Math.max(0, DEFAULT_ROSTER_NEEDS.QB! - (counts.QB ?? 0));
  needs.RB = Math.max(0, DEFAULT_ROSTER_NEEDS.RB! - (counts.RB ?? 0));
  needs.WR = Math.max(0, DEFAULT_ROSTER_NEEDS.WR! - (counts.WR ?? 0));
  needs.TE = Math.max(0, DEFAULT_ROSTER_NEEDS.TE! - (counts.TE ?? 0));
  needs.K = Math.max(0, wantK - (counts.K ?? 0));
  needs.DST = Math.max(0, wantDst - (counts.DST ?? 0));

  const flexFilled = Math.max(
    0,
    (counts.RB ?? 0) -
      DEFAULT_ROSTER_NEEDS.RB! +
      ((counts.WR ?? 0) - DEFAULT_ROSTER_NEEDS.WR!) +
      ((counts.TE ?? 0) - DEFAULT_ROSTER_NEEDS.TE!),
  );
  needs.FLEX = Math.max(0, DEFAULT_ROSTER_NEEDS.FLEX! - flexFilled);
  return needs;
}

export function projectedStarterPoints(rows: FantasyDeskRow[]): number {
  const byPos = (pos: string) =>
    rows
      .filter((r) => r.position.toUpperCase() === pos)
      .sort((a, b) => b.medianPoints - a.medianPoints);

  const qb = byPos("QB")[0];
  const rbs = byPos("RB");
  const wrs = byPos("WR");
  const tes = byPos("TE");
  const k = byPos("K")[0];
  const dst = byPos("DST")[0];

  const starters: FantasyDeskRow[] = [];
  if (qb) starters.push(qb);
  starters.push(...rbs.slice(0, 2));
  starters.push(...wrs.slice(0, 2));
  if (tes[0]) starters.push(tes[0]);

  const used = new Set(starters.map((r) => r.playerId));
  const flexPool = [...rbs.slice(2), ...wrs.slice(2), ...tes.slice(1)].filter(
    (r) => !used.has(r.playerId),
  );
  flexPool.sort((a, b) => b.medianPoints - a.medianPoints);
  if (flexPool[0]) starters.push(flexPool[0]);
  if (k) starters.push(k);
  if (dst) starters.push(dst);

  return starters.reduce((sum, row) => sum + row.medianPoints, 0);
}

/**
 * Letter grade for Builder / Mock post-draft.
 * Incomplete rosters (any required hole, including K/DST when the format
 * has them) never get B or above — points alone are not enough.
 */
export function letterGradeFromStarters(
  starterPoints: number,
  holes: string[],
): string {
  if (holes.length > 0) {
    if (starterPoints >= 950) return "C+";
    if (starterPoints >= 800) return "C";
    return "D";
  }
  if (starterPoints >= 1400) return "A";
  if (starterPoints >= 1250) return "B+";
  if (starterPoints >= 1100) return "B";
  if (starterPoints >= 950) return "C+";
  if (starterPoints >= 800) return "C";
  return "D";
}

export function teamGrade(
  rows: FantasyDeskRow[],
  board?: FantasyDeskRow[],
): {
  grade: string;
  detail: string;
  starterPoints: number;
} {
  const starterPoints = projectedStarterPoints(rows);
  const needs = rosterNeeds(rows, board);
  const holes = Object.entries(needs)
    .filter(([, n]) => n > 0)
    .map(([pos]) => pos);

  const grade = letterGradeFromStarters(starterPoints, holes);

  const detail =
    holes.length === 0
      ? `Starters project ~${starterPoints.toFixed(0)} season fantasy points.`
      : `Starters ~${starterPoints.toFixed(0)} pts · still need ${holes.join(", ")}.`;

  return { grade, detail, starterPoints };
}

export function bestAvailableByValue(
  board: FantasyDeskRow[],
  rosterIds: Set<string>,
  limit = 5,
  ctx?: Pick<ValueAwareContext, "pickOverall" | "roster">,
): ValueAwareSuggestion[] {
  const available = board.filter((row) => !rosterIds.has(row.playerId));
  const roster =
    ctx?.roster ?? board.filter((row) => rosterIds.has(row.playerId));
  return bestAvailableByValueAware(
    available,
    {
      pickOverall: ctx?.pickOverall,
      roster,
      available,
      needs: rosterNeeds(roster, board),
    },
    limit,
  );
}

export function bestAvailableByNeed(
  board: FantasyDeskRow[],
  roster: FantasyDeskRow[],
  limit = 5,
  ctx?: Pick<ValueAwareContext, "pickOverall">,
): ValueAwareSuggestion[] {
  const rosterIds = new Set(roster.map((r) => r.playerId));
  const available = board.filter((row) => !rosterIds.has(row.playerId));
  return bestAvailableByNeedAware(
    available,
    {
      pickOverall: ctx?.pickOverall,
      roster,
      available,
      needs: rosterNeeds(roster, board),
    },
    limit,
  );
}
