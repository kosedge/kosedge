import Link from "next/link";
import InsightsHeader from "@/components/insights/InsightsHeader";
import { getSportsWithInsights } from "@/lib/insights/content";

export const metadata = {
  title: "Insights — By Sport",
  description:
    "Filter KosEdge Insights by sport — desk notes and doctrine where content exists.",
};

export default function InsightsSportsPage() {
  const sports = getSportsWithInsights();

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <InsightsHeader active="sports" />

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {sports.map((s) => (
          <Link
            key={s.key}
            href={`/insights/sports/${s.key}`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-5 transition hover:border-kos-gold/40"
          >
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-xl font-semibold text-kos-gold">{s.label}</h2>
              <span className="text-xs text-kos-text/50">
                {s.noteCount} note{s.noteCount === 1 ? "" : "s"}
                {s.doctrineCount > 0
                  ? ` · ${s.doctrineCount} doctrine`
                  : ""}
              </span>
            </div>
            <p className="mt-2 text-sm text-kos-text/70">{s.fullName}</p>
          </Link>
        ))}
      </div>

      {sports.length === 0 && (
        <p className="mt-8 text-kos-text/60">
          No sport-tagged insights yet. Check This Week and Doctrine.
        </p>
      )}

      <p className="mt-10 text-sm text-kos-text/55">
        Prefer live numbers?{" "}
        <Link href="/edge-board" className="text-kos-gold hover:underline">
          Edge Board
        </Link>{" "}
        ·{" "}
        <Link href="/pro" className="text-kos-gold hover:underline">
          Pro hubs
        </Link>
      </p>
    </main>
  );
}
