/**
 * Single kickoff source for Edge Board / KEI Lines / Weekly Slate.
 * Canonical REG pack wins over odds commence / fair-lines start_time.
 */

import { canonicalKickoffForMatchup } from "@/lib/nfl-canonical-schedule";

export type NflKickoffSourceRow = {
  gameId: string;
  season?: number | null;
  week?: number | null;
  awayAbbr?: string | null;
  homeAbbr?: string | null;
  startTime?: string | null;
  gameDate?: string | null;
  commenceTime?: string | null;
};

/** Canonical kickoff ISO for display — pack first, then fair-lines / odds. */
export function resolveNflKickoffIso(
  row: NflKickoffSourceRow,
): string | null {
  const packed = canonicalKickoffForMatchup({
    gameId: row.gameId,
    season: row.season,
    week: row.week,
    awayAbbr: row.awayAbbr,
    homeAbbr: row.homeAbbr,
  });
  if (packed.found) return packed.kickoffUtc;
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
