import type { Metadata } from "next";
import { notFound } from "next/navigation";
import DeskHandicapArticleView from "@/components/articles/DeskHandicapArticle";
import { getDeskHandicap, listDeskHandicapSlugs } from "@/lib/desk-handicaps";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateStaticParams() {
  return listDeskHandicapSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = getDeskHandicap(slug);
  if (!article) {
    return { title: "Desk Handicap" };
  }
  return {
    title: article.title,
    description: article.excerpt,
    authors: [{ name: article.byline }],
    openGraph: {
      title: article.title,
      description: article.excerpt,
      type: "article",
    },
  };
}

export default async function DeskHandicapPage({ params }: PageProps) {
  const { slug } = await params;
  const article = getDeskHandicap(slug);
  if (!article) return notFound();

  return <DeskHandicapArticleView article={article} />;
}
