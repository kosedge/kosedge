import Link from "next/link";
import { SPORTS } from "@/lib/sports";

export default function PropsHubPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-kos-text">Props</h1>
          <p className="mt-2 text-kos-text/70">
            Prop analyzer and edge screens. Player props, team props, alternates.
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
