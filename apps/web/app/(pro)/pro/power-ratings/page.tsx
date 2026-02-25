import Link from "next/link";
import { SPORTS } from "@/lib/sports";

export default function PowerRatingsHubPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-kos-text">
            Power Ratings
          </h1>
          <p className="mt-2 text-kos-text/70">
            Team strength, rankings, and historical context by sport.
          </p>
        </div>
        <Link
          href="/pro/welcome"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          ← Pro
        </Link>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SPORTS.map((s) => (
          <Link
            key={s.key}
            href={`/pro/power-ratings/${s.key}`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6 hover:border-kos-gold/40 transition"
          >
            <h2 className="text-xl font-semibold text-kos-text">{s.fullName}</h2>
            <p className="mt-2 text-sm text-kos-text/70">{s.desc}</p>
            <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
              View ratings →
            </span>
          </Link>
        ))}
      </div>
    </main>
  );
}
