import type { Metadata } from "next";
import Link from "next/link";
import {
  getAllNflSeasonPreviews,
  groupPreviewsByConference,
} from "@/lib/nfl-season-previews";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL 2026 Season Previews",
  description:
    "All 32 NFL team season previews from the Kos Edge writer desk — angles, win-total betting guides, and handicapper notes.",
};

export default function NflSeasonPreviewsIndexPage() {
  const articles = getAllNflSeasonPreviews();
  const groups = groupPreviewsByConference(articles);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/nfl/overview" className="hover:text-kos-gold">
          NFL Overview
        </Link>
        <span>/</span>
        <span className="text-kos-text">Season Previews</span>
      </nav>

      <section className="relative overflow-hidden rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/14 via-[#0b1220] to-black p-6 shadow-2xl sm:p-8">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgba(245,185,66,0.18), transparent 40%), radial-gradient(circle at 80% 0%, rgba(80,140,255,0.12), transparent 35%)",
          }}
        />
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            Research desk · Team Previews
          </p>
          <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
            2026 Season Previews
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-kos-text/80 sm:text-base">
            Thirty-two writer-owned team essays — market number first, beat
            context second, model conflict check before any lean.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/edge-board/nfl"
              className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
            >
              Edge Board
            </Link>
            <a
              href="#afc"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Jump AFC
            </a>
            <a
              href="#nfc"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Jump NFC
            </a>
          </div>
          <p className="mt-4 text-xs text-kos-text/60">
            At a Glance · {articles.length}/32 published
          </p>
        </div>
      </section>

      {articles.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-6 text-sm text-amber-100">
          Season preview files were not found in the deployment bundle. Check
          that <code>content/writers/season-previews-2026</code> is traced into
          the web build.
        </div>
      ) : (
        <div className="mt-8 space-y-8">
          {groups.map((group) => (
            <section
              key={`${group.conference}-${group.division}`}
              id={
                group.division === "East"
                  ? group.conference.toLowerCase()
                  : undefined
              }
            >
              <div className="mb-3 flex items-end justify-between gap-3">
                <h2 className="text-lg font-semibold text-kos-text">
                  {group.conference} {group.division}
                </h2>
                <p className="text-xs text-kos-text/55">
                  {group.articles.length} previews
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {group.articles.map((article) => (
                  <Link
                    key={article.team}
                    href={article.href}
                    className="group rounded-2xl border border-white/10 bg-black/35 p-5 transition hover:border-kos-gold/40 hover:bg-black/50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-gold/90">
                          {article.team}
                        </p>
                        <h3 className="mt-1 text-lg font-semibold text-kos-text group-hover:text-kos-gold">
                          {article.teamName}
                        </h3>
                      </div>
                      <p className="text-right text-xs text-kos-text/60">
                        {article.author}
                      </p>
                    </div>
                    {article.angle ? (
                      <p className="mt-3 text-sm font-medium text-kos-text/90">
                        {article.angle}
                      </p>
                    ) : null}
                    <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-kos-text/70">
                      {article.excerpt}
                    </p>
                    {article.market ? (
                      <p className="mt-3 text-xs text-kos-text/55">
                        Market · {article.market}
                      </p>
                    ) : null}
                    <p className="mt-4 text-xs font-semibold text-kos-gold">
                      Read preview →
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
