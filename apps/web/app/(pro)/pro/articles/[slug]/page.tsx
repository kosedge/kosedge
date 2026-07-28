import Link from "next/link";
import { notFound } from "next/navigation";
import { HIGHLIGHTED_GAMES } from "@/lib/featured-games";

export default async function GameArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const game = HIGHLIGHTED_GAMES.find((g) => g.slug === slug);
  if (!game) return notFound();

  const title = `${game.row.teamA.name} vs ${game.row.teamB.name}`;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link
        href="/pro/welcome"
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold mb-6"
      >
        ← Pro
      </Link>
      <h1 className="text-3xl font-semibold text-kos-text">{title}</h1>
      <p className="mt-2 text-kos-text/70">
        Game breakdown, model take, and workflow. Article content coming soon.
      </p>
      <div className="mt-8 rounded-xl border border-kos-border bg-kos-surface/40 p-6">
        <h2 className="text-lg font-medium text-kos-text">Edge snapshot</h2>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-kos-text/60">Best Line</div>
            <div className="text-kos-gold font-medium">
              {game.row.bestLine.top.label}
            </div>
          </div>
          <div>
            <div className="text-kos-text/60">Best O/U</div>
            <div className="text-kos-gold font-medium">
              {game.row.bestOU.top.label}
            </div>
          </div>
          <div>
            <div className="text-kos-text/60">Open Line</div>
            <div>{game.row.openLine.top.label}</div>
          </div>
          <div>
            <div className="text-kos-text/60">Time</div>
            <div>{game.row.time ?? "—"}</div>
          </div>
        </div>
      </div>
    </main>
  );
}
