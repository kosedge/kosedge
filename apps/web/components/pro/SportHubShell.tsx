import Link from "next/link";
import type { ReactNode } from "react";
import {
  getSportEdgeBoardHref,
  getSportOverviewHref,
} from "@/lib/sport-pro-nav";

/**
 * Compact page chrome for sport tool surfaces already wrapped by SportProShell.
 * Always surfaces Overview + Edge Board for consistent desk navigation.
 */
export default function SportHubShell({
  sportKey,
  sportName,
  base,
  title,
  summary,
  badge,
  children,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
}: {
  sportKey?: string;
  sportName: string;
  base: string;
  title: string;
  summary: string;
  badge?: string;
  children: ReactNode;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}) {
  const key =
    sportKey ||
    base.replace(/^\/pro\//, "").split("/")[0] ||
    "nfl";
  const overviewHref = getSportOverviewHref(key);
  const edgeHref = getSportEdgeBoardHref(key);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.12),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              {badge ?? `${sportName} research desk`}
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-kos-text sm:text-3xl">
              {title}
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              {summary}
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs">
              <Link
                href={overviewHref}
                className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
              >
                ← {sportName} Overview
              </Link>
              <Link
                href={edgeHref}
                className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
              >
                Edge Board →
              </Link>
            </div>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-48">
            {primaryHref && primaryLabel ? (
              <Link
                href={primaryHref}
                className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25"
              >
                {primaryLabel}
              </Link>
            ) : null}
            {secondaryHref && secondaryLabel ? (
              <Link
                href={secondaryHref}
                className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/35 hover:bg-white/10"
              >
                {secondaryLabel}
              </Link>
            ) : null}
          </div>
        </div>
      </section>
      <div className="mt-6">{children}</div>
    </main>
  );
}
