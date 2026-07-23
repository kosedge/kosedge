import Link from "next/link";
import { getSport } from "@/lib/sports";
import { HIGHLIGHTED_GAMES } from "@/lib/featured-games";
import { getTonightGames } from "@/lib/edge-board-tonight";
import {
  buildSportOverviewContent,
  buildSportOverviewSections,
  hasArticleData,
} from "@/lib/pro-sport-ia";
import EdgeBoardPreview from "@/components/EdgeBoardPreview";
import SportOverviewSection from "@/components/pro/SportOverviewSection";
import WeeklyGamesScroller from "@/components/pro/WeeklyGamesScroller";

type SpotlightGame = (typeof HIGHLIGHTED_GAMES)[number];

function signalFromGame(game: SpotlightGame, sportKey: string): string {
  const lineEdge = game.row.edgeLineNum ?? 0;
  const totalEdge = game.row.edgeOUNum ?? 0;
  const maxEdge = Math.max(lineEdge, totalEdge);
  if (maxEdge >= 2.5) return `Strong model separation (${maxEdge.toFixed(1)} pts)`;
  if (maxEdge >= 1.0) return `Actionable lean (${maxEdge.toFixed(1)} pts)`;
  if (sportKey === "mlb") return "Monitoring starter and lineup confirmations";
  if (sportKey === "nhl") return "Monitoring goalie and total discovery";
  if (sportKey === "nfl" || sportKey === "cfb")
    return "Monitoring key-number discovery into close";
  return "Monitoring market discovery into close";
}

