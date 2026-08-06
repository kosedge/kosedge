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
import {
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";

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

function handicapMl(row: MlbFairLineRow): {
  home: number | null;
  away: number | null;
} {
  return {
    home: row.handicapHomeMl ?? row.fairHomeMl,
    away: row.handicapAwayMl ?? row.fairAwayMl,
  };
}

function modelMl(row: MlbFairLineRow): {
  home: number | null;
  away: number | null;
} {
  return {
    home: row.modelHomeMl ?? row.handicapHomeMl ?? row.fairHomeMl,
    away: row.modelAwayMl ?? row.handicapAwayMl ?? row.fairAwayMl,
  };
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
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.12),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              MLB Fair Lines{board.gameDate ? ` · ${board.gameDate}` : ""} · ET
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
              KEI Lines
            </h1>
            <p className="mt-2 text-sm text-kos-text/75">
              Model = pure sim research fair. KEI handicap = the product line
              (model plus lineup/nowcast movement) shown on the Edge Board —
              moneyline, total runs, and run line. Research only — you make the
              picks.
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs">
              <Link
                href="/pro/mlb/overview"
                className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
              >
                ← MLB Overview
              </Link>
              <Link
                href="/edge-board/mlb"
                className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
              >
                Edge Board →
              </Link>
            </div>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-48">
            <Link
              href="/pro/mlb/edges"
              className="min-h-11 rounded-xl border border-edge-green/35 bg-edge-green/10 px-4 py-2.5 text-center text-sm font-semibold text-edge-green transition hover:border-edge-green/55"
            >
              Edges Desk →
            </Link>
            <Link
              href={buildHref({
                date: gameDate,
                focus: focus === "run-line" ? undefined : "run-line",
              })}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              {focus === "run-line" ? "Show all markets →" : "Focus run line →"}
            </Link>
          </div>
        </div>
      </section>

      {shouldShowModelUnreachableBanner({
        error: board.error,
        hasContent: lines.length > 0,
      }) ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {modelUnreachableCopy(board.error)}
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
          <>
            <div className="mt-4 grid gap-3 md:hidden">
              {lines.map((row) => {
                const h = handicapMl(row);
                const m = modelMl(row);
                return (
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
                        <div className="text-kos-text/50">Model ML</div>
                        <div className="mt-0.5 text-kos-text/80">
                          H {formatAmericanOdds(m.home)} / A{" "}
                          {formatAmericanOdds(m.away)}
                        </div>
                      </div>
                      <div>
                        <div className="text-kos-gold/70">KEI ML</div>
                        <div className="mt-0.5 font-semibold text-kos-gold">
                          H {formatAmericanOdds(h.home)} / A{" "}
                          {formatAmericanOdds(h.away)}
                        </div>
                      </div>
                      <div>
                        <div className="text-kos-text/50">Model total</div>
                        <div className="mt-0.5 text-kos-text/80">
                          {formatTotal(
                            row.modelTotal ??
                              row.modelTotalMean ??
                              row.fairTotal ??
                              row.totalMean,
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-kos-gold/70">KEI total</div>
                        <div className="mt-0.5 font-semibold text-kos-gold">
                          {formatTotal(
                            row.handicapTotal ??
                              row.fairTotal ??
                              row.totalMean,
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-kos-text/50">Run line (home)</div>
                        <div
                          className={`mt-0.5 font-semibold ${focus === "run-line" ? "text-kos-gold" : "text-kos-text"}`}
                        >
                          {formatRunLine(
                            row.handicapSpreadHome ?? row.fairSpreadHome,
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-kos-text/50">Home cover</div>
                        <div className="mt-0.5 text-kos-text">
                          {formatWinProb(row.runLineCoverProbHome)}
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
            <div className="mt-4 hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr className="border-b border-white/10">
                    <th className="px-3 py-2 font-semibold">Matchup</th>
                    <th className="px-3 py-2 font-semibold">First pitch</th>
                    <th className="px-3 py-2 font-semibold">Model ML</th>
                    <th className="px-3 py-2 font-semibold text-kos-gold/80">
                      KEI ML
                    </th>
                    <th className="px-3 py-2 font-semibold">Model win</th>
                    <th className="px-3 py-2 font-semibold text-kos-gold/80">
                      KEI win
                    </th>
                    <th className="px-3 py-2 font-semibold">Model total</th>
                    <th className="px-3 py-2 font-semibold text-kos-gold/80">
                      KEI total
                    </th>
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
          </>
        ) : null}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          Edge Board tags compare KEI handicap to the best market — not raw
          model. When model and KEI match, no nowcast/lineup movement has been
          applied yet. Run line uses the model’s home cover probability and fair
          spread; Edges desk joins live market ML/totals when available.
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
  const h = handicapMl(row);
  const m = modelMl(row);
  const modelWin = row.modelHomeWinProb ?? row.handicapHomeWinProb ?? row.homeWinProb;
  const keiWin = row.handicapHomeWinProb ?? row.homeWinProb;
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
      <td className="px-3 py-3 text-kos-text/70">
        H {formatAmericanOdds(m.home)} / A {formatAmericanOdds(m.away)}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        H {formatAmericanOdds(h.home)} / A {formatAmericanOdds(h.away)}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {formatWinProb(modelWin)}
        {modelWin !== null && modelWin !== undefined
          ? ` / ${formatWinProb(1 - modelWin)}`
          : " / —"}
      </td>
      <td className="px-3 py-3 text-kos-text/90">
        {formatWinProb(keiWin ?? null)}
        {keiWin != null ? ` / ${formatWinProb(1 - keiWin)}` : " / —"}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatTotal(
          row.modelTotal ?? row.modelTotalMean ?? row.fairTotal ?? row.totalMean,
        )}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-text">
        {formatTotal(row.handicapTotal ?? row.fairTotal ?? row.totalMean)}
      </td>
      <td
        className={`px-3 py-3 font-semibold ${emphasizeRunLine ? "text-kos-gold" : "text-kos-gold/90"}`}
      >
        {formatRunLine(row.handicapSpreadHome ?? row.fairSpreadHome)}
      </td>
      <td
        className={`px-3 py-3 font-semibold ${emphasizeRunLine ? "text-edge-green" : "text-kos-text/80"}`}
      >
        {formatWinProb(row.runLineCoverProbHome)}
      </td>
    </tr>
  );
}
