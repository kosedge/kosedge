import type { Metadata } from "next";
import Link from "next/link";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL mock drafts are over",
  description: "Draft season is over. This week's DFS slate is live.",
};

/** In-season: hide the mock room. Engine stays in-repo; landing is DFS. */
export default function NflFantasyMockHiddenPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
        Fantasy · in-season
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
        Drafts are over — DFS is live
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-kos-text/75">
        Mock draft rooms are parked for the regular season. This week&apos;s DFS
        slate is the Fantasy landing.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href="/pro/nfl/dfs"
          className="inline-flex min-h-11 items-center rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/60"
        >
          Open this week&apos;s DFS →
        </Link>
        <Link
          href="/pro/nfl/weekly-fantasy"
          className="inline-flex min-h-11 items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
        >
          Weekly Fantasy
        </Link>
      </div>
    </main>
  );
}
