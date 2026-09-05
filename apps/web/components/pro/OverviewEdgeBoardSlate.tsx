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
      "No NFL REG week on the board yet — schedule not released or not pulled. Shell stays ready; we do not invent matchups.",
  },
  cfb: {
    title: "This Week’s Slate",
    emptyHint:
      "No CFB week on the board yet — schedule not released or not pulled. Open Edge Board when Week 1 posts.",
  },
  nba: {
    title: "Today’s Slate",
    emptyHint:
      "No NBA games scheduled on the board yet. When opening night posts, the first slate appears here — we do not invent matchups.",
  },
  mlb: {
    title: "Today’s Slate",
    emptyHint:
      "No MLB slate rows yet. When the next day posts, cards appear here — we do not invent matchups.",
  },
  nhl: {
    title: "Today’s Slate",
    emptyHint:
      "No NHL games scheduled on the board yet. Opening-night cards appear when the schedule posts — we do not invent matchups.",
  },
  wnba: {
    title: "Today’s Slate",
    emptyHint:
      "No WNBA slate on the board right now. Next available day posts here when scheduled — we do not invent matchups.",
  },
  ncaam: {
    title: "Today’s Slate",
    emptyHint:
      "No college basketball board posted yet. Opening slate appears when the schedule posts — we do not invent matchups.",
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
  weekLabel?: string | null,
): string | null {
  if (status === "timeout" || status === "error") return null;
  if (status === "empty" || gameCount === 0) return null;
  const count =
    gameCount === 1
      ? "1 matchup on the board"
      : `${gameCount} matchups on the board`;
  return weekLabel ? `${weekLabel} · ${count}` : count;
}

export default function OverviewEdgeBoardSlate({
  sport,
  games,
  status = "ready",
  weekLabel = null,
  week = null,
}: {
  sport: string;
  games: TonightGame[];
  status?: OverviewSlateStatus;
  weekLabel?: string | null;
  week?: number | null;
}) {
  const meta = SLATE_META[sport] ?? {
    title: "Today’s Slate",
    emptyHint:
      "Slate cards appear when the schedule posts — we do not invent matchups.",
  };
  const cfbWeek = typeof week === "number" && Number.isFinite(week) ? week : 1;
  const edgeBoardHref =
    sport === "cfb"
      ? `/edge-board/cfb?week=${cfbWeek}`
      : `/edge-board/${sport}`;
  const emptyCopy =
    status === "timeout" || status === "error"
      ? (STATUS_HINT[status] ?? meta.emptyHint)
      : meta.emptyHint;
  const statusLine = subtleStatusLine(status, games.length, weekLabel);

  return (
    <div className="relative mt-2.5 border-t border-white/10 pt-2.5 sm:mt-3 sm:pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            {meta.title}
          </p>
          {statusLine ? (
            <p className="mt-0.5 text-[11px] leading-tight text-kos-text/50">
              {statusLine}
            </p>
          ) : null}
        </div>
        <Link
          href={edgeBoardHref}
          className="min-h-9 inline-flex items-center rounded-lg border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55 hover:bg-kos-gold/25"
        >
          Full Edge Board →
        </Link>
      </div>

      <div className="mt-2.5">
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
