import Link from "next/link";
import {
  footerCardClassName,
  footerCtaClassName,
  footerTitleClassName,
  getSportDeskConfig,
} from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewPageHeader from "@/components/pro/OverviewPageHeader";
import OverviewEdgeBoardSlate from "@/components/pro/OverviewEdgeBoardSlate";
import SportOverviewSection from "@/components/pro/SportOverviewSection";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function NbaOverviewPage() {
  const desk = getSportDeskConfig("nba");
  const content = buildSportOverviewContent("nba", "NBA");
  const tonightGames = await loadOverviewSlateGames("nba");
  const edgeBoardHref = "/edge-board/nba";

  // Slate lives at top — drop the duplicate Weekly Slate link wall.
  const gridSections = buildSportOverviewSections({
    sportKey: "nba",
    base: "/pro/nba",
    edgeBoardHref,
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  const footerCards = desk.footerCards;
  const footerCols =
    footerCards.length >= 5
      ? "sm:grid-cols-2 lg:grid-cols-3"
      : footerCards.length >= 3
        ? "sm:grid-cols-2 lg:grid-cols-3"
        : "sm:grid-cols-2";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <OverviewPageHeader sportLabel="NBA" />

      <OverviewEdgeBoardSlate sport="nba" games={tonightGames} />

      {/* Betting Desk / Props & Fantasy / League Intel / Model Governance */}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {gridSections.map((section) => (
          <SportOverviewSection
            key={section.title}
            title={section.title}
            subtitle={section.subtitle}
            links={section.links}
          />
        ))}
        <Link
          href="/insights/sports/nba"
          className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-5 transition hover:border-kos-gold/45"
        >
          <h3 className="font-semibold text-kos-gold">Insights</h3>
          <p className="mt-2 text-sm text-kos-text/70">
            Desk notes and doctrine for NBA — This Week and house rules.
          </p>
        </Link>
      </div>

      <section id="tools" className="mt-8 scroll-mt-28">
        <h2 className="text-xl font-semibold tracking-tight text-kos-text">
          Research tools
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          Power ratings, odds compare, and NBA research desks.
        </p>
        <div className={`mt-4 grid gap-4 ${footerCols}`}>
          {footerCards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className={footerCardClassName(card.accent)}
            >
              <h3 className={footerTitleClassName(card.accent)}>
                {card.title}
              </h3>
              <p className="mt-2 text-sm text-kos-text/80">
                {card.description}
              </p>
              <span className={footerCtaClassName(card.accent)}>
                {card.cta}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
