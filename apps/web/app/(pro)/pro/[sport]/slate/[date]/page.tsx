import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

function formatMarket(game: Awaited<ReturnType<typeof getTonightGames>>[number]) {
  const line =
    game.row.bestLine?.top?.label ?? game.row.keiLine?.top?.label ?? "—";
  const total =
    game.row.bestOU?.top?.label ?? game.row.keiOU?.top?.label ?? "—";
  return `${line} · ${total}`;
}

function formatModel(game: Awaited<ReturnType<typeof getTonightGames>>[number]) {
  const line = game.row.keiLine?.top?.label ?? "—";
  const total = game.row.keiOU?.top?.label ?? "—";
  return `${line} · ${total}`;
}

function contextBlurb(sportKey: string): string {
  switch (sportKey) {
    case "cfb":
      return "Weekly framing: tempo, havoc, and key-number context beside model vs market.";
    case "ncaam":
      return "Daily framing: tempo, variance, and conference efficiency beside model vs market.";
    case "mlb":
      return "Daily framing: SP, bullpen, park factors, ML / run line / totals.";
    case "nhl":
      return "Daily framing: goalie confirmation sensitivity for ML, totals, and puck line.";
    case "nba":
      return "Daily framing: pace, rest, and availability before props research.";
    case "wnba":
      return "Daily framing: usage, travel, rest, and pace before props research.";
    default:
      return "Model vs market slate cards for research — not a picks feed.";
  }
}

export default async function SlatePage({
  params,
}: {
  params: Promise<{ sport: string; date: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const date = String(resolved?.date ?? "today");

  if (sportKey === "nfl") {
    redirect(`/pro/nfl/slate/${date || "today"}`);
  }
  if (sportKey === "cfb") {
    redirect(date === "1" ? "/pro/cfb/slate?week=1" : "/pro/cfb/slate");
  }

  const base = `/pro/${sportKey || "nfl"}`;
  const sportName = sportDisplayLabel(sportKey);
  const isWeekly = sportKey === "cfb";
  const slateLabel = isWeekly ? "Weekly Slate" : "Daily Slate";
  const games = await getTonightGames(sportKey);

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} · ${slateLabel} · ET`}
      title={`${sportName} ${slateLabel}`}
      summary={`${contextBlurb(sportKey)} Date: ${date}. You make the picks.`}
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Edge board →"
      secondaryHref={`${base}/fair-lines`}
      secondaryLabel="KEI Lines →"
    >
      {games.length === 0 ? (
        <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6">
          <p className="text-sm font-semibold text-kos-gold">
            No live slate rows yet
          </p>
          <p className="mt-2 text-sm text-kos-text/70">
            When books and KEI lines post for this sport, matchup cards appear
            here. We do not invent sample games. Use Edge Board and Compare Odds
            for market scanning in the meantime.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href={`/edge-board/${sportKey}`}
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold"
            >
              Edge Board
            </Link>
            <Link
              href={`/odds/${sportKey}`}
              className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
            >
              Compare Odds
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {games.map((g) => {
            const away = g.row.teamA?.name ?? "Away";
            const home = g.row.teamB?.name ?? "Home";
            const tip = g.row.time ?? null;
            const lineEdge = g.row.edgeLineNum;
            const totalEdge = g.row.edgeOUNum;
            return (
              <article
                key={g.slug}
                className="rounded-2xl border border-white/10 bg-black/35 p-4 sm:p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-kos-text sm:text-lg">
                      {away} @ {home}
                    </h3>
                    <p className="mt-1 text-xs tabular-nums text-kos-text/55">
                      {tip ? String(tip) : "Tip TBD"} · ET
                    </p>
                    <p className="mt-2 text-sm text-kos-text/75">
                      Market: {formatMarket(g)}
                    </p>
                    <p className="text-sm text-kos-gold/90">
                      Model: {formatModel(g)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 sm:items-end">
                    {(lineEdge != null && lineEdge > 0) ||
                    (totalEdge != null && totalEdge > 0) ? (
                      <span className="rounded-md border border-edge-green/35 bg-edge-green/10 px-2 py-1 text-xs font-semibold text-edge-green">
                        Sep{" "}
                        {Math.max(lineEdge ?? 0, totalEdge ?? 0).toFixed(1)}
                      </span>
                    ) : (
                      <span className="rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-kos-text/55">
                        Monitoring
                      </span>
                    )}
                    <Link
                      href={`/edge-board/${sportKey}`}
                      className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/20 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
                    >
                      Open on Edge Board
                    </Link>
                  </div>
                </div>
                <details className="mt-3">
                  <summary className="min-h-11 cursor-pointer list-none text-sm font-medium text-kos-gold hover:underline [&::-webkit-details-marker]:hidden">
                    Matchup context ▾
                  </summary>
                  <p className="mt-2 text-sm leading-relaxed text-kos-text/75 whitespace-pre-wrap">
                    {g.row.overview ??
                      `${away} at ${home}. Use KEI Lines and Edge Board for model vs market hierarchy. Research framing only.`}
                  </p>
                </details>
              </article>
            );
          })}
        </div>
      )}
    </SportHubShell>
  );
}
