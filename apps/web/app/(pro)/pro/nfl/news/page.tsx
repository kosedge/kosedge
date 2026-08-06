import type { Metadata } from "next";
import Link from "next/link";
import { formatArticleAttribution } from "@/lib/article-sectionizer";
import { getAllNflNewsUpdates } from "@/lib/nfl-news-updates";
import { articleShellClasses } from "@/lib/article-prose";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL News & Updates",
  description:
    "KosEdge camp news breaks and market updates — scannable, sourced, threshold-disciplined.",
};

export default function NflNewsIndexPage() {
  const articles = getAllNflNewsUpdates();

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <header>
        <p className={articleShellClasses.eyebrow}>NFL Pro · News & Updates</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          KosEdge desk briefs
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-kos-text/75">
          Fast camp news breaks and injury-driven updates. Thin edges stay Pass.
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
                {formatArticleAttribution(article.publishedAt)}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-kos-text">
                {article.title}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-kos-text/75">
                {article.excerpt}
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-kos-gold">
                Read update →
              </p>
            </Link>
          </li>
        ))}
      </ul>

      {articles.length === 0 ? (
        <p className="mt-8 text-sm text-kos-text/60">
          No KosEdge news breaks published yet.
        </p>
      ) : null}

      <footer className="mt-10">
        <Link
          href="/pro/nfl/camp"
          className="text-sm text-kos-gold hover:text-kos-gold/90"
        >
          ← Back to Camp Desk
        </Link>
      </footer>
    </main>
  );
}
