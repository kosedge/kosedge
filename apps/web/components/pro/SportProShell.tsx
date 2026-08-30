import type { ReactNode } from "react";
import Link from "next/link";
import SportProHeader from "@/components/pro/SportProHeader";
import {
  getSportEdgeBoardHref,
  getSportOverviewHref,
  sportDisplayShort,
} from "@/lib/sport-pro-nav";
import { sportDisplayLabel } from "@/lib/sports";

/**
 * Shared chrome for all Pro / Edge Board / Odds sport surfaces:
 * logo header, sports nav, sport-specific subnav, optional page chrome.
 * Desk status / freshness probes stay off customer layouts — hub owns that.
 */
export default function SportProShell({
  sport,
  children,
  pageTitle,
  pageSubtitle,
  actions,
}: {
  sport: string;
  children: ReactNode;
  /** @deprecated Unused — desk status bar no longer mounts on product layouts. */
  showFreshness?: boolean;
  pageTitle?: string;
  pageSubtitle?: string;
  actions?: ReactNode;
}) {
  const sportKey = (sport || "nfl").toLowerCase();
  const overviewHref = getSportOverviewHref(sportKey);
  const edgeHref = getSportEdgeBoardHref(sportKey);
  const short = sportDisplayShort(sportKey);
  const full = sportDisplayLabel(sportKey);

  return (
    <div className="min-h-screen bg-kos-black text-kos-text">
      <SportProHeader activeSport={sportKey} />

      {(pageTitle || actions) && (
        <div className="border-b border-white/5 bg-kos-surface/20">
          <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 py-5 sm:px-6">
            <div className="min-w-0">
              {pageTitle ? (
                <h1 className="text-2xl font-semibold tracking-tight text-kos-text sm:text-3xl">
                  {pageTitle}
                </h1>
              ) : null}
              {pageSubtitle ? (
                <p className="mt-1 max-w-2xl text-sm text-kos-text/70">
                  {pageSubtitle}
                </p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                <Link
                  href={overviewHref}
                  className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
                >
                  ← {short} Overview
                </Link>
                <Link
                  href={edgeHref}
                  className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
                >
                  Edge Board →
                </Link>
                <span className="hidden text-kos-text/35 sm:inline">
                  {full}
                </span>
              </div>
            </div>
            {actions ? (
              <div className="flex flex-wrap items-center gap-2">{actions}</div>
            ) : null}
          </div>
        </div>
      )}

      {children}
    </div>
  );
}
