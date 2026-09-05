/**
 * Shared Overview page header for NFL / NBA / MLB.
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
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-kos-text sm:text-3xl">
        Overview
      </h1>
      <p className="mt-1 text-sm text-kos-text/70">{OVERVIEW_TAGLINE}</p>
    </header>
  );
}
