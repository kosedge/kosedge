/** Shared typography + layout classes for KosEdge long-form articles (dark theme). */
export const ARTICLE_MAX_WIDTH = "max-w-[42rem]";

export const articleShellClasses = {
  main: `mx-auto ${ARTICLE_MAX_WIDTH} px-4 py-8 sm:px-6 sm:py-10`,
  eyebrow:
    "text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold",
  title:
    "mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-[2.125rem] sm:leading-tight",
  date: "mt-3 text-sm text-kos-text/80",
  meta: "mt-1 text-xs text-kos-text/60",
  headerCard:
    "rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/45 to-black/70 p-6 sm:p-8",
  bottomLine:
    "mt-5 rounded-xl border border-white/10 bg-black/30 px-4 py-4 text-[0.9375rem] leading-relaxed text-kos-text/95 sm:text-base",
  sectionGap: "mt-10 space-y-10",
  sectionTitle:
    "text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold",
  sectionHeading:
    "mt-2 text-xl font-semibold tracking-tight text-kos-text sm:text-[1.375rem]",
  footer: "mt-12 flex flex-wrap gap-3 border-t border-white/10 pt-8 text-sm",
} as const;

/** Tailwind Typography plugin modifiers tuned for mobile readability on kos-black. */
export const articleProseClasses = [
  "kos-article-prose",
  "prose prose-invert max-w-none",
  "prose-p:text-[0.9375rem] prose-p:leading-[1.75] prose-p:text-kos-text/90",
  "prose-p:my-4 sm:prose-p:text-base",
  "prose-headings:tracking-tight prose-headings:text-kos-text",
  "prose-h2:mt-10 prose-h2:mb-4 prose-h2:text-xl prose-h2:font-semibold sm:prose-h2:text-[1.375rem]",
  "prose-h3:mt-8 prose-h3:mb-3 prose-h3:text-lg prose-h3:font-semibold",
  "prose-strong:text-kos-text prose-strong:font-semibold",
  "prose-a:text-kos-gold prose-a:underline-offset-2 hover:prose-a:text-kos-gold/90",
  "prose-li:text-kos-text/90 prose-li:leading-relaxed prose-li:my-1.5",
  "prose-ul:my-4 prose-ol:my-4",
  "prose-blockquote:border-kos-gold/35 prose-blockquote:text-kos-text/85",
  "prose-table:my-0 prose-table:w-full",
  "prose-th:border-white/15 prose-th:px-3 prose-th:py-2.5",
  "prose-td:border-white/10 prose-td:px-3 prose-td:py-2.5",
].join(" ");

export const articleNavClasses =
  "mb-5 flex flex-wrap items-center gap-2 text-xs text-kos-text/70";

export const articleKeyPointsClasses =
  "mt-4 space-y-2 rounded-xl border border-white/10 bg-kos-surface/50 px-4 py-4 sm:px-5";

export const articleNumberCardClasses =
  "rounded-2xl border border-kos-gold/30 bg-kos-surface/60 p-5 sm:p-6";
