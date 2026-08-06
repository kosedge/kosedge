import ArticleShell from "@/components/articles/ArticleShell";
import ArticleSection from "@/components/articles/ArticleSection";
import ArticleProseBody from "@/components/articles/ArticleProseBody";
import {
  articleKeyPointsClasses,
  articleNumberCardClasses,
} from "@/lib/article-prose";
import {
  formatArticleDate,
  sectionizeNewsUpdate,
  type HandicappersNote,
} from "@/lib/article-sectionizer";
import type { NflNewsUpdateArticle } from "@/lib/nfl-news-updates";

type NewsUpdateArticleProps = {
  article: NflNewsUpdateArticle;
};

function HandicapperStrip({ note }: { note: HandicappersNote }) {
  if (!note.lean && !note.marketNumber && !note.fairNumber) return null;

  return (
    <div className={articleNumberCardClasses}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold">
        Handicapper&apos;s note
      </p>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {note.marketNumber ? (
          <div>
            <dt className="text-xs text-kos-text/60">Market</dt>
            <dd className="mt-1 font-semibold text-kos-text">{note.marketNumber}</dd>
          </div>
        ) : null}
        {note.fairNumber ? (
          <div>
            <dt className="text-xs text-kos-text/60">Fair</dt>
            <dd className="mt-1 font-semibold text-kos-gold">{note.fairNumber}</dd>
          </div>
        ) : null}
        {note.lean ? (
          <div>
            <dt className="text-xs text-kos-text/60">Lean</dt>
            <dd className="mt-1 font-semibold text-kos-text">{note.lean}</dd>
          </div>
        ) : null}
        {note.confidence ? (
          <div>
            <dt className="text-xs text-kos-text/60">Confidence</dt>
            <dd className="mt-1 font-semibold text-kos-text">{note.confidence}</dd>
          </div>
        ) : null}
      </dl>
      {note.keyRisk ? (
        <p className="mt-4 text-sm leading-relaxed text-kos-text/85">
          <span className="font-semibold text-kos-text/70">Key risk · </span>
          {note.keyRisk}
        </p>
      ) : null}
      {note.disclaimer ? (
        <p className="mt-4 text-xs leading-relaxed text-kos-text/55">
          {note.disclaimer}
        </p>
      ) : null}
    </div>
  );
}

export default function NewsUpdateArticle({ article }: NewsUpdateArticleProps) {
  const slots = sectionizeNewsUpdate(article.bodyMarkdown);
  const bottomLine = article.dek || slots.bottomLine.replace(/\*\*/g, "");
  const sources = article.sources || slots.sources;

  return (
    <ArticleShell
      eyebrow={`KosEdge · ${article.category}`}
      title={article.title}
      date={formatArticleDate(article.publishedAt, { includeTime: true })}
      metaLine={article.team ? `${article.teamName ?? article.team} desk` : undefined}
      bottomLine={bottomLine}
      accent="neutral"
      breadcrumbs={[
        { label: "NFL Overview", href: "/pro/nfl/overview" },
        { label: "Camp Desk", href: "/pro/nfl/camp" },
        { label: "News", href: "/pro/nfl/news" },
        { label: article.shortTitle ?? "Update" },
      ]}
      footerLinks={[
        { label: "← Camp desk", href: "/pro/nfl/camp" },
        { label: "All news", href: "/pro/nfl/news" },
        ...(article.team
          ? [
              {
                label: "Season preview",
                href: `/pro/nfl/previews/${article.team}`,
              },
            ]
          : []),
      ]}
    >
      {slots.keyPoints.length > 0 ? (
        <ArticleSection label="Key points" id="key-points">
          <ul className={articleKeyPointsClasses}>
            {slots.keyPoints.map((point) => (
              <li
                key={point}
                className="flex gap-2 text-[0.9375rem] leading-relaxed text-kos-text/90 sm:text-base"
              >
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-kos-gold" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </ArticleSection>
      ) : null}

      {slots.bodySections.map((section) => (
        <ArticleSection
          key={section.heading ?? "body"}
          label="Update"
          title={section.heading ?? undefined}
          id={section.heading?.toLowerCase().replace(/\s+/g, "-") ?? "body"}
        >
          <ArticleProseBody source={section.content} />
        </ArticleSection>
      ))}

      {slots.watchNext.trim() ? (
        <ArticleSection label="What to watch next" id="watch-next">
          <ArticleProseBody source={slots.watchNext} />
        </ArticleSection>
      ) : null}

      {sources ? (
        <ArticleSection label="Sources" id="sources">
          <ArticleProseBody source={sources} />
        </ArticleSection>
      ) : null}

      <HandicapperStrip note={slots.handicappersNote} />
    </ArticleShell>
  );
}
