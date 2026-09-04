import Link from "next/link";
import type { ReactNode } from "react";
import type { OverviewSection } from "@/lib/pro-sport-ia";
import type { OverviewSlateResult } from "@/lib/overview-slate-games";
import {
  footerCardClassName,
  footerCtaClassName,
  footerTitleClassName,
  type HubFooterCard,
} from "@/lib/pro-sport-desk";
import OverviewPageHeader from "@/components/pro/OverviewPageHeader";
import OverviewEdgeBoardSlate from "@/components/pro/OverviewEdgeBoardSlate";
import OverviewInsightsCard from "@/components/pro/OverviewInsightsCard";
import SportOverviewSection from "@/components/pro/SportOverviewSection";

/**
 * Shared flagship Overview composition for NFL / NBA / MLB.
 * Keeps above-the-fold shell + Insights + research tools aligned so dedicated
 * sport pages cannot drift independently.
 */
export default function OverviewSportShell({
  sportKey,
  sportLabel,
  slate,
  sections,
  footerCards,
  toolsSubtitle,
  extraBelowSections,
}: {
  sportKey: string;
  sportLabel: string;
  slate: OverviewSlateResult;
  sections: OverviewSection[];
  footerCards: HubFooterCard[];
  toolsSubtitle: string;
  /** Optional sport-only blocks inserted after section grid (rare). */
  extraBelowSections?: ReactNode;
}) {
  const footerCols =
    footerCards.length >= 3
      ? "sm:grid-cols-2 lg:grid-cols-3"
      : "sm:grid-cols-2";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <OverviewPageHeader sportLabel={sportLabel} />

      <OverviewEdgeBoardSlate
        sport={sportKey}
        games={slate.games}
        status={slate.status}
      />

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {sections.map((section) => (
          <SportOverviewSection
            key={section.title}
            title={section.title}
            subtitle={section.subtitle}
            links={section.links}
          />
        ))}
        <OverviewInsightsCard sportKey={sportKey} sportLabel={sportLabel} />
      </div>

      {extraBelowSections}

      <section id="tools" className="mt-8 scroll-mt-28">
        <h2 className="text-xl font-semibold tracking-tight text-kos-text">
          Research tools
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">{toolsSubtitle}</p>
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
