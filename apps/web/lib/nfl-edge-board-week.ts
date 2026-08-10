/**
 * Resolve NFL REG week from the 2026 schedule pack when fair-lines omit week.
 *
 * Live bug (2026-08-10): Edge Board rows often ship without `week` / `seasonType`
 * even though REG Week 1 games (incl. Melbourne) appear on Full slate. Strict
 * Week 1 filter then empties the tab. The wall-chart schedule pack is the
 * same REG slate the product already trusts for the season wall chart.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import { getWallChartSchedule } from "@/lib/nfl-wall-chart-2026";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { lookupNflNeutralSite } from "@/lib/nfl-neutral-sites-2026";

const NAME_TO_ABBR = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.name.toLowerCase(), t.code] as const),
);

function canonAbbr(raw: string): string {
  return canonicalizeNflTeam(raw) || String(raw || "").trim().toUpperCase();
}

function abbrFromLabel(label: string): string {
  const raw = String(label || "").trim();
  if (!raw) return "";
  const asAbbr = canonAbbr(raw);
  if (asAbbr && asAbbr.length <= 3) return asAbbr;
  const byName = NAME_TO_ABBR.get(raw.toLowerCase());
  if (byName) return canonAbbr(byName);
  const last = raw.split(/\s+/).pop()?.toLowerCase() ?? "";
  for (const t of NFL_TEAM_DIRECTORY) {
    const nick = t.name.split(/\s+/).pop()?.toLowerCase();
    if (nick && nick === last) return canonAbbr(t.code);
  }
  return asAbbr;
}

function parseGameTeams(game: string): { away: string; home: string } {
  const parts = game.includes(" @ ")
    ? game.split(" @ ")
    : game.split(" vs ");
  return {
    away: (parts[0] ?? "Away").trim() || "Away",
    home: (parts[1] ?? "Home").trim() || "Home",
  };
}

/** Coerce week from number | numeric string | null. */
export function coerceNflWeek(raw: unknown): number | null {
  if (raw == null || raw === "") return null;
  const n = typeof raw === "number" ? raw : Number(raw);
  if (!Number.isFinite(n)) return null;
  const w = Math.trunc(n);
  return w >= 1 && w <= 22 ? w : null;
}

type MatchupWeekIndex = Map<string, number>;

let cachedIndex: MatchupWeekIndex | null = null;

function pairKey(a: string, b: string): string {
  return [canonAbbr(a), canonAbbr(b)].sort().join("|");
}

/** Build away|home → week and sorted-pair → week from wall-chart pack. */
export function buildNflScheduleWeekIndex(): MatchupWeekIndex {
  if (cachedIndex) return cachedIndex;
  const schedule = getWallChartSchedule();
  const index: MatchupWeekIndex = new Map();

  for (const [team, weeks] of Object.entries(schedule)) {
    const teamAbbr = canonAbbr(team);
    for (const [weekStr, label] of Object.entries(weeks)) {
      const week = coerceNflWeek(weekStr);
      if (week == null || !label) continue;
      const opp = String(label)
        .replace(/^@\s*/, "")
        .replace(/^vs\s*/i, "")
        .trim();
      const oppAbbr = canonAbbr(opp);
      if (!teamAbbr || !oppAbbr) continue;
      const isAway = String(label).trim().startsWith("@");
      const away = isAway ? teamAbbr : oppAbbr;
      const home = isAway ? oppAbbr : teamAbbr;
      index.set(`${away}|${home}`, week);
      index.set(pairKey(away, home), week);
    }
  }

  cachedIndex = index;
  return index;
}

/**
 * Look up REG week for a matchup from the schedule pack.
 * Prefers oriented away@home; falls back to unordered pair; then neutral table.
 */
export function lookupNflScheduleWeek(args: {
  homeAbbr: string;
  awayAbbr: string;
}): number | null {
  const home = canonAbbr(args.homeAbbr);
  const away = canonAbbr(args.awayAbbr);
  if (!home || !away) return null;
  const index = buildNflScheduleWeekIndex();
  const oriented = index.get(`${away}|${home}`);
  if (oriented != null) return oriented;
  const unordered = index.get(pairKey(away, home));
  if (unordered != null) return unordered;
  const neutral = lookupNflNeutralSite({ week: null, homeAbbr: home, awayAbbr: away });
  return neutral?.week ?? null;
}

type RowWeekFields = EdgeBoardRow & {
  week?: number | string | null;
  seasonType?: string | null;
  homeAbbr?: string;
  awayAbbr?: string;
  gamesPlayedAway?: number;
  gamesPlayedHome?: number;
};

/**
 * Stamp missing week / REG seasonType from the 2026 schedule pack.
 * Never invents PRE; never overwrites a finite upstream week.
 * Safe to run before Week 1 strict filter.
 */
export function stampNflEdgeBoardWeeksFromSchedule(
  rows: EdgeBoardRow[],
): EdgeBoardRow[] {
  if (!rows.length) return rows;

  for (const r of rows) {
    const row = r as RowWeekFields;
    const existing = coerceNflWeek(row.week);
    if (existing != null) {
      row.week = existing;
    } else {
      const game = String(row.game ?? "");
      const { away, home } = parseGameTeams(game);
      const awayAbbr = canonAbbr(row.awayAbbr || abbrFromLabel(away));
      const homeAbbr = canonAbbr(row.homeAbbr || abbrFromLabel(home));
      const looked = lookupNflScheduleWeek({ homeAbbr, awayAbbr });
      if (looked != null) {
        row.week = looked;
        if (!row.awayAbbr) row.awayAbbr = awayAbbr;
        if (!row.homeAbbr) row.homeAbbr = homeAbbr;
      }
    }

    const st = String(row.seasonType ?? "")
      .trim()
      .toUpperCase();
    // Schedule pack is REG only. Fill missing seasonType so PRE is never implied.
    if (!st) {
      row.seasonType = "REG";
    }

    if (coerceNflWeek(row.week) === 1) {
      if (row.gamesPlayedAway == null) row.gamesPlayedAway = 0;
      if (row.gamesPlayedHome == null) row.gamesPlayedHome = 0;
    }
  }

  return rows;
}
