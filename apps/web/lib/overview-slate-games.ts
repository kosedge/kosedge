/**
 * Overview-only soft fetch for Edge Board slate cards.
 * Soft timeout / empty fallback — does not change assemble or model logic.
 */

import { getTonightGames, type TonightGame } from "@/lib/edge-board-tonight";

const OVERVIEW_SLATE_TIMEOUT_MS = 8_000;

export async function loadOverviewSlateGames(
  sportKey: string,
): Promise<TonightGame[]> {
  try {
    const games = await Promise.race([
      getTonightGames(sportKey),
      new Promise<TonightGame[]>((resolve) =>
        setTimeout(() => resolve([]), OVERVIEW_SLATE_TIMEOUT_MS),
      ),
    ]);
    return Array.isArray(games) ? games : [];
  } catch {
    return [];
  }
}
