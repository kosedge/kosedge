/**
 * Resolve NFL REG week from the 2026 schedule pack when fair-lines omit week.
 *
 * Live bug (2026-08-10): Edge Board rows often ship without `week` / `seasonType`
 * even though REG Week 1 games (incl. Melbourne) appear on Full slate. Strict
 * Week 1 filter then empties the tab. The wall-chart schedule pack is the
 * same REG slate the product already trusts for the season wall chart.
 *
 * Week 1 membership (2026-08-10): schedule pack is the driver. Projections /
 * odds are attributes — REG Week 1 games never silently disappear when KEI
 * or books are missing (honest empties instead).
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import { getWallChartSchedule } from "@/lib/nfl-wall-chart-2026";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { lookupNflNeutralSite } from "@/lib/nfl-neutral-sites-2026";

const NAME_TO_ABBR = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.name.toLowerCase(), t.code] as const),
);
const ABBR_TO_NAME = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.code, t.name] as const),
);

function canonAbbr(raw: string): string {
  return canonicalizeNflTeam(raw) || String(raw || "").trim().toUpperCase();
}

/** Pack / nflverse often emit LA for Rams; product id prefers LAR. */
function packAbbr(abbr: string): string {
  const c = canonAbbr(abbr);
  return c === "LAR" ? "LA" : c;
}

function teamDisplayName(abbr: string): string {
  const c = canonAbbr(abbr);
  return ABBR_TO_NAME.get(c) || c;
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

export type NflScheduleWeekGame = {
  gameId: string;
  season: number;
  week: number;
  seasonType: "REG";
  awayAbbr: string;
  homeAbbr: string;
};

/**
 * Canonical REG slate for a week from the wall-chart schedule pack.
 * Home-side `vs` entries only (16 for Week 1).
 */
export function listNflRegWeekScheduleGames(
  week: number,
  season = 2026,
): NflScheduleWeekGame[] {
  const target = coerceNflWeek(week);
  if (target == null) return [];
  const schedule = getWallChartSchedule();
  const games: NflScheduleWeekGame[] = [];

  for (const [team, weeks] of Object.entries(schedule)) {
    const label = weeks[String(target)];
    if (!label) continue;
    const text = String(label).trim();
    if (!/^vs\s+/i.test(text)) continue;
    const opp = text.replace(/^vs\s+/i, "").trim();
    const homeAbbr = canonAbbr(team);
    const awayAbbr = canonAbbr(opp);
    if (!homeAbbr || !awayAbbr) continue;
    const weekPad = String(target).padStart(2, "0");
    games.push({
      gameId: `${season}-W${weekPad}-${packAbbr(awayAbbr)}@${packAbbr(homeAbbr)}`,
      season,
      week: target,
      seasonType: "REG",
      awayAbbr,
      homeAbbr,
    });
  }

  return games.sort((a, b) => a.gameId.localeCompare(b.gameId));
}

function orientedPairKey(awayAbbr: string, homeAbbr: string): string {
  return `${canonAbbr(awayAbbr)}|${canonAbbr(homeAbbr)}`;
}

function rowOrientedPairKey(row: EdgeBoardRow): string | null {
  const r = row as RowWeekFields;
  const game = String(r.game ?? "");
  const parsed = parseGameTeams(game);
  const away = canonAbbr(r.awayAbbr || abbrFromLabel(parsed.away));
  const home = canonAbbr(r.homeAbbr || abbrFromLabel(parsed.home));
  if (!away || !home) return null;
  return orientedPairKey(away, home);
}

export type NflScheduleWeekDiff = {
  week: number;
  scheduleCount: number;
  boardCount: number;
  missing: NflScheduleWeekGame[];
  /** game_ids on schedule but not represented on the board */
  missingGameIds: string[];
  ok: boolean;
};

/** Diff board game membership vs schedule pack for a REG week. */
export function diffNflBoardVsScheduleWeek(
  rows: EdgeBoardRow[],
  week: number,
): NflScheduleWeekDiff {
  const schedule = listNflRegWeekScheduleGames(week);
  const present = new Set<string>();
  for (const row of rows) {
    const key = rowOrientedPairKey(row);
    if (key) present.add(key);
  }
  const missing = schedule.filter(
    (g) => !present.has(orientedPairKey(g.awayAbbr, g.homeAbbr)),
  );
  const boardCount = new Set(
    rows
      .map(rowOrientedPairKey)
      .filter((k): k is string => Boolean(k)),
  ).size;
  return {
    week: coerceNflWeek(week) ?? week,
    scheduleCount: schedule.length,
    boardCount,
    missing,
    missingGameIds: missing.map((g) => g.gameId),
    ok: missing.length === 0 && boardCount >= schedule.length,
  };
}

function emptyScheduleEdgeRows(game: NflScheduleWeekGame): EdgeBoardRow[] {
  const awayName = teamDisplayName(game.awayAbbr);
  const homeName = teamDisplayName(game.homeAbbr);
  const label = `${awayName} @ ${homeName}`;
  const shared = {
    game: label,
    week: game.week,
    seasonType: game.seasonType,
    awayAbbr: game.awayAbbr,
    homeAbbr: game.homeAbbr,
    gamesPlayedAway: game.week === 1 ? 0 : undefined,
    gamesPlayedHome: game.week === 1 ? 0 : undefined,
  };
  return [
    {
      id: `${game.gameId}-spread`,
      market: "Spread",
      ...shared,
    } as EdgeBoardRow,
    {
      id: `${game.gameId}-total`,
      market: "Total",
      ...shared,
    } as EdgeBoardRow,
  ];
}

/**
 * Schedule-driven membership: every REG schedule-pack game for `week` appears
 * on the board. Missing KEI / odds → honest empty rows (no silent drop).
 * Also force-stamps week + REG on any already-present schedule matchup.
 */
export function ensureNflScheduleWeekOnBoard(
  rows: EdgeBoardRow[],
  week: number,
): EdgeBoardRow[] {
  const schedule = listNflRegWeekScheduleGames(week);
  if (!schedule.length) return rows;

  const byPair = new Map<string, EdgeBoardRow[]>();
  for (const row of rows) {
    const key = rowOrientedPairKey(row);
    if (!key) continue;
    const list = byPair.get(key);
    if (list) list.push(row);
    else byPair.set(key, [row]);
  }

  const out = [...rows];
  const target = coerceNflWeek(week);
  for (const game of schedule) {
    const key = orientedPairKey(game.awayAbbr, game.homeAbbr);
    const existing = byPair.get(key);
    if (existing?.length) {
      for (const row of existing) {
        const r = row as RowWeekFields;
        if (target != null) r.week = target;
        r.seasonType = "REG";
        if (!r.awayAbbr) r.awayAbbr = game.awayAbbr;
        if (!r.homeAbbr) r.homeAbbr = game.homeAbbr;
        if (target === 1) {
          if (r.gamesPlayedAway == null) r.gamesPlayedAway = 0;
          if (r.gamesPlayedHome == null) r.gamesPlayedHome = 0;
        }
      }
      continue;
    }
    if (typeof console !== "undefined" && console.warn) {
      console.warn(
        `[edge-board] schedule game missing from board — seeding empty rows: ${game.gameId}`,
      );
    }
    const seeded = emptyScheduleEdgeRows(game);
    out.push(...seeded);
    byPair.set(key, seeded);
  }

  return out;
}
