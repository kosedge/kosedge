/**
 * Shared Overview Edge Board slate — continuation of the Overview hero surface.
 * One CTA only: Full Edge Board. Sport-specific matchup cards via WeeklyGamesScroller.
 * Card chrome lives on OverviewSportShell (header + slate = one visual unit).
 */

import Link from "next/link";
import type { TonightGame } from "@/lib/edge-board-tonight";
import type { OverviewSlateStatus } from "@/lib/overview-slate-games";
import WeeklyGamesScroller from "@/components/pro/WeeklyGamesScroller";

const SLATE_META: Record<string, { title: string; emptyHint: string }> = {
  nfl: {
    title: "This Week’s Slate",
    emptyHint:
      "No live REG matchup cards on the board yet. Open Edge Board when markets post.",
  },
  nba: {
    title: "Today’s Slate",
    emptyHint:
      "No NBA game board posted right now. Shell stays ready — we do not invent matchups.",
  },
  mlb: {
    title: "Today’s Slate",
    emptyHint:
      "No MLB slate rows yet. Edge Board refreshes when books and starters post.",
  },
};

const STATUS_HINT: Partial<Record<OverviewSlateStatus, string>> = {
  timeout:
    "Board data is taking longer than usual. Open Full Edge Board for the live board — this slate refreshes on the next page load.",
  error:
    "Couldn’t load slate cards just now. Open Full Edge Board for the live board.",
};

function subtleStatusLine(
  status: OverviewSlateStatus,
  gameCount: number,
): string | null {
  if (status === "timeout" || status === "error") return null;
  if (status === "empty" || gameCount === 0) return null;
  if (gameCount === 1) return "1 matchup on the board";
  return `${gameCount} matchups on the board`;
}

export default function OverviewEdgeBoardSlate({
  sport,
  games,
  status = "ready",
}: {
  sport: string;
  games: TonightGame[];
  status?: OverviewSlateStatus;
}) {
  const meta = SLATE_META[sport] ?? {
    title: "Today’s Slate",
    emptyHint: "Slate cards appear when live board data is available.",
  };
  const edgeBoardHref = `/edge-board/${sport}`;
  const emptyCopy =
    status === "timeout" || status === "error"
      ? (STATUS_HINT[status] ?? meta.emptyHint)
      : meta.emptyHint;
  const statusLine = subtleStatusLine(status, games.length);

  return (
    <div className="relative mt-6 border-t border-white/10 pt-5 sm:mt-7 sm:pt-6">
      <div className="flex flex-wrap items-end justify-between gap-3 sm:gap-4">
        <div className="min-w-0 max-w-2xl">
          <h2 className="text-lg font-semibold tracking-tight text-kos-text sm:text-xl">
            {meta.title}
          </h2>
          {statusLine ? (
            <p className="mt-1 text-xs text-kos-text/50">{statusLine}</p>
          ) : null}
        </div>
        <Link
          href={edgeBoardHref}
          className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55 hover:bg-kos-gold/25"
        >
          Full Edge Board →
        </Link>
      </div>

      <div className="mt-4">
        <WeeklyGamesScroller
          games={games}
          sport={sport}
          embedded
          emptyCopy={emptyCopy}
        />
      </div>
    </div>
  );
}
