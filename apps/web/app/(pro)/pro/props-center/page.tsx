import Link from "next/link";
import { SPORTS } from "@/lib/sports";

export default function PropsCenterPage() {
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
        Prop analyzer and edge screens. Player props, team props, alternates.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SPORTS.map((s) => (
          <Link
            key={s.key}
            href={`/pro/${s.key}/props`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-5 hover:border-kos-gold/40 transition"
          >
            <h3 className="font-semibold text-kos-text">{s.fullName} Props</h3>
            <p className="mt-2 text-sm text-kos-text/70">Prop analyzer and edge screens</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
