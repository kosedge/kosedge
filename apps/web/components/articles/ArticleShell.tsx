import type { ReactNode } from "react";
import Link from "next/link";
import { articleNavClasses, articleShellClasses } from "@/lib/article-prose";

export type ArticleShellBreadcrumb = {
  label: string;
  href?: string;
};

export type ArticleShellProps = {
  eyebrow?: string;
  title: string;
  date: string;
  metaLine?: string;
  bottomLine?: string;
  accent?: "gold" | "neutral";
  breadcrumbs?: ArticleShellBreadcrumb[];
  footerLinks?: Array<{ label: string; href: string }>;
  /** Optional quiet chip under the date (e.g. Editorial lineage). */
  headerExtra?: ReactNode;
  children: ReactNode;
};

export default function ArticleShell({
  eyebrow = "KosEdge",
  title,
  date,
  metaLine,
  bottomLine,
  accent = "gold",
  breadcrumbs,
  footerLinks,
  headerExtra,
  children,
}: ArticleShellProps) {
  const headerBorder =
    accent === "gold"
      ? "border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/45 to-black/70"
      : "border-white/15 bg-linear-to-br from-kos-surface/80 via-black/50 to-black/70";

  return (
    <main className={articleShellClasses.main}>
      {breadcrumbs && breadcrumbs.length > 0 ? (
        <nav className={articleNavClasses} aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, index) => (
            <span key={`${crumb.label}-${index}`} className="inline-flex items-center gap-2">
              {index > 0 ? <span aria-hidden>/</span> : null}
              {crumb.href ? (
                <Link href={crumb.href} className="hover:text-kos-gold">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-kos-text/85">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      ) : null}

      <header
        className={`rounded-3xl border p-6 sm:p-8 ${headerBorder}`}
      >
        <p className={articleShellClasses.eyebrow}>{eyebrow}</p>
        <h1 className={articleShellClasses.title}>{title}</h1>
        <p className={articleShellClasses.date}>{date}</p>
        {headerExtra ? <div className="mt-2">{headerExtra}</div> : null}
        {metaLine ? (
          <p className={articleShellClasses.meta}>{metaLine}</p>
        ) : null}
        {bottomLine ? (
          <div className={articleShellClasses.bottomLine}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold/90">
              Bottom line
            </p>
            <p className="mt-2">{bottomLine.replace(/\*\*/g, "")}</p>
          </div>
        ) : null}
      </header>

      <div className={articleShellClasses.sectionGap}>{children}</div>

      {footerLinks && footerLinks.length > 0 ? (
        <footer className={articleShellClasses.footer}>
          {footerLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 hover:border-kos-gold/35"
            >
              {link.label}
            </Link>
          ))}
        </footer>
      ) : null}
    </main>
  );
}
