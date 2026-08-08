import Link from "next/link";
import InsightsHeader from "@/components/insights/InsightsHeader";
import InsightCard from "@/components/insights/InsightCard";
import { isProUser } from "@/lib/auth/pro";
import {
  getRecentDeskNotes,
  getAllDeskNotes,
  partitionDeskNotesForUser,
} from "@/lib/insights/content";

export const metadata = {
  title: "Insights — This Week",
  description:
    "Weekly desk notes from KosEdge: market vs model, reprice logic, survivor traps, and process — free teasers and full Pro set.",
};

export default async function InsightsThisWeekPage() {
  const isPro = await isProUser();
  const recent = getRecentDeskNotes(21);
  const shelf = recent.length > 0 ? recent : getAllDeskNotes().slice(0, 6);
  const { visible, teaserOnly } = partitionDeskNotesForUser(shelf, isPro);
  const archive = isPro
    ? getAllDeskNotes().filter((n) => !shelf.some((s) => s.slug === n.slug))
    : [];

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <InsightsHeader active="this-week" />

      <div className="mt-8 flex flex-wrap gap-3 text-sm">
        <Link
          href="/edge-board"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-3 py-2 text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
        >
          Edge Board
        </Link>
        <Link
          href="/pro/kei-lines"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-3 py-2 text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
        >
          KEI Lines
        </Link>
        <Link
          href="/insights/doctrine"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-3 py-2 text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
        >
          Doctrine library
        </Link>
      </div>

      <section className="mt-10">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/50">
          Open notes
        </h2>
        <div className="mt-4 grid gap-4">
          {visible.map((article) => (
            <InsightCard key={article.slug} article={article} />
          ))}
          {visible.length === 0 && (
            <p className="text-kos-text/60">
              No open desk notes on the shelf yet. Check Doctrine while the week
              builds.
            </p>
          )}
        </div>
      </section>

      {teaserOnly.length > 0 && (
        <section className="mt-12">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/50">
              Pro desk notes
            </h2>
            <Link
              href="/pro"
              className="text-sm font-semibold text-kos-green hover:underline"
            >
              Go Pro for the full set →
            </Link>
          </div>
          <p className="mt-2 text-sm text-kos-text/60">
            Deeper &quot;why this number,&quot; reprice diaries, and archives.
            Philosophy stays free in Doctrine.
          </p>
          <div className="mt-4 grid gap-4">
            {teaserOnly.map((article) => (
              <InsightCard
                key={article.slug}
                article={article}
                teaserOnly
              />
            ))}
          </div>
        </section>
      )}

      {isPro && archive.length > 0 && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/50">
            Archive
          </h2>
          <div className="mt-4 grid gap-4">
            {archive.map((article) => (
              <InsightCard key={article.slug} article={article} />
            ))}
          </div>
        </section>
      )}

      {!isPro && (
        <section className="mt-12 rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-6">
          <h2 className="text-lg font-semibold text-kos-gold">
            Why Pro for Insights?
          </h2>
          <p className="mt-2 text-sm leading-6 text-kos-text/80">
            Doctrine teaches you how the desk thinks — free. Pro unlocks the
            ongoing weekly notes: full reprice logic, survivor trap callouts, and
            archive access tied to live boards.
          </p>
          <Link
            href="/pro"
            className="mt-4 inline-flex rounded-xl bg-kos-gold px-5 py-3 text-sm font-semibold text-black hover:opacity-90"
          >
            See Pro
          </Link>
        </section>
      )}
    </main>
  );
}
