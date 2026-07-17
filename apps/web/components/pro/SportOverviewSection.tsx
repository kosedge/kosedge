import Link from "next/link";
import type { OverviewSectionLink } from "@/lib/pro-sport-ia";

export default function SportOverviewSection({
  title,
  subtitle,
  links,
}: {
  title: string;
  subtitle: string;
  links: OverviewSectionLink[];
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6 backdrop-blur-xl">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-kos-text">{title}</h3>
        <p className="mt-1 text-sm text-kos-text/70">{subtitle}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {links.map((link) => {
          const href = link.href;
          const isPlaceholder = !href || link.status === "placeholder";
          const key = `${title}-${href ?? link.label}`;

          if (isPlaceholder) {
            return (
              <div
                key={key}
                className="rounded-xl border border-white/10 bg-white/2 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-sm font-semibold text-kos-text">
                    {link.label}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {link.premium ? (
                      <span className="rounded-full border border-kos-gold/35 bg-kos-gold/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
                        Pro
                      </span>
                    ) : null}
                    <span className="rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-text/70">
                      Pending
                    </span>
                  </div>
                </div>
                <p className="mt-1 text-xs text-kos-text/60">{link.hint}</p>
              </div>
            );
          }

          return (
            <Link
              key={key}
              href={href}
              className="group rounded-xl border border-white/10 bg-white/2 px-4 py-3 transition hover:border-kos-gold/45 hover:bg-kos-gold/6"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-sm font-semibold text-kos-text">
                  {link.label}
                </span>
                {link.premium ? (
                  <span className="rounded-full border border-kos-gold/35 bg-kos-gold/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
                    Pro
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-kos-text/60">{link.hint}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
