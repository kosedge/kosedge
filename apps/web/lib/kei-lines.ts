/**
 * KEI Lines: projected spread and over/under per game.
 * Data is read from data/processed/kei_lines_{sport}.json (exported by pipeline script).
 *
 * Architecture:
 *   model_*     = pure sim / research fair
 *   handicap_*  = KEI product line (what edgeboard shows)
 *   proj* / row.kei = handicap (migration alias)
 *   If handicap missing → handicap = model (identity)
 */

import { existsSync, readFileSync } from "node:fs";
import { loadCfbKeiPack } from "@/lib/cfb-kei-artifacts";
import { getSport } from "@/lib/sports";
import { getKeiLinesPath } from "@/lib/data-paths";

export type KeiLineGame = {
  id?: string;
  homeTeam: string;
  awayTeam: string;
  homeAbbr?: string | null;
  awayAbbr?: string | null;
  commenceTime?: string;
  week?: number | null;
  /** @deprecated Use handicapSpreadHome — migration alias of KEI handicap. */
  projSpreadHome: number | null;
  /** @deprecated Use handicapTotal — migration alias of KEI handicap. */
  projTotal: number | null;
  /** Fair home moneyline (American). Handicap alias. Used by MLB edge board. */
  projHomeMl?: number | null;
  /** Fair away moneyline (American). Handicap alias. Used by MLB edge board. */
  projAwayMl?: number | null;
  /** Handicap home win probability (0–1). Used for MLB ML edge in prob points. */
  homeWinProb?: number | null;

  // --- Handicap = KEI product line (edgeboard) ---
  handicapSpreadHome?: number | null;
  handicapTotal?: number | null;
  handicapHomeMl?: number | null;
  handicapAwayMl?: number | null;
  handicapHomeWinProb?: number | null;

  // --- Model = pure sim / research (Fair Lines desk; not used for PLAY/LEAN) ---
  modelSpreadHome?: number | null;
  modelTotal?: number | null;
  modelHomeMl?: number | null;
  modelAwayMl?: number | null;
  modelHomeWinProb?: number | null;
};

/**
 * Resolve handicap fields with identity fallback to model / legacy proj*.
 * Edgeboard and tags always consume these values.
 */
export function resolveHandicapFields(game: KeiLineGame): {
  spreadHome: number | null;
  total: number | null;
  homeMl: number | null;
  awayMl: number | null;
  homeWinProb: number | null;
} {
  const spreadHome =
    game.handicapSpreadHome ??
    game.projSpreadHome ??
    game.modelSpreadHome ??
    null;
  const total =
    game.handicapTotal ?? game.projTotal ?? game.modelTotal ?? null;
  const homeMl =
    game.handicapHomeMl ?? game.projHomeMl ?? game.modelHomeMl ?? null;
  const awayMl =
    game.handicapAwayMl ?? game.projAwayMl ?? game.modelAwayMl ?? null;
  const homeWinProb =
    game.handicapHomeWinProb ??
    game.homeWinProb ??
    game.modelHomeWinProb ??
    null;
  return { spreadHome, total, homeMl, awayMl, homeWinProb };
}

/**
 * Apply identity: when handicap missing, copy model into handicap + proj aliases.
 * Mutates and returns the same game for chaining.
 */
export function applyHandicapIdentity(game: KeiLineGame): KeiLineGame {
  const handicapSpread =
    game.handicapSpreadHome ?? game.projSpreadHome ?? game.modelSpreadHome ?? null;
  const handicapTotal =
    game.handicapTotal ?? game.projTotal ?? game.modelTotal ?? null;
  const handicapHomeMl =
    game.handicapHomeMl ?? game.projHomeMl ?? game.modelHomeMl ?? null;
  const handicapAwayMl =
    game.handicapAwayMl ?? game.projAwayMl ?? game.modelAwayMl ?? null;
  const handicapWin =
    game.handicapHomeWinProb ??
    game.homeWinProb ??
    game.modelHomeWinProb ??
    null;

  game.handicapSpreadHome = handicapSpread;
  game.handicapTotal = handicapTotal;
  game.handicapHomeMl = handicapHomeMl;
  game.handicapAwayMl = handicapAwayMl;
  game.handicapHomeWinProb = handicapWin;

  // Migration aliases: proj* / homeWinProb = handicap
  game.projSpreadHome = handicapSpread;
  game.projTotal = handicapTotal;
  game.projHomeMl = handicapHomeMl;
  game.projAwayMl = handicapAwayMl;
  game.homeWinProb = handicapWin;

  // Model identity when absent
  if (game.modelSpreadHome == null) game.modelSpreadHome = handicapSpread;
  if (game.modelTotal == null) game.modelTotal = handicapTotal;
  if (game.modelHomeMl == null) game.modelHomeMl = handicapHomeMl;
  if (game.modelAwayMl == null) game.modelAwayMl = handicapAwayMl;
  if (game.modelHomeWinProb == null) game.modelHomeWinProb = handicapWin;

  return game;
}

function cfbKeiLinesFromBundledPack(): KeiLineGame[] {
  return (loadCfbKeiPack().games ?? [])
    .filter((g) => g.kei?.kei_spread_home != null)
    .map((g) =>
      applyHandicapIdentity({
        id: String(g.game_id || `${g.away}-${g.home}`),
        homeTeam: String(g.home_name || g.home || ""),
        awayTeam: String(g.away_name || g.away || ""),
        homeAbbr: g.home,
        awayAbbr: g.away,
        commenceTime: g.kickoff,
        week: g.week,
        handicapSpreadHome: g.kei?.kei_spread_home ?? null,
        handicapTotal: g.kei?.kei_total ?? g.model_total ?? null,
        handicapHomeWinProb: g.kei?.kei_home_win_prob ?? null,
        projSpreadHome: g.kei?.kei_spread_home ?? null,
        projTotal: g.kei?.kei_total ?? g.model_total ?? null,
        homeWinProb: g.kei?.kei_home_win_prob ?? null,
        modelSpreadHome: g.model_spread_home ?? g.kei?.model_spread_home ?? null,
        modelTotal: g.model_total ?? null,
        modelHomeWinProb: g.model_home_win_prob ?? null,
      }),
    );
}

export function getKeiLines(sportKey: string): KeiLineGame[] {
  if (!getSport(sportKey)) return [];

  // Bundled import — Vercel NFT excludes apps/web/data/processed/kei_lines_*.json.
  if (sportKey.toLowerCase() === "cfb") {
    return cfbKeiLinesFromBundledPack();
  }

  const p = getKeiLinesPath(sportKey);
  if (!existsSync(p)) return [];

  try {
    const raw = readFileSync(p, "utf-8");
    const data = JSON.parse(raw) as { games?: KeiLineGame[] };
    const games = Array.isArray(data.games) ? data.games : [];
    return games.map((g) => applyHandicapIdentity({ ...g }));
  } catch {
    return [];
  }
}
