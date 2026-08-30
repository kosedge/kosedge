import type { Metadata } from "next";
import Link from "next/link";
import { formatArticleAttribution } from "@/lib/article-sectionizer";
import { getAllDeskHandicaps } from "@/lib/desk-handicaps";
import { articleShellClasses } from "@/lib/article-prose";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Desk Handicaps",
  description:
    "KosEdge bylined multi-sport desk handicaps — fair, market, lean or Pass, confidence, key risk.",
};

export default function DeskHandicapsIndexPage() {
  const articles = getAllDeskHandicaps();

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <header>
        <p className={articleShellClasses.eyebrow}>Pro · Desk</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          Desk handicaps
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-kos-text/75">
          Bylined first-live handicaps across NFL, WNBA, MLB, NBA, and NHL. Thin
          edges stay Pass.
        </p>
      </header>

      <ul className="mt-8 space-y-4">
        {articles.map((article) => (
          <li key={article.slug}>
            <Link
              href={article.href}
              className="block rounded-2xl border border-white/10 bg-kos-surface/40 p-5 transition hover:border-kos-gold/35"
            >
              <p className="text-xs text-kos-text/60">
                {article.sport} · {article.byline} ·{" "}
                {formatArticleAttribution(article.publishedAt, {
                  brand: false,
                })}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-kos-text">
                {article.title}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-kos-text/75">
                {article.excerpt}
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-kos-gold">
                Read handicap →
              </p>
            </Link>
          </li>
        ))}
      </ul>

      {articles.length === 0 ? (
        <p className="mt-8 text-sm text-kos-text/60">
          No desk handicaps published yet.
        </p>
      ) : null}

      <footer className="mt-10 flex flex-wrap gap-4 text-sm">
        <Link
          href="/pro/nfl/news"
          className="text-kos-gold hover:text-kos-gold/90"
        >
          ← NFL news
        </Link>
        <Link
          href="/pro/nfl/overview"
          className="text-kos-text/70 hover:text-kos-gold"
        >
          NFL overview
        </Link>
      </footer>
    </main>
  );
}
