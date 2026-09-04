/**
 * Shared Overview Edge Board slate — primary above-the-fold product surface.
 * One CTA only: Full Edge Board. Sport-specific matchup cards via WeeklyGamesScroller.
 */

import Link from "next/link";
import type { TonightGame } from "@/lib/edge-board-tonight";
import WeeklyGamesScroller from "@/components/pro/WeeklyGamesScroller";

const SLATE_META: Record<
  string,
  { eyebrow: string; title: string; emptyHint: string }
> = {
  nfl: {
    eyebrow: "Current slate",
    title: "Edge Board",
    emptyHint:
      "No live REG matchup cards on the board yet. Open Edge Board when markets post.",
  },
  nba: {
    eyebrow: "Today’s slate",
    title: "Edge Board",
    emptyHint:
      "No NBA game board posted right now. Shell stays ready — we do not invent matchups.",
  },
  mlb: {
    eyebrow: "Today’s slate",
    title: "Edge Board",
    emptyHint:
      "No MLB slate rows yet. Edge Board refreshes when books and starters post.",
  },
};

export default function OverviewEdgeBoardSlate({
  sport,
  games,
}: {
  sport: string;
  games: TonightGame[];
}) {
  const meta = SLATE_META[sport] ?? {
    eyebrow: "Current slate",
    title: "Edge Board",
    emptyHint: "Slate cards appear when live board data is available.",
  };
  const edgeBoardHref = `/edge-board/${sport}`;

  return (
    <section className="mt-6 rounded-2xl border border-kos-gold/25 bg-linear-to-r from-kos-gold/12 via-black/40 to-black/60 p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            {meta.eyebrow}
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
            {meta.title}
          </h2>
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
          emptyCopy={meta.emptyHint}
        />
      </div>
    </section>
  );
}
