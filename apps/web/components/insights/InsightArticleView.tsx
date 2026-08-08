import Link from "next/link";
import type { InsightArticle, InsightBlock } from "@/lib/insights/types";
import { formatInsightDate, sportLabel } from "@/lib/insights/format";

function Blocks({ blocks }: { blocks: InsightBlock[] }) {
  return (
    <div className="space-y-3">
      {blocks.map((block, i) =>
        typeof block === "string" ? (
          <p key={i} className="leading-7 text-kos-text/85">
            {block}
          </p>
        ) : (
          <ul
            key={i}
            className="list-disc space-y-1.5 pl-5 text-kos-text/85"
          >
            {block.map((item, j) => (
              <li key={j} className="leading-6">
                {item}
              </li>
            ))}
          </ul>
        ),
      )}
    </div>
  );
}

export default function InsightArticleView({
  article,
  locked = false,
}: {
  article: InsightArticle;
  /** Pro-gated: show bottom line / teaser only. */
  locked?: boolean;
}) {
  return (
    <article className="mx-auto max-w-3xl">
      <header>
        <div className="flex flex-wrap items-center gap-2 text-xs text-kos-text/55">
          <time dateTime={article.updatedAt}>
            Updated {formatInsightDate(article.updatedAt)}
          </time>
          {article.sports?.map((s) => (
            <span
              key={s}
              className="rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 font-medium text-kos-text/70"
            >
              {sportLabel(s)}
            </span>
          ))}
          {article.tags?.slice(0, 3).map((t) => (
            <span
              key={t}
              className="rounded-md border border-white/10 px-1.5 py-0.5 text-kos-text/50"
            >
              {t}
            </span>
          ))}
        </div>

        <h1 className="mt-4 text-3xl font-extrabold leading-tight tracking-tight text-white sm:text-4xl">
          {article.title}
        </h1>
      </header>

      <section className="mt-8 rounded-2xl border border-kos-gold/30 bg-kos-gold/5 p-5">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-kos-gold">
          Bottom line
        </h2>
        <p className="mt-2 text-base leading-7 text-kos-text/95">
          {article.bottomLine}
        </p>
      </section>

      {locked ? (
        <div className="relative mt-10 overflow-hidden rounded-2xl border border-kos-border">
          <div className="select-none p-6 blur-sm pointer-events-none">
            <p className="text-kos-text/80">
              {article.teaser ??
                "Full desk note — reprice logic, thresholds, and product links — is for Pro."}
            </p>
            <ul className="mt-4 list-disc space-y-1 pl-5 text-kos-text/70">
              {article.keyPoints.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-kos-black/75 px-6 text-center">
            <p className="max-w-sm text-kos-text/90">
              Full weekly desk notes and archives are for Pro. Doctrine stays
              free.
            </p>
            <Link
              href="/pro"
              className="mt-4 inline-flex rounded-xl bg-kos-gold px-5 py-3 text-sm font-semibold text-black hover:opacity-90"
            >
              Go Pro
            </Link>
          </div>
        </div>
      ) : (
        <>
          <section className="mt-10">
            <h2 className="text-lg font-semibold text-kos-gold">Key points</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-kos-text/85">
              {article.keyPoints.map((p) => (
                <li key={p} className="leading-6">
                  {p}
                </li>
              ))}
            </ul>
          </section>

          <div className="mt-10 space-y-10">
            {article.sections.map((section) => (
              <section key={section.heading}>
                <h2 className="text-lg font-semibold text-white">
                  {section.heading}
                </h2>
                <div className="mt-3">
                  <Blocks blocks={section.blocks} />
                </div>
              </section>
            ))}
          </div>

          <section className="mt-12 rounded-2xl border border-kos-border bg-kos-surface/50 p-5">
            <h2 className="text-lg font-semibold text-kos-gold">
              What to do with this on KosEdge
            </h2>
            <ul className="mt-4 space-y-3">
              {article.whatToDo.map((item) => (
                <li
                  key={item.text}
                  className="text-sm leading-6 text-kos-text/85"
                >
                  {item.text}{" "}
                  {item.link && (
                    <Link
                      href={item.link.href}
                      className="font-semibold text-kos-gold hover:underline"
                    >
                      {item.link.label} →
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </article>
  );
}
