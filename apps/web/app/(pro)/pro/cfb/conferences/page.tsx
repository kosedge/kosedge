import Link from "next/link";
import { getCfbConferencePreviews } from "@/lib/cfb-previews";

export const dynamic = "force-dynamic";

export default function CfbConferencesIndexPage() {
  const articles = getCfbConferencePreviews();

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/cfb/overview" className="hover:text-kos-gold">
          CFB Overview
        </Link>
        <span>/</span>
        <span className="text-kos-text">Conference Previews</span>
      </nav>

      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/14 via-[#0b1220] to-black p-6 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          Research desk · Conferences
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
          2026 conference previews
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-kos-text/80">
          Power 4 + Notre Dame / Independent note + two Group-of-X (AAC,
          Mountain West). Linked from Teams filter and Overview.
        </p>
        <Link
          href="/pro/cfb/teams?conf=p4"
          className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-kos-gold"
        >
          Filter Teams · Power 4 →
        </Link>
      </section>

      <ul className="mt-8 grid gap-3 sm:grid-cols-2">
        {articles.map((p) => (
          <li key={p.slug}>
            <Link
              href={`/pro/cfb/conferences/${p.slug}`}
              className="block min-h-11 rounded-2xl border border-white/10 bg-black/35 px-4 py-4 hover:border-kos-gold/40"
            >
              <p className="text-[11px] uppercase tracking-[0.12em] text-kos-gold">
                {p.date}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-kos-text">
                {p.title}
              </h2>
              <p className="mt-2 line-clamp-3 text-sm text-kos-text/70">
                {p.bottomLine}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
