import Link from "next/link";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import { getCfbTeamPreviews } from "@/lib/cfb-previews";

export const dynamic = "force-dynamic";

export default function CfbPreviewsIndexPage() {
  const articles = getCfbTeamPreviews();

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/cfb/overview" className="hover:text-kos-gold">
          CFB Overview
        </Link>
        <span>/</span>
        <span className="text-kos-text">Team Previews</span>
      </nav>

      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/14 via-[#0b1220] to-black p-6 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          Research desk · Team Previews
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
          2026 CFB team previews
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-kos-text/80">
          KosEdge + date only — no writer byline. Locked house format. Research
          language. {articles.length} shipped today; template is reusable for
          the rest of the 136.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href="/pro/cfb/conferences"
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
          >
            Conference previews
          </Link>
          <Link
            href="/pro/cfb/teams"
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
          >
            Power / Teams
          </Link>
        </div>
      </section>

      <ul className="mt-8 grid gap-3 sm:grid-cols-2">
        {articles.map((p) => (
          <li key={p.slug}>
            <Link
              href={`/pro/cfb/previews/${p.slug}`}
              className="block min-h-11 rounded-2xl border border-white/10 bg-black/35 px-4 py-4 hover:border-kos-gold/40"
            >
              <p className="text-[11px] uppercase tracking-[0.12em] text-kos-gold">
                {p.conference} · {p.date}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-kos-text">
                {cfbTeamDisplayName(p.team)}
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
