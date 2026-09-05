/**
 * Shared Overview page header for every sport hub.
 * Typography only — chrome lives on OverviewSportShell so header + slate
 * read as one continuous hero surface.
 */

import { SPORT_TAGLINE } from "@/lib/sport-pro-nav";

/** Brand-standard Overview tagline (period form = two deliberate statements). */
export const OVERVIEW_TAGLINE = SPORT_TAGLINE;

export default function OverviewPageHeader({
  sportLabel,
}: {
  /** Display label, e.g. "NFL", "NBA", "MLB" */
  sportLabel: string;
}) {
  return (
    <header className="relative max-w-2xl">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
        {sportLabel}
      </p>
      <h1 className="mt-0.5 text-2xl font-semibold tracking-tight text-kos-text sm:text-[1.75rem] sm:leading-tight">
        Overview
      </h1>
      <p className="mt-0.5 text-sm leading-snug text-kos-text/70">
        {OVERVIEW_TAGLINE}
      </p>
    </header>
  );
}