export default async function SportOverviewPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;
  const edgeBoardHref = `/edge-board/${sportKey}`;
  const content = buildSportOverviewContent(sportKey, sportName);

  const sportGames = HIGHLIGHTED_GAMES.filter((g) => g.sport === sportKey);
  const tonightGames = await getTonightGames(sportKey);
  const spotlightGames: SpotlightGame[] =
    tonightGames.slice(0, 3).length > 0
      ? tonightGames.slice(0, 3).map((game) => ({
          slug: game.slug,
          row: game.row,
          sport: game.sport,
        }))
      : sportGames.slice(0, 3);

  const sectionLinks = buildSportOverviewSections({
    sportKey,
    base,
    edgeBoardHref,
    content,
  });

  const populatedSpotlightGames = spotlightGames.filter((game) =>
    hasArticleData(game.row),
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/40 to-black/60 p-6 shadow-2xl shadow-black/25 backdrop-blur-xl sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {content.heroBadge}
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              {sportName} Overview
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-kos-text/80 sm:text-base">
              {content.heroSummary}
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-56">
            <Link
              href={edgeBoardHref}
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/15 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55 hover:bg-kos-gold/20"
            >
              {content.boardCta}
            </Link>
            <Link
              href={`${base}/slate/today`}
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/35 hover:bg-white/10"
            >
              {content.slateCta}
            </Link>
          </div>
        </div>
      </section>

      <div className="mt-6">
        <WeeklyGamesScroller games={tonightGames} sport={sportKey} />
      </div>

      {sportKey === "nfl" ? (
        <section className="mt-6">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-kos-text">Betting Desk</h2>
              <p className="mt-1 text-sm text-kos-text/70">
                KEI Lines → Edges → Props — Kosedge lines into actionable edges.
              </p>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Link
              href="/pro/nfl/fair-lines"
              className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-5 transition hover:border-kos-gold/45 hover:bg-kos-gold/10"
            >
              <h3 className="text-lg font-semibold text-kos-gold">KEI Lines</h3>
              <p className="mt-2 text-sm text-kos-text/75">
                Kosedge spreads, totals, and fair moneylines for the slate.
              </p>
              <span className="mt-3 inline-block text-sm font-semibold text-kos-gold">Open KEI Lines →</span>
            </Link>
            <Link
              href="/pro/nfl/edges"
              className="rounded-2xl border border-edge-green/30 bg-edge-green/5 p-5 transition hover:border-edge-green/50 hover:bg-edge-green/10"
            >
              <h3 className="text-lg font-semibold text-edge-green">Edges</h3>
              <p className="mt-2 text-sm text-kos-text/75">
                Thresholded game + prop edges with side and confidence.
              </p>
              <span className="mt-3 inline-block text-sm font-semibold text-edge-green">Open edges desk →</span>
            </Link>
            <Link
              href="/pro/nfl/props"
              className="rounded-2xl border border-white/12 bg-black/30 p-5 transition hover:border-kos-gold/40"
            >
              <h3 className="text-lg font-semibold text-kos-text">Props</h3>
              <p className="mt-2 text-sm text-kos-text/70">
                Full player prop board — model means, fair prices, market joins.
              </p>
              <span className="mt-3 inline-block text-sm font-semibold text-kos-gold">Open props board →</span>
            </Link>
          </div>
        </section>
      ) : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {sectionLinks.map((section) => (
          <SportOverviewSection
            key={section.title}
            title={section.title}
            subtitle={section.subtitle}
            links={section.links}
          />
        ))}
      </div>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6 backdrop-blur-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-kos-text">
              Article Highlights
            </h2>
            <p className="mt-1 text-sm text-kos-text/70">
              {content.articleSubtitle}
            </p>
          </div>
          <span className="rounded-full border border-kos-gold/30 bg-kos-gold/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
            {content.articleToneBadge}
          </span>
        </div>

        {populatedSpotlightGames.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {populatedSpotlightGames.map((game) => (
              <div
                key={game.slug}
                className="rounded-xl border border-white/10 bg-white/2 p-4"
              >
                <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-kos-gold/90">
                  {signalFromGame(game, sportKey)}
                </div>
                <EdgeBoardPreview
                  row={game.row}
                  articleHref={`/pro/articles/${game.slug}`}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 bg-white/2 p-4 text-sm text-kos-text/70">
            {content.articleEmpty}
          </div>
        )}
      </section>

      <section className={`mt-6 grid gap-4 ${sportKey === "nfl" ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
        <Link
          href={`/pro/power-ratings/${sportKey}`}
          className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-6 transition hover:border-kos-gold/45 hover:bg-kos-gold/10"
        >
          <h2 className="text-xl font-semibold text-kos-gold">Power Ratings</h2>
          <p className="mt-2 text-sm text-kos-text/80">
            Team strength, tiering, and historical movement with weekly context.
          </p>
          <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
            View ratings →
          </span>
        </Link>
        <Link
          href={`/pro/kei-lines/${sportKey}`}
          className="rounded-2xl border border-white/12 bg-black/30 p-6 transition hover:border-kos-gold/40"
        >
          <h2 className="text-xl font-semibold text-kos-text">KEI Lines</h2>
          <p className="mt-2 text-sm text-kos-text/70">
            Projected spread/total baselines to benchmark current market prices.
          </p>
          <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
            View KEI lines →
          </span>
        </Link>
        {sportKey === "nfl" ? (
          <Link
            href="/pro/nfl/projections"
            className="rounded-2xl border border-kos-gold/30 bg-linear-to-br from-kos-gold/10 via-black/30 to-black/55 p-6 transition hover:border-kos-gold/50 hover:bg-kos-gold/10"
          >
            <h2 className="text-xl font-semibold text-kos-gold">Projections Hub</h2>
            <p className="mt-2 text-sm text-kos-text/80">
              User-friendly wins, futures, and player fantasy projection tables built from the latest preseason bundle.
            </p>
            <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
              Open projections hub →
            </span>
          </Link>
        ) : null}
        {sportKey === "nfl" ? (
          <Link
            href="/wall-chart/nfl-2026"
            className="rounded-2xl border border-edge-green/30 bg-linear-to-br from-edge-green/10 via-black/30 to-black/55 p-6 transition hover:border-edge-green/50 hover:bg-edge-green/10"
          >
            <h2 className="text-xl font-semibold text-edge-green">2026 Wall Chart</h2>
            <p className="mt-2 text-sm text-kos-text/80">
              Printable 24×18 NFL schedule tracker — laminated wet-erase friendly with full 2026 matchups.
            </p>
            <span className="mt-4 inline-block text-sm font-semibold text-edge-green">
              Open wall chart →
            </span>
          </Link>
        ) : null}
        {sportKey === "nfl" ? (
          <Link
            href="/pro/nfl/fantasy"
            className="rounded-2xl border border-kos-gold/30 bg-linear-to-br from-kos-gold/10 via-black/30 to-black/55 p-6 transition hover:border-kos-gold/50 hover:bg-kos-gold/10"
          >
            <h2 className="text-xl font-semibold text-kos-gold">Fantasy Draft Board</h2>
            <p className="mt-2 text-sm text-kos-text/80">
              Full VOR-ranked draft board across QB/RB/WR/TE/K/DST with tiers, position filters, and scoring toggles.
            </p>
            <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
              Open draft board →
            </span>
          </Link>
        ) : null}
        {sportKey === "nfl" ? (
          <Link
            href="/pro/nfl/awards"
            className="rounded-2xl border border-white/12 bg-black/30 p-6 transition hover:border-kos-gold/40"
          >
            <h2 className="text-xl font-semibold text-kos-text">MVP &amp; OPOY Race</h2>
            <p className="mt-2 text-sm text-kos-text/70">
              Real projected award contenders with the team success + stat evidence behind every ranking.
            </p>
            <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
              View award race →
            </span>
          </Link>
        ) : null}
      </section>
    </main>
  );
}
