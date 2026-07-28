import Link from "next/link";
import type { TonightGame } from "@/lib/edge-board-tonight";
import { hasArticleData } from "@/lib/pro-sport-ia";

type SportScrollerContent = {
  sectionTitle: string;
  sectionSubtitle: string;
  emptyCopy: string;
  signalHigh: string;
  signalModerate: string;
  movementSignal: string;
  defaultSignal: string;
};

const DEFAULT_SCROLLER_CONTENT: SportScrollerContent = {
  sectionTitle: "Weekly Games",
  sectionSubtitle: "Current slate with status, timing, and model signal.",
  emptyCopy: "Weekly slate cards appear when live board data is available.",
  signalHigh: "High model edge",
  signalModerate: "Actionable edge",
  movementSignal: "Market moved",
  defaultSignal: "Monitoring price discovery",
};

const SPORT_SCROLLER_CONTENT: Record<string, SportScrollerContent> = {
  nfl: {
    sectionTitle: "Weekly Matchups",
    sectionSubtitle: "Board timing, key-number pressure, and model separation.",
    emptyCopy: "NFL matchup cards appear once weekly market feeds refresh.",
    signalHigh: "High edge near key numbers",
    signalModerate: "Actionable key-number lean",
    movementSignal: "Spread shifted",
    defaultSignal: "Monitoring injury and key-number discovery",
  },
  cfb: {
    sectionTitle: "Weekly Matchups",
    sectionSubtitle: "Tempo leverage, havoc profile, and market response.",
    emptyCopy: "CFB matchup cards appear when weekly market data is live.",
    signalHigh: "High model separation",
    signalModerate: "Actionable matchup lean",
    movementSignal: "Spread shifted",
    defaultSignal: "Monitoring lineup and limit-driven movement",
  },
  mlb: {
    sectionTitle: "Daily Matchups",
    sectionSubtitle: "Starter/bullpen context and live market shape.",
    emptyCopy: "MLB cards appear after probable starters and prices post.",
    signalHigh: "High starter/market edge",
    signalModerate: "Actionable side/total lean",
    movementSignal: "Market moved",
    defaultSignal: "Monitoring lineup and pitcher confirmations",
  },
  nhl: {
    sectionTitle: "Daily Matchups",
    sectionSubtitle: "Goalie context, total environment, and price movement.",
    emptyCopy: "NHL cards appear once goaltender and market feeds sync.",
    signalHigh: "High goalie/market edge",
    signalModerate: "Actionable matchup lean",
    movementSignal: "Market moved",
    defaultSignal: "Monitoring goalie confirmation and totals shape",
  },
  nba: {
    sectionTitle: "Daily Matchups",
    sectionSubtitle: "Rotation context, pace profile, and edge signals.",
    emptyCopy: "NBA cards appear as availability and pricing feeds update.",
    signalHigh: "High rotation-adjusted edge",
    signalModerate: "Actionable pace/price lean",
    movementSignal: "Market moved",
    defaultSignal: "Monitoring availability-driven pricing",
  },
  wnba: {
    sectionTitle: "Daily Matchups",
    sectionSubtitle: "Usage concentration, pace control, and market signal.",
    emptyCopy: "WNBA cards appear when slate and market feeds are posted.",
    signalHigh: "High usage/market edge",
    signalModerate: "Actionable matchup lean",
    movementSignal: "Market moved",
    defaultSignal: "Monitoring rotation and travel-adjusted pricing",
  },
  ncaam: {
    sectionTitle: "Daily Matchups",
    sectionSubtitle: "Possession profile, variance pockets, and price signal.",
    emptyCopy: "College basketball cards appear when daily slate data is live.",
    signalHigh: "High model separation",
    signalModerate: "Actionable tempo/price lean",
    movementSignal: "Market moved",
    defaultSignal: "Monitoring lineup news and late steam",
  },
};

function getScrollerContent(sport: string): SportScrollerContent {
  return SPORT_SCROLLER_CONTENT[sport] ?? DEFAULT_SCROLLER_CONTENT;
}

