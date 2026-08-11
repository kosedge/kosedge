import ArticleShell from "@/components/articles/ArticleShell";
import ArticleSection from "@/components/articles/ArticleSection";
import ArticleProseBody from "@/components/articles/ArticleProseBody";
import NflLineageBadge from "@/components/pro/nfl/NflLineageBadge";
import {
  articleNumberCardClasses,
} from "@/lib/article-prose";
import {
  formatPreviewDate,
  sectionizeTeamPreview,
  type HandicappersNote,
} from "@/lib/article-sectionizer";
import { editorialSnapshotLineage } from "@/lib/nfl-lineage";
import type { NflSeasonPreviewArticle } from "@/lib/nfl-season-previews";

type TeamPreviewArticleProps = {
  article: NflSeasonPreviewArticle;
};

function NumberCard({
  market,
  note,
  body,
}: {
  market: string | null;
  note: HandicappersNote;
  body: string;
}) {
  const fair = note.fairNumber ?? null;
  const lean = note.lean ?? null;
  const marketNum = note.marketNumber ?? market;

  if (!fair && !marketNum && !lean && !body.trim()) return null;

  return (
    <div className={articleNumberCardClasses}>
      <dl className="grid gap-3 sm:grid-cols-3">
        {marketNum ? (
          <div>
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/60">
              Market
            </dt>
            <dd className="mt-1 text-lg font-semibold text-kos-text">{marketNum}</dd>
          </div>
        ) : null}
        {fair ? (
          <div>
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/60">
              Fair range
            </dt>
            <dd className="mt-1 text-lg font-semibold text-kos-gold">{fair}</dd>
          </div>
        ) : null}
        {lean ? (
          <div>
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/60">
              Lean
            </dt>
            <dd className="mt-1 text-lg font-semibold text-kos-text">{lean}</dd>
          </div>
        ) : null}
      </dl>
      {body.trim() ? (
        <div className="mt-5 border-t border-white/10 pt-5">
          <ArticleProseBody source={body} />
        </div>
      ) : null}
    </div>
  );
}

function ModelNote({ note }: { note: HandicappersNote }) {
  if (!note.raw && !note.disclaimer) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-kos-surface/40 p-5 sm:p-6">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold">
        Model note
      </p>
      {note.raw ? (
        <dl className="mt-4 space-y-3 text-sm text-kos-text/90">
          {note.confidence ? (
            <div className="flex flex-wrap gap-x-2">
              <dt className="font-semibold text-kos-text/70">Confidence</dt>
              <dd>{note.confidence}</dd>
            </div>
          ) : null}
          {note.keyRisk ? (
            <div>
              <dt className="font-semibold text-kos-text/70">Key risk</dt>
              <dd className="mt-1 leading-relaxed">{note.keyRisk}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {note.disclaimer ? (
        <p className="mt-4 text-xs leading-relaxed text-kos-text/55">
          {note.disclaimer}
        </p>
      ) : null}
    </div>
  );
}

export default function TeamPreviewArticle({ article }: TeamPreviewArticleProps) {
  const slots = sectionizeTeamPreview(article.bodyMarkdown);
  const bottomLine =
    article.angle?.replace(/\*\*/g, "") ||
    slots.bottomLine.replace(/\*\*/g, "");
  const published = formatPreviewDate(article.publishedDate);

  const sections: Array<{
    label: string;
    title?: string;
    content: string;
    id: string;
  }> = [
    {
      id: "the-number",
      label: "The number",
      content: slots.theNumber,
    },
    {
      id: "quick-projection",
      label: "Quick projection",
      title: "Division outlook & profile",
      content: slots.quickProjection,
    },
    {
      id: "roster-snapshot",
      label: "Roster snapshot",
      content: slots.rosterSnapshot,
    },
    {
      id: "what-matters",
      label: "What matters most",
      content: slots.whatMattersMost,
    },
    {
      id: "schedule",
      label: "Schedule / path notes",
      content: slots.scheduleNotes,
    },
    {
      id: "betting-angles",
      label: "Betting angles to track",
      content: slots.bettingAngles,
    },
    {
      id: "what-would-change",
      label: "What would change this view",
      content: slots.whatWouldChange,
    },
    {
      id: "additional-context",
      label: "Additional context",
      content: slots.remainingBody,
    },
  ].filter((section) => section.content.trim());

  return (
    <ArticleShell
      eyebrow={`KosEdge${article.desk ? ` · ${article.desk}` : ""}`}
      title={article.title}
      date={published}
      metaLine={`2026 season preview · ${article.wordCount.toLocaleString()} words`}
      headerExtra={
        <NflLineageBadge
          lineage={editorialSnapshotLineage(article.publishedDate)}
        />
      }
      bottomLine={bottomLine}
      breadcrumbs={[
        { label: "NFL Overview", href: "/pro/nfl/overview" },
        { label: "Season Previews", href: "/pro/nfl/previews" },
        { label: article.team },
      ]}
      footerLinks={[
        { label: "← All 32 previews", href: "/pro/nfl/previews" },
        {
          label: "Team research hub",
          href: `/pro/nfl/teams/${article.team}/overview`,
        },
        { label: "Futures / projections", href: "/pro/nfl/projections" },
      ]}
    >
      <ArticleSection label="The number" id="the-number-top">
        <NumberCard
          market={article.market}
          note={slots.handicappersNote}
          body={slots.theNumber}
        />
      </ArticleSection>

      {sections
        .filter((s) => s.id !== "the-number")
        .map((section) => (
          <ArticleSection
            key={section.id}
            id={section.id}
            label={section.label}
            title={section.title}
          >
            <ArticleProseBody source={section.content} />
          </ArticleSection>
        ))}

      {article.sources ? (
        <ArticleSection label="Sources" id="sources">
          <p className="text-sm leading-relaxed text-kos-text/80">
            {article.sources}
          </p>
        </ArticleSection>
      ) : null}

      <ModelNote note={slots.handicappersNote} />
    </ArticleShell>
  );
}
