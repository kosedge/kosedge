/**
 * Packaged official 2026 ESPN W0/W1 slate — research desk fallback.
 * used_in_spread stays false. No KEI. Lives in-repo so /pro/cfb/slate
 * still renders games when Railway status 500s.
 */

import slate from "@/lib/data/cfb-official-slate-w0-w1-2026.json";

export type CfbWeekBoardGame = {
  week: number;
  game_id?: string;
  home: string;
  away: string;
  kickoff?: string;
  neutral_site?: boolean;
  fcs_home?: boolean;
  fcs_away?: boolean;
  fbs_vs_fbs?: boolean;
  conference_game?: boolean;
};

export type CfbWeekBoard = {
  season?: number;
  weeks?: number[];
  n_games?: number;
  n_fbs_vs_fbs?: number;
  slate_complete?: boolean;
  official?: boolean;
  source?: string;
  used_in_spread?: boolean;
  kei?: boolean;
  as_of?: string;
  games?: CfbWeekBoardGame[];
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
    kickoff: typeof r.kickoff === "string" ? r.kickoff : undefined,
    neutral_site: Boolean(r.neutral_site),
    fcs_home: Boolean(r.fcs_home),
    fcs_away: Boolean(r.fcs_away),
    fbs_vs_fbs:
      typeof r.fbs_vs_fbs === "boolean"
        ? r.fbs_vs_fbs
        : !r.fcs_home && !r.fcs_away,
    conference_game: Boolean(r.conference_game),
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
    slate_complete: Boolean(slate.slate_complete),
    official: Boolean(slate.official),
    source: slate.source,
    used_in_spread: false,
    kei: false,
    as_of: typeof slate.as_of === "string" ? slate.as_of : undefined,
    games,
  };
}

export function resolveWeekBoard(remote?: CfbWeekBoard | null): CfbWeekBoard {
  const remoteGames = remote?.games ?? [];
  if (remoteGames.length > 0) return { ...remote, used_in_spread: false };
  return packagedOfficialWeekBoard();
}

export function gamesForWeek(board: CfbWeekBoard, week: number): CfbWeekBoardGame[] {
  return (board.games ?? []).filter((g) => g.week === week);
}
