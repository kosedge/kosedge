import Link from "next/link";
import { notFound } from "next/navigation";
import InsightsHeader from "@/components/insights/InsightsHeader";
import InsightCard from "@/components/insights/InsightCard";
import { isEntitledProUser } from "@/lib/auth/pro";
import { getSport } from "@/lib/sports";
import {
  getDeskNotesBySport,
  getDoctrineArticles,
  partitionDeskNotesForUser,
} from "@/lib/insights/content";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  if (!sport) return { title: "Insights" };
  return {
    title: `${sport.label} Insights`,
    description: `KosEdge desk notes and doctrine for ${sport.fullName}.`,
  };
}

export default async function InsightsSportPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  if (!sport) return notFound();

  const isPro = await isEntitledProUser();
  const notes = getDeskNotesBySport(sportKey);
  const doctrine = getDoctrineArticles().filter((d) =>
    d.sports?.includes(sport.key),
  );
  const { visible, teaserOnly } = partitionDeskNotesForUser(notes, isPro);
  const hasContent = notes.length > 0 || doctrine.length > 0;

  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 sm:py-14">
      <InsightsHeader active="sports" />

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">
            {sport.label}{" "}
            <span className="text-kos-text/50 font-normal">
              · {sport.fullName}
            </span>
          </h2>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <Link
            href={`/edge-board/${sport.key}`}
            className="rounded-xl border border-kos-border px-3 py-1.5 text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
          >
            Edge Board
          </Link>
          <Link
            href={`/pro/${sport.key}/overview`}
            className="rounded-xl border border-kos-border px-3 py-1.5 text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
          >
            {sport.label} Hub
          </Link>
        </div>
      </div>

      {!hasContent && (
        <p className="mt-10 text-kos-text/65 leading-7">
          No {sport.label}-tagged desk notes yet. Cross-sport{" "}
          <Link
            href="/insights/doctrine"
            className="text-kos-gold hover:underline"
          >
            Doctrine
          </Link>{" "}
          still applies — and the live board is the source of numbers.
        </p>
      )}

      {visible.length + teaserOnly.length > 0 && (
        <section className="mt-10">
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/50">
            Desk notes
          </h3>
          <div className="mt-4 grid gap-4">
            {visible.map((a) => (
              <InsightCard key={a.slug} article={a} />
            ))}
            {teaserOnly.map((a) => (
              <InsightCard key={a.slug} article={a} teaserOnly />
            ))}
          </div>
        </section>
      )}

      {doctrine.length > 0 && (
        <section className="mt-12">
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/50">
            Related doctrine
          </h3>
          <div className="mt-4 grid gap-4">
            {doctrine.map((a) => (
              <InsightCard key={a.slug} article={a} />
            ))}
          </div>
        </section>
      )}

      <p className="mt-10">
        <Link
          href="/insights/sports"
          className="text-sm text-kos-text/60 hover:text-kos-gold"
        >
          ← All sports
        </Link>
      </p>
    </main>
  );
}
