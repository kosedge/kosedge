import type { Metadata } from "next";
import { notFound } from "next/navigation";
import NewsUpdateArticle from "@/components/articles/NewsUpdateArticle";
import {
  getNflNewsUpdate,
  listNflNewsUpdateSlugs,
} from "@/lib/nfl-news-updates";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateStaticParams() {
  return listNflNewsUpdateSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = getNflNewsUpdate(slug);
  if (!article) {
    return { title: "NFL News Update" };
  }
  return {
    title: article.title,
    description: article.excerpt,
    openGraph: {
      title: article.title,
      description: article.excerpt,
      type: "article",
    },
  };
}

export default async function NflNewsUpdatePage({ params }: PageProps) {
  const { slug } = await params;
  const article = getNflNewsUpdate(slug);
  if (!article) return notFound();

  return <NewsUpdateArticle article={article} />;
}
