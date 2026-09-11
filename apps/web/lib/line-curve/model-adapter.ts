/**
 * Bind KosEdge model / KEI outputs onto Line Curve ModelMarginInput.
 * Fail closed when the run cannot be tied to the exact event.
 */

import {
  findCfbKeiGame,
  loadCfbKeiPack,
  type CfbKeiGame,
} from "@/lib/cfb-kei-artifacts";
import type { CfbProjectGameResponse } from "@/lib/cfb-season-engine";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines-view-types";
import { closed } from "@/lib/line-curve/guardrails";
import { normalizeName } from "@/lib/line-curve/margin-pmf";
import type { LineCurveClosed, ModelMarginInput } from "@/lib/line-curve/types";

function keiSigma(game: CfbKeiGame): number | null {
  const raw = game.kei?.model_sigma;
  return typeof raw === "number" && Number.isFinite(raw) && raw > 0
    ? raw
    : null;
}

function scoresFromSpreadTotal(
  spreadHome: number,
  total: number,
): { home: number; away: number } | null {
  if (!Number.isFinite(spreadHome) || !Number.isFinite(total) || total <= 0) {
    return null;
  }
  // CFB engine: spread_home = away_exp − home_exp; total = home + away.
  const home = (total - spreadHome) / 2;
  const away = (total + spreadHome) / 2;
  if (home <= 0 || away <= 0) return null;
  return { home, away };
}

export function modelFromCfbKeiGame(args: {
  game: CfbKeiGame;
  eventId: string;
  homeTeam: string;
  awayTeam: string;
}): ModelMarginInput | LineCurveClosed {
  const pack = loadCfbKeiPack();
  const spread =
    args.game.model_spread_home ?? args.game.kei?.model_spread_home;
  const total = args.game.model_total ?? args.game.kei?.kei_total;
  const sigma = keiSigma(args.game);
  const gameId = args.game.game_id;
  const engine = pack.engine_version;
  const keiVersion = pack.kei_version ?? args.game.kei?.kei_version;
  if (
    spread == null ||
    total == null ||
    sigma == null ||
    !gameId ||
    !engine ||
    !keiVersion
  ) {
    return closed(
      "missing_model_run",
      "CFB KEI row is missing spread/total/sigma/version — refuse to price.",
    );
  }
  const scores = scoresFromSpreadTotal(spread, total);
  if (!scores) {
    return closed("missing_model_run", "CFB KEI scores cannot be derived.");
  }
  return {
    eventId: args.eventId,
    modelRunId: `${engine}:${keiVersion}:${gameId}`,
    sport: "cfb",
    homeTeam: args.homeTeam,
    awayTeam: args.awayTeam,
    modelSpreadHome: spread,
    expectedHomeScore: scores.home,
    expectedAwayScore: scores.away,
    marginSd: sigma,
  };
}

export function bindCfbKeiByTeams(args: {
  eventId: string;
  homeTeam: string;
  awayTeam: string;
  homeCode?: string;
  awayCode?: string;
  week?: number;
}): ModelMarginInput | LineCurveClosed {
  const game =
    (args.homeCode && args.awayCode
      ? findCfbKeiGame(args.homeCode, args.awayCode, args.week)
      : undefined) ??
    loadCfbKeiPack().games?.find((g) => {
      if (args.week != null && g.week !== args.week) return false;
      const homeHit =
        normalizeName(g.home_name ?? "") === normalizeName(args.homeTeam) ||
        normalizeName(g.home ?? "") === normalizeName(args.homeCode ?? "");
      const awayHit =
        normalizeName(g.away_name ?? "") === normalizeName(args.awayTeam) ||
        normalizeName(g.away ?? "") === normalizeName(args.awayCode ?? "");
      return homeHit && awayHit;
    });
  if (!game) {
    return closed(
      "unbound_model_event",
      "No CFB KEI game matches this event — refuse to recycle another week.",
    );
  }
  return modelFromCfbKeiGame({
    game,
    eventId: args.eventId,
    homeTeam: args.homeTeam,
    awayTeam: args.awayTeam,
  });
}

export function modelFromCfbProjectGame(args: {
  eventId: string;
  projected: CfbProjectGameResponse;
  homeTeam: string;
  awayTeam: string;
}): ModelMarginInput | LineCurveClosed {
  const run =
    args.projected.engine_version && args.projected.game_id
      ? `${args.projected.engine_version}:${args.projected.game_id}`
      : args.projected.engine_version;
  if (!run) {
    return closed(
      "missing_model_run",
      "project-game response has no engine version.",
    );
  }
  const spread = args.projected.spread_home;
  const home = args.projected.expected_home_score;
  const away = args.projected.expected_away_score;
  const sd = args.projected.margin_sd;
  if (
    spread == null ||
    home == null ||
    away == null ||
    sd == null ||
    !Number.isFinite(spread) ||
    !Number.isFinite(home) ||
    !Number.isFinite(away) ||
    !Number.isFinite(sd)
  ) {
    return closed(
      "missing_model_run",
      "project-game is missing spread / scores / margin_sd.",
    );
  }
  return {
    eventId: args.eventId,
    modelRunId: run,
    sport: "cfb",
    homeTeam: args.homeTeam,
    awayTeam: args.awayTeam,
    modelSpreadHome: spread,
    expectedHomeScore: home,
    expectedAwayScore: away,
    marginSd: sd,
  };
}

export function modelFromNflFairLine(args: {
  eventId: string;
  row: NflFairLineRow;
  homeTeam: string;
  awayTeam: string;
  modelVersion?: string | null;
  activeRunId?: string | null;
}): ModelMarginInput | LineCurveClosed {
  const gameId = args.row.gameId;
  const version = args.modelVersion;
  if (!gameId || !version) {
    return closed(
      "missing_model_run",
      "NFL fair-lines row is missing gameId / modelVersion.",
    );
  }
  const spread =
    args.row.modelSpreadHome ??
    args.row.spreadHome ??
    args.row.handicapSpreadHome;
  const total =
    args.row.totalMean ?? args.row.modelTotal ?? args.row.handicapTotal;
  if (spread == null || total == null) {
    return closed(
      "missing_model_run",
      "NFL fair-lines row is missing model spread / total.",
    );
  }
  const scores = scoresFromSpreadTotal(spread, total);
  if (!scores) {
    return closed(
      "missing_model_run",
      "NFL expected scores cannot be derived.",
    );
  }
  const runId = args.activeRunId
    ? `${version}:${args.activeRunId}:${gameId}`
    : `${version}:${gameId}`;
  return {
    eventId: args.eventId,
    modelRunId: runId,
    sport: "nfl",
    homeTeam: args.homeTeam,
    awayTeam: args.awayTeam,
    modelSpreadHome: spread,
    expectedHomeScore: scores.home,
    expectedAwayScore: scores.away,
    marginSd: 13.5,
  };
}
