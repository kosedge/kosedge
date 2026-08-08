import Link from "next/link";
import type { InsightArticle } from "@/lib/insights/types";
import { formatInsightDate, sportLabel } from "@/lib/insights/format";

function hrefFor(article: InsightArticle): string {
  if (article.kind === "doctrine") {
    return `/insights/doctrine/${article.slug}`;
  }
  return `/insights/notes/${article.slug}`;
}

export default function InsightCard({
  article,
  teaserOnly = false,
}: {
  article: InsightArticle;
  /** Show teaser + Pro CTA instead of bottom line deep dive. */
  teaserOnly?: boolean;
}) {
  const href = hrefFor(article);
  const summary = teaserOnly
    ? (article.teaser ?? article.bottomLine)
    : article.bottomLine;

  return (
    <article className="rounded-2xl border border-kos-border bg-kos-surface/40 p-5 transition hover:border-kos-gold/35">
      <div className="flex flex-wrap items-center gap-2 text-xs text-kos-text/55">
        <time dateTime={article.updatedAt}>
          {formatInsightDate(article.updatedAt)}
        </time>
        {article.sports?.map((s) => (
          <span
            key={s}
            className="rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 font-medium text-kos-text/70"
          >
            {sportLabel(s)}
          </span>
        ))}
        {article.kind === "doctrine" && (
          <span className="rounded-md border border-kos-gold/25 bg-kos-gold/10 px-1.5 py-0.5 font-medium text-kos-gold">
            Doctrine
          </span>
        )}
        {article.tier === "pro" && (
          <span className="rounded-md border border-kos-green/30 bg-kos-green/10 px-1.5 py-0.5 font-medium text-kos-green">
            Pro
          </span>
        )}
      </div>

      <h2 className="mt-3 text-xl font-semibold tracking-tight text-kos-text">
        <Link href={href} className="hover:text-kos-gold transition-colors">
          {article.title}
        </Link>
      </h2>

      <p className="mt-2 text-sm leading-6 text-kos-text/75">{summary}</p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Link
          href={href}
          className="text-sm font-semibold text-kos-gold hover:underline"
        >
          {teaserOnly ? "Preview →" : "Read →"}
        </Link>
        {teaserOnly && (
          <Link
            href="/pro"
            className="text-sm font-semibold text-kos-green hover:underline"
          >
            Unlock with Pro →
          </Link>
        )}
      </div>
    </article>
  );
}