function parseNumber(label: string): number | null {
  const n = Number.parseFloat(String(label).replace(/[^\d.+-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function getGameStatus(
  time?: string,
): "Upcoming" | "Live" | "Final" | "Listed" {
  const value = (time ?? "").toLowerCase();
  if (value.includes("live") || value.includes("q") || value.includes("half")) {
    return "Live";
  }
  if (value.includes("final") || value.includes("ft")) return "Final";
  if (value.includes("am") || value.includes("pm")) return "Upcoming";
  return "Listed";
}

function getSignal(game: TonightGame, content: SportScrollerContent): string {
  const lineEdge = game.row.edgeLineNum ?? 0;
  const totalEdge = game.row.edgeOUNum ?? 0;
  const maxEdge = Math.max(lineEdge, totalEdge);

  if (maxEdge >= 2.5) return `${content.signalHigh} ${maxEdge.toFixed(1)} pts`;
  if (maxEdge >= 1.0)
    return `${content.signalModerate} ${maxEdge.toFixed(1)} pts`;

  const openSpread = parseNumber(game.row.openLine.top.label);
  const bestSpread = parseNumber(game.row.bestLine.top.label);
  if (openSpread != null && bestSpread != null) {
    const shift = Math.abs(bestSpread - openSpread);
    if (shift >= 0.5)
      return `${content.movementSignal} ${shift.toFixed(1)} pts`;
  }

  return content.defaultSignal;
}

function withFallback(value: string | undefined, fallback: string): string {
  const normalized = (value ?? "").trim();
  if (
    !normalized ||
    normalized === "—" ||
    normalized.toLowerCase() === "coming soon"
  ) {
    return fallback;
  }
  return normalized;
}

export default function WeeklyGamesScroller({
  games,
  sport,
}: {
  games: TonightGame[];
  sport: string;
}) {
  const content = getScrollerContent(sport);

  if (!games.length) {
    return (
      <section className="rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6 backdrop-blur-xl">
        <h2 className="text-lg font-semibold text-kos-text">
          {content.sectionTitle}
        </h2>
        <p className="mt-2 text-sm text-kos-text/70">{content.emptyCopy}</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6 backdrop-blur-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-kos-text">
            {content.sectionTitle}
          </h2>
          <p className="mt-1 text-sm text-kos-text/70">
            {content.sectionSubtitle}
          </p>
        </div>
        <Link
          href={`/edge-board/${sport}`}
          className="rounded-lg border border-kos-gold/30 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold transition hover:border-kos-gold/50 hover:bg-kos-gold/15"
        >
          Open full board
        </Link>
      </div>

      <div className="-mx-1 overflow-x-auto pb-1">
        <div className="flex min-w-max gap-3 px-1">
          {games.map((game) => {
            const status = getGameStatus(game.row.time);
            const signal = getSignal(game, content);
            const bestLine = withFallback(
              game.row.bestLine.top.label,
              "Line pending",
            );
            const bestTotal = withFallback(
              game.row.bestOU.top.label,
              "Total pending",
            );
            const gameTime = withFallback(game.row.time, "Time pending");
            const hasData = hasArticleData(game.row);
            const statusClass =
              status === "Live"
                ? "border-kos-green/45 bg-kos-green/10 text-kos-green"
                : status === "Final"
                  ? "border-white/20 bg-white/5 text-kos-text/75"
                  : "border-kos-gold/30 bg-kos-gold/10 text-kos-gold";

            const card = (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass}`}
                  >
                    {status}
                  </span>
                  <span className="text-xs text-kos-text/60">{gameTime}</span>
                </div>
                <div className="mt-3 text-sm font-semibold text-kos-text">
                  {game.row.teamA.name} @ {game.row.teamB.name}
                </div>
                <div className="mt-2 text-xs text-kos-text/70">{signal}</div>
                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="text-kos-text/60">
                    Best {bestLine} / {bestTotal}
                  </span>
                  {hasData ? (
                    <span className="font-semibold text-kos-gold">Preview</span>
                  ) : (
                    <span className="font-semibold text-kos-text/70">
                      Data pending
                    </span>
                  )}
                </div>
              </>
            );

            if (!hasData) {
              return (
                <div
                  key={game.slug}
                  className="w-72 shrink-0 rounded-xl border border-white/10 bg-black/35 p-4"
                >
                  {card}
                </div>
              );
            }

            return (
              <Link
                key={game.slug}
                href={`/pro/articles/${game.slug}`}
                className="w-72 shrink-0 rounded-xl border border-white/10 bg-black/35 p-4 transition hover:border-kos-gold/45 hover:bg-kos-gold/5"
              >
                {card}
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
