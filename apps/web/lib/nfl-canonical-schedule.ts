/**
 * Canonical 2026 NFL REG schedule — display SoT for kickoff, venue, week, teams.
 * Odds / fair-lines commence may differ; this pack wins for product clocks.
 */

import pack from "@/lib/nfl-canonical-schedule-2026.json";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";

export const NFL_CANONICAL_SCHEDULE_SEASON = 2026;
export const NFL_REG_GAME_COUNT = 272;
export const NFL_TEAM_COUNT = 32;

export type CanonicalNflGame = {
  game_id: string;
  engine_game_id: string;
  season: number;
  week: number;
  game_type: "PRE" | "REG" | "POST";
  away_team_id: string;
  home_team_id: string;
  venue: string | null;
  location: string | null;
  international: boolean;
  kickoff_utc: string | null;
  network: string | null;
  status: string;
};

type Pack = {
  season: number;
  game_count: number;
  games: CanonicalNflGame[];
};

const PACK = pack as Pack;
const GAMES = PACK.games;

const BY_PRODUCT_ID = new Map<string, CanonicalNflGame>();
const BY_ENGINE_ID = new Map<string, CanonicalNflGame>();
const BY_WEEK_PAIR = new Map<string, CanonicalNflGame>();
const BY_WEEK_TEAM = new Map<string, CanonicalNflGame>();

function pairKey(week: number, away: string, home: string): string {
  return `${week}|${away}|${home}`;
}

const BY_PAIR = new Map<string, CanonicalNflGame[]>();

function pairTeams(away: string, home: string): string {
  return `${away}|${home}`;
}

for (const game of GAMES) {
  BY_PRODUCT_ID.set(game.game_id, game);
  BY_ENGINE_ID.set(game.engine_game_id, game);
  BY_WEEK_PAIR.set(
    pairKey(game.week, game.away_team_id, game.home_team_id),
    game,
  );
  BY_WEEK_TEAM.set(`${game.week}|${game.away_team_id}`, game);
  BY_WEEK_TEAM.set(`${game.week}|${game.home_team_id}`, game);
  const pk = pairTeams(game.away_team_id, game.home_team_id);
  const list = BY_PAIR.get(pk) ?? [];
  list.push(game);
  BY_PAIR.set(pk, list);
}

export const NFL_WEEK1_KICKOFF_ANCHORS = [
  {
    game_id: "2026-W01-NE@SEA",
    kickoff_et: "8:20 PM ET",
    kickoff_utc: "2026-09-10T00:20:00.000Z",
    venue: "Lumen Field",
  },
  {
    game_id: "2026-W01-SF@LAR",
    kickoff_et: "8:35 PM ET",
    kickoff_utc: "2026-09-11T00:35:00.000Z",
    venue: "Melbourne Cricket Ground",
  },
] as const;

export function listCanonicalNflGames(): CanonicalNflGame[] {
  return GAMES;
}

export function lookupCanonicalNflGame(args: {
  gameId?: string | null;
  season?: number | null;
  week?: number | null;
  awayAbbr?: string | null;
  homeAbbr?: string | null;
}): CanonicalNflGame | null {
  const id = String(args.gameId ?? "").trim();
  if (id) {
    const hit = BY_PRODUCT_ID.get(id) ?? BY_ENGINE_ID.get(id);
    if (hit) return hit;
  }
  const week = args.week == null ? NaN : Number(args.week);
  const away = canonicalizeNflTeam(args.awayAbbr);
  const home = canonicalizeNflTeam(args.homeAbbr);
  if (!away || !home) return null;
  if (args.season != null && Number(args.season) !== PACK.season) return null;
  if (Number.isFinite(week)) {
    return (
      BY_WEEK_PAIR.get(pairKey(Math.trunc(week), away, home)) ??
      BY_WEEK_PAIR.get(pairKey(Math.trunc(week), home, away)) ??
      null
    );
  }
  const directed = BY_PAIR.get(pairTeams(away, home)) ?? [];
  if (directed.length === 1) return directed[0];
  return null;
}

export function lookupCanonicalNflGameForTeam(args: {
  week: number;
  teamAbbr: string;
}): CanonicalNflGame | null {
  const team = canonicalizeNflTeam(args.teamAbbr);
  if (!team) return null;
  return BY_WEEK_TEAM.get(`${args.week}|${team}`) ?? null;
}

/**
 * Canonical kickoff for a REG matchup.
 * found=false → no pack row (PRE / unknown); caller may use odds.
 * found=true + kickoffUtc=null → official time TBD; do not invent 4pm from odds.
 */
export function canonicalKickoffForMatchup(args: {
  gameId?: string | null;
  season?: number | null;
  week?: number | null;
  awayAbbr?: string | null;
  homeAbbr?: string | null;
}): { found: boolean; kickoffUtc: string | null; game: CanonicalNflGame | null } {
  const game = lookupCanonicalNflGame(args);
  if (!game) return { found: false, kickoffUtc: null, game: null };
  return { found: true, kickoffUtc: game.kickoff_utc, game };
}

export function formatKickoffEt(iso: string | null | undefined): string {
  if (!iso) return "TBD";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "TBD";
  const clock = d.toLocaleTimeString("en-US", {
    timeZone: "America/New_York",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${clock} ET`;
}

export function week1AuditRows(): Array<{
  game_id: string;
  kosedge_kickoff_et: string;
  official_kickoff_et: string;
  match: "Y" | "N";
}> {
  return GAMES.filter((g) => g.week === 1).map((g) => {
    const kosedge = formatKickoffEt(g.kickoff_utc);
    const anchor = NFL_WEEK1_KICKOFF_ANCHORS.find(
      (a) => a.game_id === g.game_id,
    );
    const official = anchor?.kickoff_et ?? kosedge;
    return {
      game_id: g.game_id,
      kosedge_kickoff_et: kosedge,
      official_kickoff_et: official,
      match: kosedge === official ? "Y" : "N",
    };
  });
}
