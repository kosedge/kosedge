import Link from "next/link";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import { HIGHLIGHTED_GAMES } from "@/lib/featured-games";
import { getTonightGames } from "@/lib/edge-board-tonight";
import {
  buildSportOverviewContent,
  buildSportOverviewSections,
  hasArticleData,
} from "@/lib/pro-sport-ia";
import {
  deskCardClassName,
  footerCardClassName,
  footerCtaClassName,
  footerTitleClassName,
  getSportDeskConfig,
} from "@/lib/pro-sport-desk";
import EdgeBoardPreview from "@/components/EdgeBoardPreview";
import SportOverviewSection from "@/components/pro/SportOverviewSection";
import WeeklyGamesScroller from "@/components/pro/WeeklyGamesScroller";

type SpotlightGame = (typeof HIGHLIGHTED_GAMES)[number];

function signalFromGame(game: SpotlightGame, sportKey: string): string {
  const lineEdge = game.row.edgeLineNum ?? 0;
  const totalEdge = game.row.edgeOUNum ?? 0;
  const maxEdge = Math.max(lineEdge, totalEdge);
  if (maxEdge >= 2.5)
    return `Strong model separation (${maxEdge.toFixed(1)} pts)`;
  if (maxEdge >= 1.0) return `Actionable lean (${maxEdge.toFixed(1)} pts)`;
  if (sportKey === "mlb") return "Monitoring starter and lineup confirmations";
  if (sportKey === "nhl") return "Monitoring goalie and total discovery";
  if (sportKey === "nfl" || sportKey === "cfb")
    return "Monitoring key-number discovery into close";
  return "Monitoring market discovery into close";
}

function deskTitleClass(accent: "gold" | "green" | "neutral"): string {
  if (accent === "gold") return "text-lg font-semibold text-kos-gold";
  if (accent === "green") return "text-lg font-semibold text-edge-green";
  return "text-lg font-semibold text-kos-text";
}

function deskCtaClass(accent: "gold" | "green" | "neutral"): string {
  if (accent === "green")
    return "mt-3 inline-block text-sm font-semibold text-edge-green";
  return "mt-3 inline-block text-sm font-semibold text-kos-gold";
}

export default async function SportOverviewPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const edgeBoardHref = `/edge-board/${sportKey || "nfl"}`;
  const content = buildSportOverviewContent(sportKey, sportName);
  const desk = getSportDeskConfig(sportKey);

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

  const footerCols =
    desk.footerCards.length >= 5
      ? "sm:grid-cols-3"
      : desk.footerCards.length >= 3
        ? "sm:grid-cols-2 lg:grid-cols-4"
        : "sm:grid-cols-2";

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
        <section className="mt-6 rounded-2xl border border-kos-gold/20 bg-linear-to-r from-kos-gold/10 via-black/35 to-black/55 p-5 sm:p-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-2xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
                Training Camp Desk
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
                Daily camp cadence into preseason week 1
              </h2>
              <p className="mt-2 text-sm text-kos-text/75">
                Beat map, public camp headlines, and writer ownership — so the
                NFL Pro hub stays live while PRE boards use market + camp
                strength references (not empty model dashes).
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/pro/nfl/camp"
                className="rounded-xl border border-kos-gold/35 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
              >
                Open Camp Desk →
              </Link>
              <Link
                href="/pro/nfl/slate/today"
                className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35"
              >
                PRE + REG slate
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      <section className="mt-6">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-kos-text">
              Betting Desk
            </h2>
            <p className="mt-1 text-sm text-kos-text/70">
              {desk.pathLabel} — sport-specific desk path.
            </p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {desk.cards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className={deskCardClassName(card.accent, card.status)}
            >
              <h3 className={deskTitleClass(card.accent)}>{card.title}</h3>
              <p className="mt-2 text-sm text-kos-text/75">
                {card.description}
              </p>
              <span className={deskCtaClass(card.accent)}>{card.cta}</span>
            </Link>
          ))}
        </div>
      </section>

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

      <section className={`mt-6 grid gap-4 ${footerCols}`}>
        {desk.footerCards.map((card) => (
          <Link
            key={card.title}
            href={card.href}
            className={footerCardClassName(card.accent)}
          >
            <h2 className={footerTitleClassName(card.accent)}>{card.title}</h2>
            <p className="mt-2 text-sm text-kos-text/80">{card.description}</p>
            <span className={footerCtaClassName(card.accent)}>{card.cta}</span>
          </Link>
        ))}
      </section>
    </main>
  );
}
