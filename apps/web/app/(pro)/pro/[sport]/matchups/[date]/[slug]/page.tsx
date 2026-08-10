import Link from "next/link";
import {
  resolveSportKey,
  safeUpperCase,
  sportDisplayLabel,
} from "@/lib/sports";

const SPORT_CONTEXT_LABELS: Record<
  string,
  { drivers: string; execution: string; risk: string }
> = {
  nfl: {
    drivers: "key numbers, pressure rate, and explosive pass prevention",
    execution: "key-number timing and injury finalization",
    risk: "late injury designations and weather",
  },
  cfb: {
    drivers: "tempo divergence, havoc profile, and red-zone efficiency",
    execution: "market-limit timing and lineup confirmation",
    risk: "depth-chart volatility and weather",
  },
  nba: {
    drivers: "pace environment, rim pressure, and rotation depth",
    execution: "availability-aware repricing windows",
    risk: "late scratches and fatigue",
  },
  wnba: {
    drivers: "usage concentration, turnover control, and transition profile",
    execution: "book depth checks and travel-aware timing",
    risk: "rotation compression and guard availability",
  },
  mlb: {
    drivers: "starter fit, bullpen leverage, and park-adjusted run context",
    execution: "lineup-card timing and bullpen usage tracking",
    risk: "late scratches and wind shifts",
  },
  nhl: {
    drivers: "goaltender quality, five-on-five xG profile, and special teams",
    execution: "goalie confirmation and totals timing",
    risk: "goalie swaps and schedule congestion",
  },
  ncaam: {
    drivers: "tempo control, rebounding leverage, and foul environment",
    execution: "late steam handling and lineup validation",
    risk: "rotation volatility and whistle variance",
  },
};

function parseSlugTeams(
  slug: string | null | undefined,
): { away: string; home: string } | null {
  const token = safeUpperCase(slug);
  if (!token) return null;
  const parts = token.split(/[@-]/);
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return { away: parts[0]!, home: parts[1]! };
  }
  return null;
}

export default async function MatchupPage({
  params,
}: {
  params: Promise<{ sport: string; date: string; slug: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const date = String(resolved?.date ?? "today");
  const slug = String(resolved?.slug ?? "");
  const sportName = sportDisplayLabel(sportKey);
  const context = sportKey ? SPORT_CONTEXT_LABELS[sportKey] : undefined;
  const hasSportTemplate = Boolean(context);
  const teams = parseSlugTeams(slug);
  const isNfl = sportKey === "nfl";

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap gap-3 text-sm">
        <Link
          href={
            isNfl ? "/pro/nfl/slate/today" : `/pro/${sportKey}/slate/${date}`
          }
          className="text-kos-gold/90 hover:text-kos-gold"
        >
          ← Weekly Slate
        </Link>
        {isNfl ? (
          <>
            <Link href="/pro/nfl/overview" className="text-kos-text/65 hover:text-kos-text">
              NFL Overview
            </Link>
            <Link href="/edge-board/nfl" className="text-kos-text/65 hover:text-kos-text">
              Edge Board
            </Link>
          </>
        ) : null}
      </div>

      <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
        {isNfl ? "Brief pending · research links only" : `${sportName} matchup`}
      </p>
      <h1 className="mt-2 text-3xl font-semibold text-kos-text">
        {teams ? `${teams.away} @ ${teams.home}` : `${sportName} Matchup`}
      </h1>
      <p className="mt-2 text-sm text-kos-text/70">
        {sportName} · {date} · {slug}
      </p>

      {isNfl ? (
        <section className="mt-6 rounded-2xl border border-dashed border-white/20 bg-linear-to-r from-kos-gold/10 via-black/40 to-black/60 p-5">
          <h2 className="text-lg font-semibold text-kos-text">
            Writer preview · template
          </h2>
          <p className="mt-2 text-sm text-kos-text/75">
            Featured matchup brief is not attached yet — this shell is research
            links only, not a published brief. Use Team Previews and Edge Board
            for context until the Weekly Slate desk lands copy.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {teams ? (
              <>
                <Link
                  href={`/pro/nfl/previews/${teams.away}`}
                  className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
                >
                  {teams.away} preview
                </Link>
                <Link
                  href={`/pro/nfl/previews/${teams.home}`}
                  className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
                >
                  {teams.home} preview
                </Link>
                <Link
                  href={`/pro/nfl/teams/${teams.away}/overview`}
                  className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
                >
                  {teams.away} research
                </Link>
                <Link
                  href={`/pro/nfl/teams/${teams.home}/overview`}
                  className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
                >
                  {teams.home} research
                </Link>
              </>
            ) : null}
            <Link
              href="/edge-board/nfl"
              className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
            >
              Open Edge Board
            </Link>
            <Link
              href="/pro/nfl/props"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Props
            </Link>
          </div>
        </section>
      ) : null}

      <div className="mt-6 grid gap-6">
        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h2 className="text-lg font-semibold">Model vs Market</h2>
          <p className="mt-2 text-sm text-kos-text/80">
            {hasSportTemplate
              ? `KEI lines and best book prices for this matchup — jump to Edge Board or KEI Lines for the live board.`
              : "Model reference and best available numbers pending data sync."}
          </p>
          {isNfl ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href="/pro/nfl/fair-lines"
                className="text-sm font-semibold text-kos-gold hover:underline"
              >
                KEI Lines →
              </Link>
              <Link
                href="/odds/nfl"
                className="text-sm font-semibold text-kos-text/70 hover:text-kos-gold"
              >
                Compare Odds →
              </Link>
            </div>
          ) : null}
        </section>

        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h2 className="text-lg font-semibold">Key stats & personnel</h2>
          <p className="mt-2 text-sm text-kos-text/80">
            Drivers: {context?.drivers ?? "matchup efficiency variables"}.
            Execution focus: {context?.execution ?? "timing windows"}. Risk:{" "}
            {context?.risk ?? "availability and environment"}.
          </p>
        </section>
      </div>
    </main>
  );
}
