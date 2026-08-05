import { MOCK_STARTER_NEEDS } from "@/lib/fantasy/mock-types";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

export function boardHasPosition(
  board: FantasyDeskRow[],
  position: string,
): boolean {
  const pos = position.toUpperCase();
  return board.some((row) => row.position.toUpperCase() === pos);
}

/** Roster needs for mock — drops K/DST requirements when board omits them. */
export function mockRosterNeeds(
  roster: FantasyDeskRow[],
  board: FantasyDeskRow[],
): Record<string, number> {
  const counts: Record<string, number> = {
    QB: 0,
    RB: 0,
    WR: 0,
    TE: 0,
    K: 0,
    DST: 0,
  };
  for (const row of roster) {
    const pos = row.position.toUpperCase();
    if (pos in counts) counts[pos] = (counts[pos] ?? 0) + 1;
  }

  const wantK = boardHasPosition(board, "K") ? MOCK_STARTER_NEEDS.K! : 0;
  const wantDst = boardHasPosition(board, "DST") ? MOCK_STARTER_NEEDS.DST! : 0;

  const needs: Record<string, number> = {
    QB: Math.max(0, MOCK_STARTER_NEEDS.QB! - (counts.QB ?? 0)),
    RB: Math.max(0, MOCK_STARTER_NEEDS.RB! - (counts.RB ?? 0)),
    WR: Math.max(0, MOCK_STARTER_NEEDS.WR! - (counts.WR ?? 0)),
    TE: Math.max(0, MOCK_STARTER_NEEDS.TE! - (counts.TE ?? 0)),
    K: Math.max(0, wantK - (counts.K ?? 0)),
    DST: Math.max(0, wantDst - (counts.DST ?? 0)),
  };

  const flexFilled = Math.max(
    0,
    (counts.RB ?? 0) -
      MOCK_STARTER_NEEDS.RB! +
      ((counts.WR ?? 0) - MOCK_STARTER_NEEDS.WR!) +
      ((counts.TE ?? 0) - MOCK_STARTER_NEEDS.TE!),
  );
  needs.FLEX = Math.max(0, MOCK_STARTER_NEEDS.FLEX! - flexFilled);
  return needs;
}
