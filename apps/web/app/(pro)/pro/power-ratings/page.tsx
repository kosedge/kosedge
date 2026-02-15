import Link from "next/link";

export default function PowerRatingsPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-kos-text">Power Ratings</h1>
          <p className="mt-2 text-kos-text/70">
            Team strength, updates, and historical context.
          </p>
        </div>
        <Link
          href="/pro/welcome"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          ← Pro
        </Link>
      </div>
      <div className="mt-8 rounded-2xl border border-kos-border bg-kos-surface/30 p-8">
        <p className="text-kos-text/60">Shell placeholder. Wire power ratings.</p>
      </div>
    </main>
  );
}
