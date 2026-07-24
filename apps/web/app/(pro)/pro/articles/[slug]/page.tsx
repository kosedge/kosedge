import Link from "next/link";
import { notFound } from "next/navigation";
import { HIGHLIGHTED_GAMES } from "@/lib/featured-games";
import { getGameBySlug } from "@/lib/edge-board-tonight";
import { buildProArticleContent } from "@/lib/pro-article-content";
import { getSport } from "@/lib/sports";

function toSportLabel(sport: string): string {
  return getSport(sport)?.fullName ?? sport.toUpperCase();
}

export default async function GameArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let game = HIGHLIGHTED_GAMES.find((g) => g.slug === slug);
  if (!game) {
    const tonight = await getGameBySlug(slug);
    if (tonight) game = { slug, row: tonight.row, sport: tonight.sport };
  }
  if (!game) return notFound();

  const sportLabel = toSportLabel(game.sport);
  const content = buildProArticleContent({ sport: game.sport, row: game.row });
  const title = `${game.row.teamA.name} vs ${game.row.teamB.name}`;
  const confidenceTone =
    content.mode === "placeholder"
      ? "Premium data pending"
      : game.row.edgeLineNum != null || game.row.edgeOUNum != null
        ? "Model-backed confidence"
        : "Evidence still building";

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
      <Link
        href={`/pro/${game.sport}/overview`}
        className="mb-6 inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold"
      >
        ← Back to {sportLabel} overview
      </Link>

      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/40 to-black/60 p-6 shadow-xl backdrop-blur-xl sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
          {sportLabel} matchup brief
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-kos-text/80 sm:text-base">
          {content.mode === "placeholder"
            ? "Premium placeholder briefing. Market and matchup intelligence publish after feed validation finishes for this game."
            : "Professional preview focused on market context, model separation, and practical risk controls. This brief is informational and execution oriented."}
        </p>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl">
          <h2 className="text-lg font-semibold text-kos-text">
            Market Context
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {content.marketContext}
          </p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl">
          <h2 className="text-lg font-semibold text-kos-text">Model Edge</h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {content.modelEdge}
          </p>
        </article>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl">
          <h2 className="text-lg font-semibold text-kos-text">
            Matchup Drivers
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-kos-text/80">
            {content.matchupDrivers.map((driver) => (
              <li key={driver} className="flex gap-2">
                <span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-kos-gold" />
                <span>{driver}</span>
              </li>
            ))}
          </ul>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl">
          <h2 className="text-lg font-semibold text-kos-text">Risk Factors</h2>
          <ul className="mt-3 space-y-2 text-sm text-kos-text/80">
            {content.riskFactors.map((risk) => (
              <li key={risk} className="flex gap-2">
                <span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-kos-green" />
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-kos-gold/20 bg-kos-gold/6 p-5 backdrop-blur-xl">
        <h2 className="text-lg font-semibold text-kos-gold">
          {confidenceTone}
        </h2>
        <p className="mt-2 text-sm text-kos-text/85">{content.confidence}</p>
      </section>

      <section className="mt-6 rounded-xl border border-kos-border bg-kos-surface/40 p-6">
        <h2 className="text-lg font-medium text-kos-text">Edge Snapshot</h2>
        <div className="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <div className="text-kos-text/60">Best Line</div>
            <div className="text-kos-gold font-medium">
              {game.row.bestLine.top.label || "Pending"}
            </div>
          </div>
          <div>
            <div className="text-kos-text/60">Best O/U</div>
            <div className="text-kos-gold font-medium">
              {game.row.bestOU.top.label || "Pending"}
            </div>
          </div>
          <div>
            <div className="text-kos-text/60">Open Line</div>
            <div>{game.row.openLine.top.label || "Pending"}</div>
          </div>
          <div>
            <div className="text-kos-text/60">Time</div>
            <div>{game.row.time ?? "—"}</div>
          </div>
        </div>
      </section>
    </main>
  );
}
