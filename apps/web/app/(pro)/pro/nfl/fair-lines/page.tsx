import Link from "next/link";
import {
  edgeToneClass,
  fetchNflFairLines,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  formatWinProb,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";

const DEFAULT_SEASON = 2026;
/** Season slate window — API default is 14; widen so preseason still shows Week 1+. */
const DEFAULT_DAYS_AHEAD = 120;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function buildHref(base: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(base)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/pro/nfl/fair-lines?${query}` : "/pro/nfl/fair-lines";
}

export default async function NflFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const season = Number.isFinite(seasonRaw) && seasonRaw >= 2010 ? seasonRaw : DEFAULT_SEASON;
  const daysAheadRaw = Number(firstValue(search.daysAhead));
  const daysAhead =
    Number.isFinite(daysAheadRaw) && daysAheadRaw >= 1 && daysAheadRaw <= 365
      ? daysAheadRaw
      : DEFAULT_DAYS_AHEAD;
  const includePastDaysRaw = Number(firstValue(search.includePast));
  const includePastDays =
    Number.isFinite(includePastDaysRaw) && includePastDaysRaw >= 0 ? Math.min(includePastDaysRaw, 60) : 0;

  const board = await fetchNflFairLines({ season, daysAhead, includePastDays });
  const marketJoined = board.diagnostics.marketJoinedCount;
  const sample = board.lines.slice(0, 3);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} Fair Lines Board
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Kosedge Makes Its Own Lines
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Neutral model fair values — spread, total, and moneylines — for the upcoming slate. Market columns
              appear when the odds feed joins cleanly; otherwise you still get the Kosedge reference alone.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Back to NFL Overview
            </Link>
            <Link
              href="/pro/nfl/props"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Player Props Board →
            </Link>
          </div>
        </div>
      </section>

      {board.error ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {board.error} Fair lines will populate once the model service is reachable.
        </section>
      ) : null}

      {!board.error && board.diagnostics.kosedgeOnly ? (
        <section className="mt-6 rounded-2xl border border-sky-400/25 bg-sky-400/10 p-5 text-sm text-sky-100">
          Odds feed unavailable or unmatched — showing Kosedge lines only
          {board.diagnostics.oddsFeedError ? ` (${board.diagnostics.oddsFeedError})` : "."}
        </section>
      ) : null}

      {!board.error ? (
        <section className="mt-6 grid gap-4 md:grid-cols-3">
          <StatCard
            label="Games on board"
            value={String(board.count)}
            detail={`Next ${board.window.daysAhead} days · model ${board.modelVersion || "—"}`}
          />
          <StatCard
            label="Market joins"
            value={String(marketJoined)}
            detail={
              marketJoined > 0
                ? `${marketJoined} of ${board.count} games have live Vegas comparison`
                : "Kosedge-only until odds join"
            }
          />
          <StatCard
            label="Sims per line"
            value={sample[0]?.simulationCount ? String(sample[0].simulationCount) : "—"}
            detail="Monte Carlo replicates behind each fair price"
          />
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Lookahead window">
            {[14, 45, 120, 200].map((option) => {
              const isActive = daysAhead === option;
              return (
                <Link
                  key={option}
                  href={buildHref({
                    season: String(season),
                    daysAhead: String(option),
                    includePast: includePastDays > 0 ? String(includePastDays) : undefined,
                  })}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                  }`}
                >
                  {option}d ahead
                </Link>
              );
            })}
          </nav>
          <Link
            href={buildHref({
              season: String(season),
              daysAhead: String(daysAhead),
              includePast: includePastDays > 0 ? undefined : "3",
            })}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
              includePastDays > 0
                ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-edge-green/25"
            }`}
          >
            {includePastDays > 0 ? "Including recent games ✓" : "Include last 3 days"}
          </Link>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">Fair Lines Board</h2>
          <p className="text-xs text-kos-text/60">
            {board.count} game{board.count === 1 ? "" : "s"}
          </p>
        </div>

        {!board.error && board.lines.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No projections yet for this window. Widen the lookahead or wait for the next slate materialization.
          </div>
        ) : null}

        {board.lines.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Matchup</th>
                  <th className="px-3 py-2 font-semibold">Kickoff</th>
                  <th className="px-3 py-2 font-semibold">Kos spread</th>
                  <th className="px-3 py-2 font-semibold">Kos total</th>
                  <th className="px-3 py-2 font-semibold">Fair ML</th>
                  <th className="px-3 py-2 font-semibold">Win probs</th>
                  <th className="px-3 py-2 font-semibold">Vegas ML</th>
                  <th className="px-3 py-2 font-semibold">Vegas total</th>
                  <th className="px-3 py-2 font-semibold">ML edge</th>
                </tr>
              </thead>
              <tbody>
                {board.lines.map((row) => (
                  <FairLineRow key={row.gameId} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          Kosedge fair moneylines and spreads are simulation-backed reference prices — not picks. Edges are only
          shown when a live market price joins the same matchup.
        </p>
      </section>
    </main>
  );
}

function FairLineRow({ row }: { row: NflFairLineRow }) {
  return (
                <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">
          {row.awayAbbr} @ {row.homeAbbr}
        </div>
        <div className="text-xs text-kos-text/55">
          {row.awayTeam} at {row.homeTeam}
        </div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">{formatKickoff(row.startTime)}</td>
      <td className="px-3 py-3 font-semibold text-kos-gold">{formatSpread(row.spreadHome)}</td>
      <td className="px-3 py-3 font-semibold text-kos-text">{formatTotal(row.totalMean)}</td>
      <td className="px-3 py-3 text-kos-text/90">
        <div>
          H {formatAmericanOdds(row.fairHomeMl)} / A {formatAmericanOdds(row.fairAwayMl)}
        </div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatWinProb(row.homeWinProb)} / {formatWinProb(row.awayWinProb)}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined
          ? `${formatAmericanOdds(row.marketHomeMl)} / ${formatAmericanOdds(row.marketAwayMl)}`
          : "—"}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined ? formatTotal(row.marketTotal) : "—"}
      </td>
      <td className={`px-3 py-3 font-semibold ${edgeToneClass(row.mlEdgeProb)}`}>
        {row.mlEdgeProb === null ? "—" : `${(row.mlEdgeProb * 100).toFixed(1)}pp`}
      </td>
    </tr>
  );
}

function StatCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/55">{label}</p>
      <p className="mt-2 text-xl font-semibold text-kos-text">{value}</p>
      <p className="mt-1 text-xs text-kos-text/60">{detail}</p>
    </div>
  );
}
