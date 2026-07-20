import Link from "next/link";
import {
  fetchNflPropsBoard,
  formatAmericanOdds,
  formatConfidence,
  formatEdgeProb,
  formatPropNumber,
  propMarketLabel,
  PROP_MARKET_LABELS,
  type NflPropBoardRow,
} from "@/lib/nfl-props-board";

/** Default to a 2025 week with real Odds-API snapshots joined (weeks 4–17). 2026 lights up when yardage markets post. */
const DEFAULT_SEASON = 2025;
const DEFAULT_WEEK = 17;
const MARKET_TABS = ["ALL", ...Object.keys(PROP_MARKET_LABELS)] as const;
const LIMIT_OPTIONS = [100, 250, 500] as const;

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
  return query ? `/pro/nfl/props?${query}` : "/pro/nfl/props";
}

export default async function NflPropsBoardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const weekRaw = Number(firstValue(search.week));
  const season = Number.isFinite(seasonRaw) && seasonRaw >= 2010 ? seasonRaw : DEFAULT_SEASON;
  const week = Number.isFinite(weekRaw) && weekRaw >= 1 && weekRaw <= 25 ? weekRaw : DEFAULT_WEEK;
  const market = (firstValue(search.market) ?? "ALL").toLowerCase();
  const team = (firstValue(search.team) ?? "").toUpperCase();
  const limitRaw = Number(firstValue(search.limit));
  const limit = LIMIT_OPTIONS.includes(limitRaw as (typeof LIMIT_OPTIONS)[number]) ? limitRaw : 250;

  const board = await fetchNflPropsBoard({
    season,
    week,
    marketKey: market === "all" ? undefined : market,
    team: team || undefined,
    limit,
  });

  const activeQuery = {
    season: String(season),
    week: String(week),
    market: market === "all" ? undefined : market,
    team: team || undefined,
    limit: String(limit),
  };

  const topEdge = [...board.rows]
    .filter((row) => row.edgeOver !== null || row.edgeUnder !== null)
    .sort((a, b) => {
      const aMax = Math.max(Math.abs(a.edgeOver ?? 0), Math.abs(a.edgeUnder ?? 0));
      const bMax = Math.max(Math.abs(b.edgeOver ?? 0), Math.abs(b.edgeUnder ?? 0));
      return bMax - aMax;
    })[0];

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} Week {week} Props Board
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Kosedge Player Props
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Model means, fair over/under prices, and confidence for every materialised prop. Market edges appear
              only when a book line is joined — never invented.
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
              href="/pro/nfl/fair-lines"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Fair Lines Board →
            </Link>
          </div>
        </div>
      </section>

      {board.error ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {board.error} The props board will populate once the model service is reachable.
        </section>
      ) : null}

      {!board.error && board.diagnostics.kosedgeOnly ? (
        <section className="mt-6 rounded-2xl border border-sky-400/25 bg-sky-400/10 p-5 text-sm text-sky-100">
          No market-joined prop edges yet (with_mkt = 0). Showing Kosedge model means and fair prices only — market
          edge columns stay blank until books join.
        </section>
      ) : null}

      {!board.error ? (
        <section className="mt-6 grid gap-4 md:grid-cols-3">
          <StatCard
            label="Props on board"
            value={String(board.count)}
            detail={`${season} · Week ${week}`}
          />
          <StatCard
            label="Market joins"
            value={String(board.diagnostics.marketJoinedCount)}
            detail={
              board.diagnostics.marketJoinedCount > 0
                ? "Rows with live over/under book prices"
                : "Kosedge-only fair prices"
            }
          />
          <StatCard
            label="Largest model edge"
            value={
              topEdge
                ? `${topEdge.playerName} · ${propMarketLabel(topEdge.marketKey)}`
                : "—"
            }
            detail={
              topEdge
                ? `Over ${formatEdgeProb(topEdge.edgeOver)} · Under ${formatEdgeProb(topEdge.edgeUnder)}`
                : "Edges appear when market prices join"
            }
          />
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Market filter">
            {MARKET_TABS.map((tab) => {
              const key = tab.toLowerCase();
              const isActive = market === key;
              return (
                <Link
                  key={tab}
                  href={buildHref({
                    ...activeQuery,
                    market: key === "all" ? undefined : key,
                  })}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                  }`}
                >
                  {tab === "ALL" ? "ALL" : propMarketLabel(key)}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-2 text-xs text-kos-text/65">
            <span>Rows:</span>
            {LIMIT_OPTIONS.map((option) => (
              <Link
                key={option}
                href={buildHref({ ...activeQuery, limit: String(option) })}
                className={`rounded-md px-2 py-1 font-semibold transition ${
                  limit === option ? "bg-white/15 text-kos-text" : "text-kos-text/60 hover:text-kos-text"
                }`}
              >
                {option}
              </Link>
            ))}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <Link
            href={buildHref({ season: "2025", week: "1", limit: String(limit) })}
            className={`rounded-lg px-3 py-1.5 font-semibold transition ${
              season === 2025 && week === 1
                ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-edge-green/25"
            }`}
          >
            2025 W1 (has edges)
          </Link>
          <Link
            href={buildHref({ season: "2026", week: "1", limit: String(limit) })}
            className={`rounded-lg px-3 py-1.5 font-semibold transition ${
              season === 2026 && week === 1
                ? "border border-kos-gold/45 bg-kos-gold/15 text-kos-gold"
                : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-kos-gold/25"
            }`}
          >
            2026 W1
          </Link>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">Props Board</h2>
          <p className="text-xs text-kos-text/60">
            {board.count} prop{board.count === 1 ? "" : "s"}
          </p>
        </div>

        {!board.error && board.rows.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No prop edges for {season} week {week} yet. Try 2025 W1, or wait for the next materialization cycle.
          </div>
        ) : null}

        {board.rows.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Player</th>
                  <th className="px-3 py-2 font-semibold">Market</th>
                  <th className="px-3 py-2 font-semibold">Line</th>
                  <th className="px-3 py-2 font-semibold">Model mean</th>
                  <th className="px-3 py-2 font-semibold">Fair over</th>
                  <th className="px-3 py-2 font-semibold">Fair under</th>
                  <th className="px-3 py-2 font-semibold">Edge over</th>
                  <th className="px-3 py-2 font-semibold">Edge under</th>
                  <th className="px-3 py-2 font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {board.rows.map((row, index) => (
                  <PropRow key={`${row.playerId ?? row.playerName}-${row.marketKey}-${index}`} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}

function PropRow({ row }: { row: NflPropBoardRow }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">{row.playerName}</div>
        <div className="text-xs text-kos-text/55">{row.team}</div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">{propMarketLabel(row.marketKey)}</td>
      <td className="px-3 py-3 font-semibold text-kos-text">{formatPropNumber(row.line)}</td>
      <td className="px-3 py-3 font-semibold text-kos-gold">{formatPropNumber(row.modelMean)}</td>
      <td className="px-3 py-3 text-kos-text/90">{formatAmericanOdds(row.fairOverPrice)}</td>
      <td className="px-3 py-3 text-kos-text/90">{formatAmericanOdds(row.fairUnderPrice)}</td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined ? formatEdgeProb(row.edgeOver) : <span className="text-kos-text/40">no mkt</span>}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined ? formatEdgeProb(row.edgeUnder) : <span className="text-kos-text/40">no mkt</span>}
      </td>
      <td className="px-3 py-3 text-edge-green">{formatConfidence(row.confidence)}</td>
    </tr>
  );
}

function StatCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/55">{label}</p>
      <p className="mt-2 text-lg font-semibold text-kos-text">{value}</p>
      <p className="mt-1 text-xs text-kos-text/60">{detail}</p>
    </div>
  );
}
