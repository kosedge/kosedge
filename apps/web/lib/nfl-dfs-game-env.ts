/**
 * DFS game-environment join — same FG pregame identity rules as Edge Board.
 * F5 / live / missing period / wrong event fail closed.
 */

import {
  isFeaturedFullGameOddsKey,
  isFirstFiveInningsOddsKey,
  isFullGameLivePeriod,
  isFullGamePregamePeriod,
  isOddsInPlayEvent,
} from "@/lib/edge-board-market-identity";
import { canonicalTeamCode } from "@/lib/nfl-dfs-identity";

export type DfsGameEnv = {
  available: boolean;
  reason: string;
  total: number | null;
  spread: number | null;
  impliedTeamTotal: number | null;
  book: string | null;
  period: string | null;
};

export type DfsGameMarketQuote = {
  event?: string | null;
  sport?: string | null;
  market: string;
  period?: string | null;
  line?: number | null;
  book?: string | null;
  timestamp?: string | null;
  homeTeam?: string | null;
  awayTeam?: string | null;
  season?: number | null;
  week?: number | null;
  commenceTime?: string | null;
  linesAsOf?: string | null;
};

export function certifyDfsGameQuote(
  quote: DfsGameMarketQuote,
  input: { season: number; week: number; team: string; opponent: string },
): DfsGameEnv {
  const unavailable = (reason: string): DfsGameEnv => ({
    available: false,
    reason,
    total: null,
    spread: null,
    impliedTeamTotal: null,
    book: null,
    period: null,
  });

  if (quote.season != null && quote.season !== input.season) {
    return unavailable("season_mismatch");
  }
  if (quote.week != null && quote.week !== input.week) {
    return unavailable("week_mismatch");
  }
  if (!quote.period) return unavailable("missing_period_identity");
  if (
    isFullGameLivePeriod(quote.period) ||
    isOddsInPlayEvent({
      commenceTime: quote.commenceTime,
      linesAsOf: quote.linesAsOf ?? quote.timestamp,
    })
  ) {
    return unavailable("in_play");
  }
  if (isFirstFiveInningsOddsKey(quote.market) || !isFullGamePregamePeriod(quote.period)) {
    return unavailable("period_not_fg");
  }
  if (!isFeaturedFullGameOddsKey(quote.market)) {
    return unavailable("market_not_featured_fg");
  }

  const team = canonicalTeamCode(input.team);
  const opp = canonicalTeamCode(input.opponent);
  const home = canonicalTeamCode(quote.homeTeam);
  const away = canonicalTeamCode(quote.awayTeam);
  if (!team || !opp || !home || !away) return unavailable("missing_event_teams");
  const participants = new Set([home, away]);
  if (!participants.has(team) || !participants.has(opp)) {
    return unavailable("event_mismatch");
  }

  return {
    available: true,
    reason: "ok",
    total: quote.market === "totals" ? (quote.line ?? null) : null,
    spread: quote.market === "spreads" ? (quote.line ?? null) : null,
    impliedTeamTotal: null,
    book: quote.book ?? null,
    period: quote.period,
  };
}

export function impliedTeamTotal(
  gameTotal: number | null,
  teamSpread: number | null,
): number | null {
  if (gameTotal == null || teamSpread == null) return null;
  if (!(gameTotal > 0) || !Number.isFinite(teamSpread)) return null;
  return Math.round((gameTotal / 2 - teamSpread / 2) * 1000) / 1000;
}
