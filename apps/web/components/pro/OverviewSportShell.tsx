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
 *
 * Header + slate share one hero surface (visual continuity); components stay
 * separate for reuse.
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
      <section
        aria-label={`${sportLabel} Overview`}
        className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.14),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7"
      >
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
        <div className="relative">
          <OverviewPageHeader sportLabel={sportLabel} />
          <OverviewEdgeBoardSlate
            sport={sportKey}
            games={slate.games}
            status={slate.status}
          />
        </div>
      </section>

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
