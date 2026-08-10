/**
 * Single kickoff source for Edge Board / KEI Lines / Weekly Slate.
 * Prefer fair-lines `start_time`; fall back to game_date only when needed.
 */

export type NflKickoffSourceRow = {
  gameId: string;
  startTime?: string | null;
  gameDate?: string | null;
  commenceTime?: string | null;
};

/** Canonical kickoff ISO (or date) for a game_id — fair-lines first. */
export function resolveNflKickoffIso(
  row: NflKickoffSourceRow,
): string | null {
  const candidates = [row.startTime, row.commenceTime, row.gameDate];
  for (const c of candidates) {
    if (c == null) continue;
    const s = String(c).trim();
    if (s) return s;
  }
  return null;
}

/** Smoke pairs used by Truth Layer invariants (NE–SEA + four others). */
export const NFL_KICKOFF_SMOKE_MATCHUPS: ReadonlyArray<{
  away: string;
  home: string;
  label: string;
}> = [
  { away: "NE", home: "SEA", label: "NE@SEA" },
  { away: "KC", home: "LAC", label: "KC@LAC" },
  { away: "PHI", home: "DAL", label: "PHI@DAL" },
  { away: "BUF", home: "MIA", label: "BUF@MIA" },
  { away: "SF", home: "LAR", label: "SF@LAR" },
];
