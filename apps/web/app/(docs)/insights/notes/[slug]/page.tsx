import Link from "next/link";
import { notFound } from "next/navigation";
import InsightArticleView from "@/components/insights/InsightArticleView";
import { isProUser } from "@/lib/auth/pro";
import {
  canReadFullArticle,
  getAllDeskNotes,
  getDeskNoteBySlug,
} from "@/lib/insights/content";

export function generateStaticParams() {
  return getAllDeskNotes().map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getDeskNoteBySlug(slug);
  if (!article) return { title: "Desk note" };
  return {
    title: `${article.title} — Insights`,
    description: article.bottomLine,
  };
}

export default async function DeskNotePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getDeskNoteBySlug(slug);
  if (!article) return notFound();

  const isPro = await isProUser();
  const locked = !canReadFullArticle(article, isPro);

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <Link
        href="/insights"
        className="text-sm font-medium text-kos-text/60 hover:text-kos-gold"
      >
        ← This Week
      </Link>
      <div className="mt-8">
        <InsightArticleView article={article} locked={locked} />
      </div>
    </main>
  );
}
