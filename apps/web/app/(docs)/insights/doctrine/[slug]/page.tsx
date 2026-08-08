import Link from "next/link";
import { notFound } from "next/navigation";
import InsightArticleView from "@/components/insights/InsightArticleView";
import {
  getDoctrineArticles,
  getDoctrineBySlug,
} from "@/lib/insights/content";

export function generateStaticParams() {
  return getDoctrineArticles().map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getDoctrineBySlug(slug);
  if (!article) return { title: "Doctrine" };
  return {
    title: `${article.title} — Doctrine`,
    description: article.bottomLine,
  };
}

export default async function DoctrineArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getDoctrineBySlug(slug);
  if (!article) return notFound();

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <Link
        href="/insights/doctrine"
        className="text-sm font-medium text-kos-text/60 hover:text-kos-gold"
      >
        ← Doctrine
      </Link>
      <div className="mt-8">
        <InsightArticleView article={article} />
      </div>
    </main>
  );
}
