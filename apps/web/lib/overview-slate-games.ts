/**
 * Overview-only soft fetch for Edge Board slate cards.
 * Soft timeout / honest status — does not change assemble or model logic.
 *
 * At 8s without a response we stop blocking SSR and return `timeout`
 * (empty games + distinct copy), not a silent "no slate" empty state.
 */

import { getTonightGames, type TonightGame } from "@/lib/edge-board-tonight";

const OVERVIEW_SLATE_TIMEOUT_MS = 8_000;

export type OverviewSlateStatus = "ready" | "empty" | "timeout" | "error";

export type OverviewSlateResult = {
  games: TonightGame[];
  status: OverviewSlateStatus;
};

export async function loadOverviewSlateGames(
  sportKey: string,
): Promise<OverviewSlateResult> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  try {
    const result = await Promise.race([
      getTonightGames(sportKey).then((games) => ({
        kind: "ok" as const,
        games: Array.isArray(games) ? games : [],
      })),
      new Promise<{ kind: "timeout" }>((resolve) => {
        timeoutId = setTimeout(
          () => resolve({ kind: "timeout" }),
          OVERVIEW_SLATE_TIMEOUT_MS,
        );
      }),
    ]);

    if (timeoutId) clearTimeout(timeoutId);

    if (result.kind === "timeout") {
      return { games: [], status: "timeout" };
    }

    return {
      games: result.games,
      status: result.games.length > 0 ? "ready" : "empty",
    };
  } catch {
    if (timeoutId) clearTimeout(timeoutId);
    return { games: [], status: "error" };
  }
}
