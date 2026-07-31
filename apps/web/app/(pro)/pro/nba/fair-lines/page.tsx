import Link from "next/link";
import {
  fetchNbaFairLines,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  formatWinProb,
  type NbaFairLineRow,
} from "@/lib/nba-fair-lines";

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
  return query ? `/pro/nba/fair-lines?${query}` : "/pro/nba/fair-lines";
}

export default async function NbaFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const gameDate = firstValue(search.date);

  const board = await fetchNbaFairLines({ gameDate, daysAhead: 5 });
  const lines = board.lines;
  const emptyHonest =
    !board.error &&
    lines.length === 0 &&
    (board.slateStatus === "offseason_empty" ||
      board.slateStatus === "no_projections_yet");

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.12),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              NBA Fair Lines{board.gameDate ? ` · ${board.gameDate}` : ""} · ET
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
              KEI Lines
            </h1>
            <p className="mt-2 text-sm text-kos-text/75">
              Possession-level Monte Carlo reference prices — moneyline, spread,
              and total. Research only — you make the picks. We do not invent
              fair prices when the slate is empty.
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs">
              <Link
                href="/pro/nba/overview"
                className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
              >
                ← NBA Overview
              </Link>
              <Link
                href="/edge-board/nba"
                className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
              >
                Edge Board →
              </Link>
            </div>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-48">
            <Link
              href="/pro/nba/edges"
              className="min-h-11 rounded-xl border border-edge-green/35 bg-edge-green/10 px-4 py-2.5 text-center text-sm font-semibold text-edge-green transition hover:border-edge-green/55"
            >
              Edges Desk →
            </Link>
            <Link
              href={buildHref({
                date: gameDate
                  ? undefined
                  : new Date().toISOString().slice(0, 10),
              })}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              {gameDate ? "Clear date filter →" : "Filter today →"}
            </Link>
          </div>
        </div>
      </section>

      {board.error ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          Fair lines will populate once the model service is reachable.
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-kos-text/60">
            {lines.length} game{lines.length === 1 ? "" : "s"}
            {board.modelVersion ? ` · ${board.modelVersion}` : ""}
            {board.workerBuildId ? ` · ${board.workerBuildId}` : ""}
            {board.phase ? ` · ${board.phase}` : ""}
          </p>
          {board.slateStatus && board.slateStatus !== "ok" ? (
            <p className="text-xs font-medium text-kos-gold/80">
              slate: {board.slateStatus}
            </p>
          ) : null}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">Fair Lines</h2>
        </div>

        {emptyHonest ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            {board.message ??
              "NBA possession sim board is connected. No projections for this date yet — offseason empty slate is intentional, not a stub price."}
          </div>
        ) : null}

        {!board.error && !emptyHonest && lines.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No NBA projections for this date yet. Check back after the daily sim
            cycle.
          </div>
        ) : null}

        {lines.length > 0 ? (
          <>
            <div className="mt-4 grid gap-3 md:hidden">
              {lines.map((row) => (
                <article
                  key={row.gameId}
                  className="rounded-xl border border-white/10 bg-black/35 p-4"
                >
                  <div className="text-sm font-semibold text-kos-text">
                    {row.awayTeam} @ {row.homeTeam}
                  </div>
                  <p className="mt-1 text-xs text-kos-text/55">
                    {formatKickoff(row.startTime)} · ET
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-kos-text/50">Fair ML</div>
                      <div className="mt-0.5 text-kos-text">
                        H {formatAmericanOdds(row.fairHomeMl)} / A{" "}
                        {formatAmericanOdds(row.fairAwayMl)}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Fair total</div>
                      <div className="mt-0.5 font-semibold text-kos-gold">
                        {formatTotal(row.fairTotal ?? row.totalMean)}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Spread (home)</div>
                      <div className="mt-0.5 font-semibold text-kos-gold">
                        {formatSpread(row.fairSpreadHome)}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Home cover</div>
                      <div className="mt-0.5 text-kos-text">
                        {formatWinProb(row.homeCoverProb)}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <div className="mt-4 hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr className="border-b border-white/10">
                    <th className="px-3 py-2 font-semibold">Matchup</th>
                    <th className="px-3 py-2 font-semibold">Tip</th>
                    <th className="px-3 py-2 font-semibold">Fair ML</th>
                    <th className="px-3 py-2 font-semibold">Win probs</th>
                    <th className="px-3 py-2 font-semibold">Fair total</th>
                    <th className="px-3 py-2 font-semibold">Spread (home)</th>
                    <th className="px-3 py-2 font-semibold">Home cover</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((row) => (
                    <FairLineRow key={row.gameId} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          NBA fair lines are simulation-backed reference prices from the
          possession Monte Carlo — not picks. Edges desk joins live market
          lines when available. Props stay queued until mainlines calibrate.
        </p>
      </section>
    </main>
  );
}

function FairLineRow({ row }: { row: NbaFairLineRow }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">
          {row.awayTeam} @ {row.homeTeam}
        </div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatKickoff(row.startTime)}
      </td>
      <td className="px-3 py-3 text-kos-text/90">
        H {formatAmericanOdds(row.fairHomeMl)} / A{" "}
        {formatAmericanOdds(row.fairAwayMl)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatWinProb(row.homeWinProb)}
        {row.homeWinProb !== null
          ? ` / ${formatWinProb(1 - row.homeWinProb)}`
          : " / —"}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-text">
        {formatTotal(row.fairTotal ?? row.totalMean)}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        {formatSpread(row.fairSpreadHome)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatWinProb(row.homeCoverProb)}
      </td>
    </tr>
  );
}
