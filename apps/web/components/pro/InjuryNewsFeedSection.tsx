import Link from "next/link";
import type { InjuryNewsItem } from "@/lib/nfl-injury-news";

function formatPublished(value: string | null): string {
  if (!value) return "";
  const ts = Date.parse(value);
  if (!Number.isFinite(ts)) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  }).format(new Date(ts));
}

export default function InjuryNewsFeedSection({
  sportLabel,
  items,
  sourceSummary,
  emptyHint,
  campHref,
}: {
  sportLabel: string;
  items: InjuryNewsItem[];
  sourceSummary: string;
  emptyHint: string;
  campHref?: string;
}) {
  return (
    <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
      <div className="rounded-2xl border border-amber-400/25 bg-amber-400/5 p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-100/80">
              Injuries & News
            </p>
            <h2 className="mt-1 text-lg font-semibold text-kos-text">
              Availability headlines · multi-source
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-kos-text/70">
              {sourceSummary} KosEdge briefs with citations ship here when
              research clears.
            </p>
          </div>
          {campHref ? (
            <Link
              href={campHref}
              className="rounded-xl border border-kos-gold/30 bg-kos-gold/10 px-4 py-2 text-sm text-kos-gold hover:border-kos-gold/50"
            >
              {sportLabel === "NFL" ? "Camp Desk" : "Sport overview"}
            </Link>
          ) : null}
        </div>
        {items.length === 0 ? (
          <p className="mt-4 text-sm text-kos-text/65">{emptyHint}</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {items.map((item) => (
              <li key={item.id}>
                <a
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border border-white/10 bg-black/25 p-3 transition hover:border-kos-gold/35"
                >
                  <p className="text-[11px] uppercase tracking-wide text-kos-text/50">
                    {item.sourceLabel}
                    {item.published
                      ? ` · ${formatPublished(item.published)}`
                      : ""}
                  </p>
                  <p className="mt-1 font-medium text-kos-text">
                    {item.headline}
                  </p>
                  {item.description ? (
                    <p className="mt-1 text-sm text-kos-text/65">
                      {item.description}
                    </p>
                  ) : null}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
