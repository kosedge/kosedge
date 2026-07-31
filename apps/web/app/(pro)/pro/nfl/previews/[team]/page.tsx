import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import { useMDXComponents } from "@/mdx-components";
import {
  getNflSeasonPreview,
  listNflSeasonPreviewTeams,
} from "@/lib/nfl-season-previews";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ team: string }>;
};

export async function generateStaticParams() {
  return listNflSeasonPreviewTeams().map((team) => ({ team }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { team } = await params;
  const article = getNflSeasonPreview(team);
  if (!article) {
    return { title: "NFL Season Preview" };
  }
  return {
    title: article.title,
    description:
      article.angle ??
      `${article.teamName} 2026 season preview by ${article.author}.`,
    openGraph: {
      title: article.title,
      description: article.angle ?? article.excerpt,
      type: "article",
    },
  };
}

export default async function NflSeasonPreviewArticlePage({
  params,
}: PageProps) {
  const { team } = await params;
  const article = getNflSeasonPreview(team);
  if (!article) return notFound();
  const components = useMDXComponents({});

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-5 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/nfl/overview" className="hover:text-kos-gold">
          NFL Overview
        </Link>
        <span>/</span>
        <Link href="/pro/nfl/previews" className="hover:text-kos-gold">
          Season Previews
        </Link>
        <span>/</span>
        <span className="text-kos-text">{article.team}</span>
      </nav>

      <header className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/45 to-black/70 p-6 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          Kos Edge Analytics
          {article.desk ? ` · ${article.desk}` : ""}
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
          {article.title}
        </h1>
        <p className="mt-3 text-sm text-kos-text/75">
          By <span className="text-kos-text">{article.author}</span>
          {" · "}
          {article.wordCount.toLocaleString()} words
        </p>
        {article.angle ? (
          <p className="mt-4 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm leading-relaxed text-kos-text/90">
            <span className="font-semibold text-kos-gold">Angle · </span>
            {article.angle}
          </p>
        ) : null}
        {article.market ? (
          <p className="mt-3 text-xs text-kos-text/60">
            Market · {article.market}
          </p>
        ) : null}
      </header>

      <article className="prose prose-invert mt-8 max-w-none prose-headings:tracking-tight prose-a:text-kos-gold prose-strong:text-kos-text prose-td:border-white/10 prose-th:border-white/15">
        <MDXRemote source={article.bodyMarkdown} components={components} />
      </article>

      <footer className="mt-10 flex flex-wrap gap-3 border-t border-white/10 pt-6 text-sm">
        <Link
          href="/pro/nfl/previews"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 hover:border-kos-gold/40"
        >
          ← All 32 previews
        </Link>
        <Link
          href={`/pro/nfl/teams/${article.team}/overview`}
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 hover:border-kos-gold/35"
        >
          Team research hub
        </Link>
        <Link
          href="/pro/nfl/projections"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 hover:border-kos-gold/35"
        >
          Futures / projections
        </Link>
      </footer>
    </main>
  );
}
