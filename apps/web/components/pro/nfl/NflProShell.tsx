import type { ReactNode } from "react";
import Link from "next/link";
import NflProHeader from "@/components/pro/nfl/NflProHeader";
import { NflDataFreshnessBanner } from "@/components/pro/NflDataFreshnessBanner";

/**
 * Shared chrome for NFL Pro surfaces: logo header, sports nav, NFL subnav,
 * freshness banner, and optional page chrome.
 */
export default function NflProShell({
  children,
  showFreshness = true,
  pageTitle,
  pageSubtitle,
  actions,
}: {
  children: ReactNode;
  showFreshness?: boolean;
  pageTitle?: string;
  pageSubtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-kos-black text-kos-text">
      <NflProHeader activeSport="nfl" />
      {showFreshness ? <NflDataFreshnessBanner /> : null}

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
                  href="/pro/nfl/overview"
                  className="font-medium text-kos-gold/90 hover:text-kos-gold"
                >
                  ← NFL Overview
                </Link>
                <Link
                  href="/edge-board/nfl"
                  className="font-medium text-kos-text/65 hover:text-kos-text"
                >
                  Edge Board →
                </Link>
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
