import Link from "next/link";
import { getSport } from "@/lib/sports";

const SHELL_LINKS = [
  { href: "fair-lines", label: "Fair Lines", desc: "Model reference vs market. Neutral presentation." },
  { href: "slate/today", label: "Slate", desc: "Daily/weekly games with matchup context." },
  { href: "teams", label: "Teams", desc: "Team summaries, power ratings." },
  { href: "tracking", label: "Tracking", desc: "CLV, review dashboards." },
  { href: "exicution", label: "Execution", desc: "Best numbers by book, dispersion." },
  { href: "props", label: "Props", desc: "Prop analyzer and edge screens." },
];

const KEICMB_LINKS = [
  { href: "keicmb-lines", label: "KEICMB Lines", desc: "Kos Edge Index CBB · Our spread & over/under lines for today's games." },
  { href: "keicmb-rankings", label: "KEICMB Rankings", desc: "Team rankings 1–350 from our model (adjem, Torvik, ensemble)." },
];

export default function SportOverviewPage({ params }: { params: { sport: string } }) {
  const sport = getSport(params.sport);
  const sportName = sport?.fullName ?? params.sport.toUpperCase();
  const base = `/pro/${params.sport}`;
  const edgeBoardHref = `/edge-board/${params.sport}`;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
          {sportName} Hub
        </h1>
        <p className="mt-2 text-kos-text/80">
          Sport-specific information, fair lines, and execution support. No picks. No hype.
        </p>
      </div>

      {/* Edge Board CTA */}
      <Link
        href={edgeBoardHref}
        className="mb-8 block rounded-2xl border border-kos-gold/30 bg-kos-gold/5 p-6 hover:border-kos-gold/50 hover:bg-kos-gold/10 transition"
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-kos-gold">Edge Board</h2>
            <p className="mt-1 text-sm text-kos-text/80">
              Today&apos;s slate · Open vs Best · Model reference (coming)
            </p>
          </div>
          <span className="text-kos-gold">→</span>
        </div>
      </Link>

      {/* Shell nav cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SHELL_LINKS.map((l) => (
          <Link
            key={l.href}
            href={`${base}/${l.href}`}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-5 hover:border-kos-gold/40 transition"
          >
            <h3 className="font-semibold text-kos-text">{l.label}</h3>
            <p className="mt-2 text-sm text-kos-text/70">{l.desc}</p>
          </Link>
        ))}
      </div>

      <p className="mt-8 text-sm text-kos-text/50">
        Placeholder shells. Wire model and content when ready.
      </p>
    </main>
  );
}
