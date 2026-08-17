/**
 * In-house KosEdge official CFB slate (W0/W1).
 * Desk SoT is this artifact — not a live iframe and not a Railway override.
 * Primary: ESPN team schedule. Fact-check: The Odds API NCAAF events.
 */

import slate from "@/lib/data/cfb-official-slate-2026.json";

export type CfbWeekBoardGame = {
  week: number;
  game_id?: string;
  home: string;
  away: string;
  home_name?: string;
  away_name?: string;
  kickoff?: string;
  neutral_site?: boolean;
  venue?: string;
  network?: string;
  conference?: string;
  fcs_home?: boolean;
  fcs_away?: boolean;
  fbs_vs_fbs?: boolean;
  conference_game?: boolean;
  status?: string;
  factcheck?: string;
};

export type CfbWeekBoard = {
  season?: number;
  weeks?: number[];
  n_games?: number;
  n_fbs_vs_fbs?: number;
  n_w0?: number;
  n_w1?: number;
  slate_complete?: boolean;
  official?: boolean;
  source?: string;
  primary_source?: string;
  factcheck_source?: string;
  slate_version?: string;
  used_in_spread?: boolean;
  kei?: boolean;
  as_of?: string;
  primary_as_of?: string;
  games?: CfbWeekBoardGame[];
  factcheck?: {
    agreed?: number;
    conflicts?: unknown[];
    only_primary?: string[];
    only_secondary?: string[];
    secondary_events?: number;
    error?: string | null;
  };
};

function asGame(row: unknown): CfbWeekBoardGame | null {
  if (!row || typeof row !== "object") return null;
  const r = row as Record<string, unknown>;
  const home = typeof r.home === "string" ? r.home : "";
  const away = typeof r.away === "string" ? r.away : "";
  const week = typeof r.week === "number" ? r.week : Number(r.week);
  if (!home || !away || !Number.isFinite(week)) return null;
  return {
    week,
    game_id: typeof r.game_id === "string" ? r.game_id : undefined,
    home,
    away,
    home_name: typeof r.home_name === "string" ? r.home_name : undefined,
    away_name: typeof r.away_name === "string" ? r.away_name : undefined,
    kickoff: typeof r.kickoff === "string" ? r.kickoff : undefined,
    neutral_site: Boolean(r.neutral_site),
    venue: typeof r.venue === "string" ? r.venue : undefined,
    network: typeof r.network === "string" ? r.network : undefined,
    conference: typeof r.conference === "string" ? r.conference : undefined,
    fcs_home: Boolean(r.fcs_home),
    fcs_away: Boolean(r.fcs_away),
    fbs_vs_fbs:
      typeof r.fbs_vs_fbs === "boolean"
        ? r.fbs_vs_fbs
        : !r.fcs_home && !r.fcs_away,
    conference_game: Boolean(r.conference_game),
    status: typeof r.status === "string" ? r.status : undefined,
    factcheck: typeof r.factcheck === "string" ? r.factcheck : undefined,
  };
}

export function packagedOfficialWeekBoard(): CfbWeekBoard {
  const games = (slate.games ?? [])
    .map(asGame)
    .filter((g): g is CfbWeekBoardGame => g != null);
  return {
    season: slate.season,
    weeks: slate.weeks,
    n_games: games.length,
    n_fbs_vs_fbs: games.filter((g) => g.fbs_vs_fbs).length,
    n_w0: games.filter((g) => g.week === 0).length,
    n_w1: games.filter((g) => g.week === 1).length,
    slate_complete: Boolean(slate.slate_complete),
    official: Boolean(slate.official),
    source: slate.source,
    primary_source: slate.primary_source,
    factcheck_source: slate.factcheck_source,
    slate_version: slate.slate_version,
    used_in_spread: false,
    kei: false,
    as_of: typeof slate.as_of === "string" ? slate.as_of : undefined,
    primary_as_of:
      typeof slate.primary_as_of === "string" ? slate.primary_as_of : undefined,
    games,
    factcheck: slate.factcheck,
  };
}

/** Desk SoT is the KosEdge artifact. Remote Railway boards do not replace it. */
export function resolveWeekBoard(_remote?: CfbWeekBoard | null): CfbWeekBoard {
  return packagedOfficialWeekBoard();
}

export function gamesForWeek(
  board: CfbWeekBoard,
  week: number,
): CfbWeekBoardGame[] {
  return (board.games ?? []).filter((g) => g.week === week);
}

export function officialSlateWeeks(): number[] {
  const weeks = packagedOfficialWeekBoard().weeks ?? [0, 1];
  return weeks.length ? weeks : [0, 1];
}

export function parseOfficialSlateWeek(raw?: string): number {
  const n = Number(raw ?? 0);
  const weeks = officialSlateWeeks();
  return weeks.includes(n) ? n : (weeks[0] ?? 0);
}

export function projectGameHref(row: CfbWeekBoardGame): string {
  const q = new URLSearchParams({
    home: row.home.replace(/^fcs:/i, ""),
    away: row.away.replace(/^fcs:/i, ""),
    week: String(row.week),
  });
  if (row.neutral_site) q.set("neutral", "1");
  return `/pro/cfb/project-game?${q.toString()}`;
}

export function kickoffEtLabel(raw?: string): string {
  if (!raw) return "—";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
  });
}

export function matchupLabel(row: CfbWeekBoardGame): string {
  const away = row.away_name || row.away;
  const home = row.home_name || row.home;
  return `${away} @ ${home}`;
}

export function officialSlateAttribution(board: CfbWeekBoard = packagedOfficialWeekBoard()): string {
  const fact = board.factcheck_source === "the_odds_api_ncaaf_events"
    ? "The Odds API"
    : board.factcheck_source || "second source";
  return `Official slate · KosEdge · sourced from ESPN, fact-checked vs ${fact} · as_of ${board.as_of ?? "—"}`;
}
