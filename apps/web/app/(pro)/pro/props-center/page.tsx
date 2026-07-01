import Link from "next/link";
import { SPORTS } from "@/lib/sports";

export default function PropsCenterPage() {
  const proSports = SPORTS.filter((sport) => sport.supportsPropsFantasy);
  const collegeSports = SPORTS.filter((sport) => !sport.supportsPropsFantasy);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link
        href="/pro/welcome"
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold mb-6"
      >
        ← Pro
      </Link>
      <h1 className="text-3xl font-semibold text-kos-text">Props Center</h1>
      <p className="mt-2 text-kos-text/70">
        Cross-sport props and fantasy tools for launch-ready pro leagues.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {proSports.map((s) => (
          <Link
            key={s.key}
            href={`/pro/${s.key}/props`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-5 hover:border-kos-gold/40 transition"
          >
            <h3 className="font-semibold text-kos-text">{s.fullName} Props</h3>
            <p className="mt-2 text-sm text-kos-text/70">
              Player props and fantasy-ready dashboards
            </p>
          </Link>
        ))}
      </div>
      <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-5 text-sm text-kos-text/75">
        <p className="font-semibold text-kos-text">College rollout status</p>
        <p className="mt-2">
          Props and fantasy pathways for{" "}
          {collegeSports.map((sport) => sport.fullName).join(" and ")} remain in
          premium placeholder mode until player-level feeds pass launch checks.
        </p>
      </div>
    </main>
  );
}
