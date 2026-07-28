import Link from "next/link";
import {
  fetchMlbFairLines,
  formatAmericanOdds,
  formatKickoff,
  formatRunLine,
  formatTotal,
  formatWinProb,
  type MlbFairLineRow,
} from "@/lib/mlb-fair-lines";

type SearchValue = string | string[] | undefined;
type Focus = "all" | "run-line";

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
  return query ? `/pro/mlb/fair-lines?${query}` : "/pro/mlb/fair-lines";
}

export default async function MlbFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const gameDate = firstValue(search.date);
  const focus: Focus =
    firstValue(search.focus) === "run-line" ? "run-line" : "all";

  const board = await fetchMlbFairLines({ gameDate });
  const lines = board.lines;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              MLB Fair Lines{board.gameDate ? ` · ${board.gameDate}` : ""}
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Kosedge MLB Fair Values
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Neutral model fair values — moneyline, total runs, and run line —
              for today’s slate. Starter and bullpen context feeds the
              projection; this board stays outcome-neutral.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/mlb/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Back to MLB Overview
            </Link>
            <Link
              href="/pro/mlb/edges"
              className="rounded-xl border border-edge-green/35 bg-edge-green/10 px-4 py-2 text-center text-sm font-semibold text-edge-green transition hover:border-edge-green/55"
            >
              Edges Desk →
            </Link>
            <Link
              href={buildHref({
                date: gameDate,
                focus: focus === "run-line" ? undefined : "run-line",
              })}
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              {focus === "run-line" ? "Show all markets →" : "Focus run line →"}
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
          <nav className="flex flex-wrap gap-2" aria-label="Market focus">
            {(
              [
                { id: "all" as const, label: "All markets" },
                { id: "run-line" as const, label: "Run line focus" },
              ] as const
            ).map((option) => {
              const isActive = focus === option.id;
              return (
                <Link
                  key={option.id}
                  href={buildHref({
                    date: gameDate,
                    focus: option.id === "all" ? undefined : option.id,
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
          <p className="text-xs text-kos-text/60">
            {lines.length} game{lines.length === 1 ? "" : "s"}
            {board.modelVersion ? ` · ${board.modelVersion}` : ""}
          </p>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">
            {focus === "run-line" ? "Run Line Board" : "Fair Lines"}
          </h2>
        </div>

        {!board.error && lines.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No MLB projections for this date yet. Check back after the daily sim
            cycle.
          </div>
        ) : null}

        {lines.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Matchup</th>
                  <th className="px-3 py-2 font-semibold">First pitch</th>
                  <th className="px-3 py-2 font-semibold">Fair ML</th>
                  <th className="px-3 py-2 font-semibold">Win probs</th>
                  <th className="px-3 py-2 font-semibold">Fair total</th>
                  <th
                    className={`px-3 py-2 font-semibold ${focus === "run-line" ? "text-kos-gold" : ""}`}
                  >
                    Run line (home)
                  </th>
                  <th
                    className={`px-3 py-2 font-semibold ${focus === "run-line" ? "text-kos-gold" : ""}`}
                  >
                    Home cover prob
                  </th>
                </tr>
              </thead>
              <tbody>
                {lines.map((row) => (
                  <FairLineRow
                    key={row.gameId}
                    row={row}
                    emphasizeRunLine={focus === "run-line"}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          MLB fair lines are simulation-backed reference prices — not picks. Run
          line uses the model’s home cover probability and fair spread; Edges
          desk joins live Vegas ML/totals when available.
        </p>
      </section>
    </main>
  );
}

function FairLineRow({
  row,
  emphasizeRunLine,
}: {
  row: MlbFairLineRow;
  emphasizeRunLine: boolean;
}) {
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
      <td
        className={`px-3 py-3 font-semibold ${emphasizeRunLine ? "text-kos-gold" : "text-kos-gold/90"}`}
      >
        {formatRunLine(row.fairSpreadHome)}
      </td>
      <td
        className={`px-3 py-3 font-semibold ${emphasizeRunLine ? "text-edge-green" : "text-kos-text/80"}`}
      >
        {formatWinProb(row.runLineCoverProbHome)}
      </td>
    </tr>
  );
}
