/**
 * Merge KEI (projected) lines into Edge Board rows by matching game and commence time.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";

function matchGame(row: EdgeBoardRow, kei: KeiLineGame): boolean {
  if (!row.game || !row.commenceTime || !kei.commenceTime) return false;
  const rowGame = row.game.toLowerCase();
  const away = kei.awayTeam.toLowerCase();
  const home = kei.homeTeam.toLowerCase();
  return (
    (rowGame.includes(away) && rowGame.includes(home)) ||
    row.commenceTime === kei.commenceTime ||
    Math.abs(new Date(row.commenceTime).getTime() - new Date(kei.commenceTime).getTime()) < 60_000
  );
}

/** Find KEI game for an edge board row (by game string and commence time). */
function findKeiForRow(rows: EdgeBoardRow[], keiGames: KeiLineGame[], row: EdgeBoardRow): KeiLineGame | undefined {
  return keiGames.find((k) => matchGame(row, k));
}

/**
 * Merge KEI projected spread/total into edge board rows. Mutates and returns the same array.
 */
export function mergeKeiIntoEdgeBoardRows(rows: EdgeBoardRow[], sportKey: string): EdgeBoardRow[] {
  const keiGames = getKeiLines(sportKey);
  if (keiGames.length === 0) return rows;

  for (const row of rows) {
    const kei = findKeiForRow(rows, keiGames, row);
    if (!kei) continue;

    if (row.market === "Spread" && kei.projSpreadHome != null) {
      row.kei = kei.projSpreadHome > 0 ? `+${kei.projSpreadHome.toFixed(1)}` : kei.projSpreadHome.toFixed(1);
    } else if (row.market === "Total" && kei.projTotal != null) {
      row.kei = kei.projTotal.toFixed(1);
    }
  }

  return rows;
}
