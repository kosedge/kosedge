import ArticleShell from "@/components/articles/ArticleShell";
import ArticleSection from "@/components/articles/ArticleSection";
import ArticleProseBody from "@/components/articles/ArticleProseBody";
import { articleNumberCardClasses } from "@/lib/article-prose";
import {
  formatArticleDate,
  sectionizeDeskHandicap,
  type HandicappersNote,
} from "@/lib/article-sectionizer";
import type { DeskHandicapArticle } from "@/lib/desk-handicaps";

type DeskHandicapArticleViewProps = {
  article: DeskHandicapArticle;
};

function HandicapperStrip({ note }: { note: HandicappersNote }) {
  if (!note.lean && !note.marketNumber && !note.fairNumber) return null;

  const heading = note.label
    ? `Handicapper's note — ${note.label}`
    : "Handicapper's note";

  return (
    <div className={articleNumberCardClasses}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold">
        {heading}
      </p>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {note.marketNumber ? (
          <div>
            <dt className="text-xs text-kos-text/60">Market</dt>
            <dd className="mt-1 font-semibold text-kos-text">
              {note.marketNumber.replace(/\*\*/g, "")}
            </dd>
          </div>
        ) : null}
        {note.fairNumber ? (
          <div>
            <dt className="text-xs text-kos-text/60">Fair</dt>
            <dd className="mt-1 font-semibold text-kos-gold">
              {note.fairNumber.replace(/\*\*/g, "")}
            </dd>
          </div>
        ) : null}
        {note.lean ? (
          <div>
            <dt className="text-xs text-kos-text/60">Lean</dt>
            <dd className="mt-1 font-semibold text-kos-text">
              {note.lean.replace(/\*\*/g, "")}
            </dd>
          </div>
        ) : null}
        {note.confidence ? (
          <div>
            <dt className="text-xs text-kos-text/60">Confidence</dt>
            <dd className="mt-1 font-semibold text-kos-text">
              {note.confidence.replace(/\*\*/g, "")}
            </dd>
          </div>
        ) : null}
      </dl>
      {note.keyRisk ? (
        <p className="mt-4 text-sm leading-relaxed text-kos-text/85">
          <span className="font-semibold text-kos-text/70">Key risk · </span>
          {note.keyRisk.replace(/\*\*/g, "")}
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

export default function DeskHandicapArticleView({
  article,
}: DeskHandicapArticleViewProps) {
  const slots = sectionizeDeskHandicap(article.bodyMarkdown, {
    angle: article.angle,
    sources: article.sources,
  });
  const bottomLine = slots.bottomLine.replace(/\*\*/g, "");
  const sources = article.sources || slots.sources;

  return (
    <ArticleShell
      eyebrow={`KosEdge · ${article.sport} · ${article.category}`}
      title={article.title}
      date={formatArticleDate(article.publishedAt, { includeTime: true })}
      metaLine={article.bylineFull}
      bottomLine={bottomLine}
      accent="neutral"
      breadcrumbs={[
        { label: "Pro", href: "/pro/nfl/overview" },
        { label: "Desk", href: "/pro/desk" },
        { label: article.shortTitle ?? "Handicap" },
      ]}
      footerLinks={[
        { label: "← All desk handicaps", href: "/pro/desk" },
        { label: "NFL news", href: "/pro/nfl/news" },
      ]}
    >
      <ArticleSection label="Handicap" id="body">
        <ArticleProseBody source={slots.bodyMarkdown} />
      </ArticleSection>

      {sources ? (
        <ArticleSection label="Sources" id="sources">
          <ArticleProseBody source={sources} />
        </ArticleSection>
      ) : null}

      <div className="space-y-4">
        {slots.handicappersNotes.map((note, index) => (
          <HandicapperStrip
            key={`${note.label ?? "note"}-${index}`}
            note={note}
          />
        ))}
      </div>
    </ArticleShell>
  );
}
