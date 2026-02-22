/**
 * Merge KEI lines (our projected spread and O/U) into edge board rows.
 * Used by /api/edge-board/[sport]/today to populate "our numbers" on the board.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { getKeiLines } from "@/lib/kei-lines";

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

function formatSpread(projSpreadHome: number): string {
  const n = Math.round(projSpreadHome * 10) / 10;
  if (n >= 0) return `+${n}`;
  return String(n);
}

/**
 * Merges KEI projections into edge board rows. Mutates rows in place and returns them.
 * Each row with market "Spread" gets row.kei = our projected home spread (e.g. "-5.2").
 * Each row with market "Total" gets row.kei = our projected total (e.g. "148.5").
 */
export function mergeKeiIntoEdgeBoardRows(
  rows: EdgeBoardRow[],
  sportKey: string,
): EdgeBoardRow[] {
  const games = getKeiLines(sportKey);
  if (!games.length) return rows;

  const byGame = new Map<
    string,
    { projSpreadHome: number | null; projTotal: number | null }
  >();
  for (const g of games) {
    const gameStr = `${g.awayTeam} @ ${g.homeTeam}`;
    for (const key of gameKeys(gameStr)) {
      byGame.set(key, {
        projSpreadHome: g.projSpreadHome ?? null,
        projTotal: g.projTotal ?? null,
      });
    }
  }

  for (const row of rows) {
    const game = row?.game;
    if (!game) continue;
    const keys = gameKeys(game);
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
