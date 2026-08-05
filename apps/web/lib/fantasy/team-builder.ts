import type { FantasyDeskRow, RosterSlot } from "@/lib/fantasy/types";

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

export function rosterNeeds(rows: FantasyDeskRow[]): Record<string, number> {
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

  const needs: Record<string, number> = {};
  needs.QB = Math.max(0, DEFAULT_ROSTER_NEEDS.QB! - (counts.QB ?? 0));
  needs.RB = Math.max(0, DEFAULT_ROSTER_NEEDS.RB! - (counts.RB ?? 0));
  needs.WR = Math.max(0, DEFAULT_ROSTER_NEEDS.WR! - (counts.WR ?? 0));
  needs.TE = Math.max(0, DEFAULT_ROSTER_NEEDS.TE! - (counts.TE ?? 0));
  needs.K = Math.max(0, DEFAULT_ROSTER_NEEDS.K! - (counts.K ?? 0));
  needs.DST = Math.max(0, DEFAULT_ROSTER_NEEDS.DST! - (counts.DST ?? 0));

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

export function teamGrade(rows: FantasyDeskRow[]): {
  grade: string;
  detail: string;
  starterPoints: number;
} {
  const starterPoints = projectedStarterPoints(rows);
  const needs = rosterNeeds(rows);
  const holes = Object.entries(needs)
    .filter(([, n]) => n > 0)
    .map(([pos]) => pos);

  let grade = "C";
  if (starterPoints >= 1400 && holes.length === 0) grade = "A";
  else if (starterPoints >= 1250 && holes.length <= 1) grade = "B+";
  else if (starterPoints >= 1100) grade = "B";
  else if (starterPoints >= 950) grade = "C+";
  else if (starterPoints >= 800) grade = "C";
  else grade = "D";

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
): FantasyDeskRow[] {
  return board
    .filter(
      (row) =>
        !rosterIds.has(row.playerId) &&
        row.adp != null &&
        row.valueDelta != null,
    )
    .sort((a, b) => {
      const valueDiff = (b.valueDelta ?? 0) - (a.valueDelta ?? 0);
      if (valueDiff !== 0) return valueDiff;
      return a.rankOverall - b.rankOverall;
    })
    .slice(0, limit);
}

export function bestAvailableByNeed(
  board: FantasyDeskRow[],
  roster: FantasyDeskRow[],
  limit = 5,
): FantasyDeskRow[] {
  const needs = rosterNeeds(roster);
  const rosterIds = new Set(roster.map((r) => r.playerId));
  const priority = Object.entries(needs)
    .filter(([pos, n]) => n > 0 && pos !== "FLEX")
    .sort((a, b) => b[1] - a[1])
    .map(([pos]) => pos);

  const flexNeed = (needs.FLEX ?? 0) > 0;
  const out: FantasyDeskRow[] = [];
  const seen = new Set<string>();

  const pushFrom = (predicate: (row: FantasyDeskRow) => boolean) => {
    for (const row of board) {
      if (out.length >= limit) break;
      if (rosterIds.has(row.playerId) || seen.has(row.playerId)) continue;
      if (!predicate(row)) continue;
      out.push(row);
      seen.add(row.playerId);
    }
  };

  for (const pos of priority) {
    pushFrom((row) => row.position.toUpperCase() === pos);
  }
  if (flexNeed) {
    pushFrom((row) => ["RB", "WR", "TE"].includes(row.position.toUpperCase()));
  }
  if (out.length < limit) {
    pushFrom(() => true);
  }
  return out;
}
