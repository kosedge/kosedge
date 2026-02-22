import Link from "next/link";
import { getSport } from "@/lib/sports";
import { HIGHLIGHTED_GAMES, TOP_EDGE } from "@/lib/featured-games";
import EdgeBoardPreview from "@/components/EdgeBoardPreview";

const SHELL_LINKS = [
  {
    href: "fair-lines",
    label: "Fair Lines",
    desc: "Model reference vs market. Neutral presentation.",
  },
  {
    href: "slate/today",
    label: "Slate",
    desc: "Daily/weekly games with matchup context.",
  },
  { href: "teams", label: "Teams", desc: "Team summaries, power ratings." },
  { href: "tracking", label: "Tracking", desc: "CLV, review dashboards." },
  {
    href: "execution",
    label: "Execution",
    desc: "Best numbers by book, dispersion.",
  },
  { href: "props", label: "Props", desc: "Prop analyzer and edge screens." },
];

export default async function SportOverviewPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;
  const edgeBoardHref = `/edge-board/${sportKey}`;

  const sportGames = HIGHLIGHTED_GAMES.filter((g) => g.sport === sportKey);
  const topEdgeForSport = TOP_EDGE.sport === sportKey ? TOP_EDGE : null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
          {sportName} Hub
        </h1>
        <p className="mt-2 text-kos-text/80">
          Sport-specific information, fair lines, and execution support. No
          picks. No hype.
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

      {/* Featured game articles */}
      {(topEdgeForSport || sportGames.length > 0) && (
        <div className="mb-8">
          <h2 className="text-lg font-bebas text-kos-gold tracking-wide mb-4">
            Featured Game Articles
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topEdgeForSport && (
              <EdgeBoardPreview
                key={topEdgeForSport.slug}
                row={topEdgeForSport.row}
                articleHref={`/pro/articles/${topEdgeForSport.slug}`}
              />
            )}
            {sportGames
              .filter((g) => g.slug !== topEdgeForSport?.slug)
              .map((g) => (
                <EdgeBoardPreview
                  key={g.slug}
                  row={g.row}
                  articleHref={`/pro/articles/${g.slug}`}
                />
              ))}
          </div>
        </div>
      )}

      {/* Power Ratings + KEI */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <Link
          href={`/pro/power-ratings/${sportKey}`}
          className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-6 hover:border-kos-gold/45 hover:bg-kos-gold/10 transition"
        >
          <h2 className="text-xl font-semibold text-kos-gold">Power Ratings</h2>
          <p className="mt-2 text-sm text-kos-text/80">
            Team strength, rankings, and historical context by sport.
          </p>
          <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
            View ratings →
          </span>
        </Link>
        <Link
          href={`/pro/kei-lines/${sportKey}`}
          className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6 hover:border-kos-gold/40 transition"
        >
          <h2 className="text-xl font-semibold text-kos-text">KEI Lines</h2>
          <p className="mt-2 text-sm text-kos-text/70">
            Our projected spread and over/under for today&apos;s games.
          </p>
          <span className="mt-4 inline-block text-sm font-semibold text-kos-gold">
            View lines →
          </span>
        </Link>
      </div>

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
    </main>
  );
}
