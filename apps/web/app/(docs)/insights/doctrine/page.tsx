import InsightsHeader from "@/components/insights/InsightsHeader";
import InsightCard from "@/components/insights/InsightCard";
import { getDoctrineArticles } from "@/lib/insights/content";

export const metadata = {
  title: "Insights — Doctrine",
  description:
    "KosEdge house rules: fair-first process, thresholds, CLV as diagnostic, bankroll, and more. Free philosophy for the desk.",
};

export default function DoctrineLibraryPage() {
  const articles = getDoctrineArticles();

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <InsightsHeader active="doctrine" />

      <p className="mt-8 text-sm text-kos-text/60">
        {articles.length} pillars · updated for the live desk · no public module
        numbers
      </p>

      <div className="mt-6 grid gap-4">
        {articles.map((article) => (
          <InsightCard key={article.slug} article={article} />
        ))}
      </div>
    </main>
  );
}
