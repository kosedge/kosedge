import Link from "next/link";
import type { ReactNode } from "react";

export default function SportHubShell({
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
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {badge ?? `Pro ${sportName}`}
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              {title}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-kos-text/80 sm:text-base">
              {summary}
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href={`${base}/overview`}
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Back to {sportName} Hub
            </Link>
            {primaryHref && primaryLabel ? (
              <Link
                href={primaryHref}
                className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
              >
                {primaryLabel}
              </Link>
            ) : null}
            {secondaryHref && secondaryLabel ? (
              <Link
                href={secondaryHref}
                className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
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
