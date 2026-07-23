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
/** Wide fetch window; UI slate tabs decide what to show. */
const FETCH_DAYS_AHEAD = 200;
const PAST_WEEK_DAYS = 7;

type SearchValue = string | string[] | undefined;
type Slate = "week" | "season";

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

function isInPastWindow(startTime: string | null, pastDays: number): boolean {
  if (!startTime || pastDays <= 0) return false;
  const t = new Date(startTime).getTime();
  if (!Number.isFinite(t)) return false;
  const now = Date.now();
  const cutoff = now - pastDays * 24 * 60 * 60 * 1000;
  return t >= cutoff && t <= now;
}

export default async function NflFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const season = Number.isFinite(seasonRaw) && seasonRaw >= 2010 ? seasonRaw : DEFAULT_SEASON;
  const slate: Slate = firstValue(search.slate) === "season" ? "season" : "week";
  const includePastRaw = firstValue(search.includePast);
  const includePastDays =
    includePastRaw === "7" || includePastRaw === "3" || includePastRaw === "1" ? PAST_WEEK_DAYS : 0;

  const board = await fetchNflFairLines({
    season,
    daysAhead: FETCH_DAYS_AHEAD,
    includePastDays,
  });

  const visibleLines =
    slate === "season"
      ? board.lines
      : board.lines.filter((row) => {
          if (row.week != null && row.week === board.currentWeek) return true;
          return isInPastWindow(row.startTime, includePastDays);
        });

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} KEI Lines
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Kosedge Makes Its Own Lines
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Neutral model fair values — spread, total, and moneylines — for the slate. Market columns appear when
              Vegas joins; otherwise you still get the Kosedge reference alone.
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
              href="/pro/nfl/edges"
              className="rounded-xl border border-edge-green/35 bg-edge-green/10 px-4 py-2 text-center text-sm font-semibold text-edge-green transition hover:border-edge-green/55"
            >
              Edges Desk →
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
          KEI Lines will populate once the model service is reachable.
        </section>
      ) : null}

      {!board.error && board.diagnostics.kosedgeOnly ? (
        <section className="mt-6 rounded-2xl border border-sky-400/25 bg-sky-400/10 p-5 text-sm text-sky-100">
          Vegas lines unavailable — showing Kosedge lines only.
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Slate window">
            {(
              [
                { id: "week" as const, label: "Current week" },
                { id: "season" as const, label: "Season slate" },
              ] as const
            ).map((option) => {
              const isActive = slate === option.id;
              return (
                <Link
                  key={option.id}
                  href={buildHref({
                    season: String(season),
                    slate: option.id === "week" ? undefined : option.id,
                    includePast: includePastDays > 0 ? String(PAST_WEEK_DAYS) : undefined,
                  })}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                  }`}
                >
                  {option.label}
                </Link>
              );
            })}
          </nav>
          <Link
            href={buildHref({
              season: String(season),
              slate: slate === "week" ? undefined : slate,
              includePast: includePastDays > 0 ? undefined : String(PAST_WEEK_DAYS),
            })}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
              includePastDays > 0
                ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-edge-green/25"
            }`}
          >
            {includePastDays > 0 ? "Including last week ✓" : "Include last week"}
          </Link>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">KEI Lines</h2>
          <p className="text-xs text-kos-text/60">
            {visibleLines.length} game{visibleLines.length === 1 ? "" : "s"}
            {slate === "week" && board.currentWeek ? ` · Week ${board.currentWeek}` : ""}
          </p>
        </div>

        {!board.error && visibleLines.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No lines in this window yet. Try Season slate, or wait for the next update.
          </div>
        ) : null}

        {visibleLines.length > 0 ? (
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
                {visibleLines.map((row) => (
                  <FairLineRow key={row.gameId} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          KEI moneylines and spreads are simulation-backed reference prices — not picks. Edges are only shown when a
          live market price joins the same matchup.
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
