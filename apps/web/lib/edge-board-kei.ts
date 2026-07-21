/**
 * Merge KEI lines (our projected spread and O/U) into edge board rows.
 * Used by /api/edge-board/[sport]/today and the edge-board page to populate
 * sport-specific KEI columns (KEICMB, KEINFL, …) on the shared board.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";

function normalizeGameKey(game: string): string {
  return game
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/\s*@\s*/g, " @ ")
    .replace(/['.]/g, "")
    .trim();
}

/** Build keys for matching: full "away @ home" and short forms so Odds API and KEI names match. */
function gameKeys(game: string): string[] {
  const n = normalizeGameKey(game);
  const parts = n.split(/\s*@\s*/);
  if (parts.length !== 2) return [n];
  const take = (s: string, words: number) =>
    s
      .trim()
      .replace(/['.]/g, "")
      .split(/\s+/)
      .slice(0, words)
      .join(" ")
      .toLowerCase();
  const away = parts[0]!.trim().replace(/['.]/g, "");
  const home = parts[1]!.trim().replace(/['.]/g, "");
  const keys = [n, `${away} @ ${home}`];
  const shortAway = take(parts[0]!, 2);
  const shortHome = take(parts[1]!, 2);
  if (shortAway !== away || shortHome !== home) {
    keys.push(`${shortAway} @ ${shortHome}`);
  }
  const oneAway = take(parts[0]!, 1);
  const oneHome = take(parts[1]!, 1);
  if (oneAway !== away || oneHome !== home) {
    keys.push(`${oneAway} @ ${oneHome}`);
  }
  return [...new Set(keys)];
}

const NFL_CODE_TO_NAME = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.code.toLowerCase(), t.name.toLowerCase()] as const),
);
const NFL_NAME_TO_CODE = new Map(
  NFL_TEAM_DIRECTORY.map((t) => [t.name.toLowerCase(), t.code.toLowerCase()] as const),
);

/** Expand / compress NFL team labels so "NE @ SEA" matches "New England Patriots @ Seattle Seahawks". */
function nflTeamAliases(label: string): string[] {
  const raw = label.trim().toLowerCase().replace(/['.]/g, "");
  if (!raw) return [];
  const aliases = new Set<string>([raw]);
  const asCode = NFL_NAME_TO_CODE.get(raw);
  if (asCode) aliases.add(asCode);
  const fromCode = NFL_CODE_TO_NAME.get(raw);
  if (fromCode) aliases.add(fromCode);
  // nickname match ("patriots", "seahawks")
  const words = raw.split(/\s+/);
  if (words.length > 1) {
    aliases.add(words[words.length - 1]!);
  }
  return [...aliases];
}

function nflGameKeys(awayTeam: string, homeTeam: string): string[] {
  const awayAliases = nflTeamAliases(awayTeam);
  const homeAliases = nflTeamAliases(homeTeam);
  const keys: string[] = [];
  for (const a of awayAliases) {
    for (const h of homeAliases) {
      keys.push(...gameKeys(`${a} @ ${h}`));
    }
  }
  return [...new Set(keys)];
}

function formatSpread(projSpreadHome: number): string {
  const n = Math.round(projSpreadHome * 10) / 10;
  if (n >= 0) return `+${n}`;
  return String(n);
}

function registerGame(
  byGame: Map<string, { projSpreadHome: number | null; projTotal: number | null }>,
  sportKey: string,
  g: KeiLineGame,
) {
  const value = {
    projSpreadHome: g.projSpreadHome ?? null,
    projTotal: g.projTotal ?? null,
  };
  const keys =
    sportKey.toLowerCase() === "nfl"
      ? nflGameKeys(g.awayTeam, g.homeTeam)
      : gameKeys(`${g.awayTeam} @ ${g.homeTeam}`);

  // Also register explicit abbr fields when present on NFL exports.
  if (sportKey.toLowerCase() === "nfl" && g.awayAbbr && g.homeAbbr) {
    keys.push(...nflGameKeys(g.awayAbbr, g.homeAbbr));
  }

  for (const key of new Set(keys)) {
    byGame.set(key, value);
  }
}

const ET = "America/New_York";

function formatKeiCommenceTime(iso: string | undefined): string | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return undefined;
  const date = d.toLocaleDateString("en-US", {
    timeZone: ET,
    month: "2-digit",
    day: "2-digit",
  });
  const time = d.toLocaleTimeString("en-US", {
    timeZone: ET,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${date} ${time} ET`;
}

function rowMatchKeys(sportKey: string, game: string): string[] {
  const parts = game.split(/\s*@\s*/);
  if (sportKey.toLowerCase() === "nfl" && parts.length === 2) {
    return nflGameKeys(parts[0]!, parts[1]!);
  }
  return gameKeys(game);
}

/**
 * Ensure every KEI/fair-line game appears on the board (PLAY / LEAN / PASS alike).
 * Odds rows win when present; missing games get skeleton Spread + Total rows.
 */
export function ensureAllKeiGamesOnBoard(
  rows: EdgeBoardRow[],
  sportKey: string,
  games: KeiLineGame[],
): EdgeBoardRow[] {
  if (!games.length) return rows;

  const covered = new Set<string>();
  for (const row of rows) {
    if (!row?.game) continue;
    for (const key of rowMatchKeys(sportKey, row.game)) {
      covered.add(key);
    }
  }

  const seeded: EdgeBoardRow[] = [...rows];
  for (const g of games) {
    const gameStr = `${g.awayTeam} @ ${g.homeTeam}`;
    const keys = rowMatchKeys(sportKey, gameStr);
    if (keys.some((k) => covered.has(k))) continue;

    const idBase =
      g.id ||
      `${sportKey}-${g.awayAbbr ?? g.awayTeam}-${g.homeAbbr ?? g.homeTeam}-${g.commenceTime ?? "tba"}`;
    const time = formatKeiCommenceTime(g.commenceTime);
    seeded.push({
      id: `${idBase}-spread`,
      game: gameStr,
      time,
      commenceTime: g.commenceTime,
      market: "Spread",
    });
    seeded.push({
      id: `${idBase}-total`,
      game: gameStr,
      time,
      commenceTime: g.commenceTime,
      market: "Total",
    });
    for (const key of keys) covered.add(key);
  }

  return seeded;
}

/**
 * Merges KEI projections into edge board rows. Mutates rows in place and returns them.
 * Each row with market "Spread" gets row.kei = our projected home spread (e.g. "-5.2").
 * Each row with market "Total" gets row.kei = our projected total (e.g. "148.5").
 * Pass gamesOverride for NFL live fair-lines (or tests); otherwise reads kei_lines_*.json.
 */
export function mergeKeiIntoEdgeBoardRows(
  rows: EdgeBoardRow[],
  sportKey: string,
  gamesOverride?: KeiLineGame[],
): EdgeBoardRow[] {
  const games = gamesOverride ?? getKeiLines(sportKey);
  if (!games.length) return rows;

  const byGame = new Map<
    string,
    { projSpreadHome: number | null; projTotal: number | null }
  >();
  for (const g of games) {
    registerGame(byGame, sportKey, g);
  }

  for (const row of rows) {
    const game = row?.game;
    if (!game) continue;
    const parts = game.split(/\s*@\s*/);
    const keys =
      sportKey.toLowerCase() === "nfl" && parts.length === 2
        ? nflGameKeys(parts[0]!, parts[1]!)
        : gameKeys(game);
    let proj:
      | { projSpreadHome: number | null; projTotal: number | null }
      | undefined;
    for (const key of keys) {
      proj = byGame.get(key);
      if (proj) break;
    }
    if (!proj) continue;

    if (row.market === "Spread" && proj.projSpreadHome != null) {
      (row as EdgeBoardRow & { kei?: string }).kei = formatSpread(
        proj.projSpreadHome,
      );
    } else if (row.market === "Total" && proj.projTotal != null) {
      (row as EdgeBoardRow & { kei?: string }).kei = String(
        Math.round(proj.projTotal * 10) / 10,
      );
    }
  }

  return rows;
}
