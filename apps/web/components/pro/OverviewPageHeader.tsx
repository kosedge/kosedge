/**
 * Shared Overview page header for NFL / NBA / MLB.
 * Minimal brand hierarchy — sport label, Overview, tagline. No CTA stack.
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
    <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.14),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
      <div className="relative max-w-2xl">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          {sportLabel}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
          Overview
        </h1>
        <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
          {OVERVIEW_TAGLINE}
        </p>
      </div>
    </section>
  );
}
