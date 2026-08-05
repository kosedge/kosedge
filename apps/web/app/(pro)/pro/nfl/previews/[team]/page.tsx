import type { Metadata } from "next";
import { notFound } from "next/navigation";
import TeamPreviewArticle from "@/components/articles/TeamPreviewArticle";
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
      `${article.teamName} 2026 season preview from KosEdge.`,
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

  return <TeamPreviewArticle article={article} />;
}
