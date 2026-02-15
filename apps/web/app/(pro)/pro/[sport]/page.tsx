import Link from "next/link";

const sports = [
  { key: "cbb", label: "College Basketball", desc: "Daily slate, fair lines, matchup context, execution." },
  { key: "nfl", label: "NFL", desc: "Weekly slate and matchup pages (in-season)." },
  { key: "nba", label: "NBA", desc: "Daily slate and execution tooling." },
  { key: "mlb", label: "MLB", desc: "Daily slate, markets, and tracking." },
];

export default function ProHubLanding() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-4xl font-semibold tracking-tight text-kos-text">Pro Betting Hub</h1>
      <p className="mt-3 max-w-2xl text-kos-text/80">
        Sport-specific hubs designed for information, execution quality, and long-term review. No picks. No hype.
      </p>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {sports.map((s) => (
          <Link
            key={s.key}
            href={`/pro/${s.key}`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6 hover:border-kos-gold/40"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">{s.label}</h2>
              <span className="text-sm text-kos-text/60">Enter</span>
            </div>
            <p className="mt-2 text-kos-text/80">{s.desc}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}