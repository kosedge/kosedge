import Link from "next/link";
import {
  fetchNflEdgesDesk,
  formatKickoff,
  type DeskEdgeRow,
  type DeskMarketType,
} from "@/lib/nfl-edges";

const DEFAULT_SEASON = 2026;
const DEFAULT_WEEK = 1;
const MARKET_TABS: DeskMarketType[] = ["all", "ml", "spread", "total", "props"];
const MIN_EDGE_OPTIONS = [
  { label: "1pp / 0.5pt", prob: 0.01, line: 0.5 },
  { label: "2pp / 1pt", prob: 0.02, line: 1.0 },
  { label: "3pp / 1.5pt", prob: 0.03, line: 1.5 },
] as const;
const MIN_CONF_OPTIONS = [0, 0.4, 0.6, 0.75] as const;

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
  return query ? `/pro/nfl/edges?${query}` : "/pro/nfl/edges";
}

function marketLabel(market: DeskMarketType): string {
  switch (market) {
    case "all":
      return "All";
    case "ml":
      return "ML";
    case "spread":
      return "Spread";
    case "total":
      return "Total";
    case "props":
      return "Props";
  }
}

export default async function NflEdgesDeskPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const weekRaw = Number(firstValue(search.week));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010
      ? seasonRaw
      : DEFAULT_SEASON;
  const week =
    Number.isFinite(weekRaw) && weekRaw >= 1 && weekRaw <= 25
      ? weekRaw
      : DEFAULT_WEEK;
  const marketRaw = (firstValue(search.market) ?? "all").toLowerCase();
  const market = (
    MARKET_TABS.includes(marketRaw as DeskMarketType) ? marketRaw : "all"
  ) as DeskMarketType;
  const minEdgeIdxRaw = Number(firstValue(search.minEdge));
  const minEdgeIdx =
    Number.isFinite(minEdgeIdxRaw) &&
    minEdgeIdxRaw >= 0 &&
    minEdgeIdxRaw < MIN_EDGE_OPTIONS.length
      ? minEdgeIdxRaw
      : 1;
  const minEdge = MIN_EDGE_OPTIONS[minEdgeIdx];
  const minConfRaw = Number(firstValue(search.minConf));
  const minConfidence = MIN_CONF_OPTIONS.includes(
    minConfRaw as (typeof MIN_CONF_OPTIONS)[number],
  )
    ? minConfRaw
    : 0;

  const desk = await fetchNflEdgesDesk({
    season,
    week,
    market,
    minProbEdge: minEdge.prob,
    minLineEdge: minEdge.line,
    minConfidence,
  });

  const activeQuery = {
    season: String(season),
    week: String(week),
    market: market === "all" ? undefined : market,
    minEdge: String(minEdgeIdx),
    minConf: minConfidence > 0 ? String(minConfidence) : undefined,
  };

  const fetchError =
    desk.diagnostics.fairLinesError &&
    desk.diagnostics.edgesTodayError &&
    desk.diagnostics.propsError
      ? desk.diagnostics.fairLinesError
      : undefined;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              Week {week} · {season} · Research desk
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Model vs Market Edges
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Meaningful separations between Kos Edge lines and the joined
              market. Research context only — not a pick sheet. Empty when
              nothing clears the cut.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              NFL Overview
            </Link>
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
            >
              Edge Board →
            </Link>
          </div>
        </div>
      </section>

      {fetchError ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          Edges will populate once the model service is reachable.
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Market type">
            {MARKET_TABS.map((tab) => {
              const isActive = market === tab;
              return (
                <Link
                  key={tab}
                  href={buildHref({
                    ...activeQuery,
                    market: tab === "all" ? undefined : tab,
                  })}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-edge-green/25 hover:text-kos-text"
                  }`}
                >
                  {marketLabel(tab)}
                </Link>
              );
            })}
          </nav>
          <div className="flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
            <span>Min edge:</span>
            {MIN_EDGE_OPTIONS.map((option, index) => (
              <Link
                key={option.label}
                href={buildHref({ ...activeQuery, minEdge: String(index) })}
                className={`rounded-md px-2 py-1 font-semibold transition ${
                  minEdgeIdx === index
                    ? "bg-white/15 text-kos-text"
                    : "text-kos-text/60 hover:text-kos-text"
                }`}
              >
                {option.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
          <span>Min confidence:</span>
          {MIN_CONF_OPTIONS.map((option) => (
            <Link
              key={option}
              href={buildHref({
                ...activeQuery,
                minConf: option > 0 ? String(option) : undefined,
              })}
              className={`rounded-md px-2 py-1 font-semibold transition ${
                minConfidence === option
                  ? "bg-white/15 text-kos-text"
                  : "text-kos-text/60 hover:text-kos-text"
              }`}
            >
              {option === 0 ? "Any" : `${Math.round(option * 100)}%`}
            </Link>
          ))}
          <span className="ml-2 text-kos-text/45">Week:</span>
          {[1, 2, 3, 4, 5].map((w) => (
            <Link
              key={w}
              href={buildHref({ ...activeQuery, week: String(w) })}
              className={`rounded-md px-2 py-1 font-semibold transition ${
                week === w
                  ? "border border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                  : "text-kos-text/60"
              }`}
            >
              Week {w} · {season}
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">
            Edges · Week {week} · {season}
          </h2>
        </div>

        {!fetchError && desk.rows.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No edges clear the current thresholds. Lower min edge / confidence,
            widen market type, or check{" "}
            <Link
              href="/pro/nfl/fair-lines"
              className="text-kos-gold underline-offset-2 hover:underline"
            >
              KEI Lines
            </Link>{" "}
            and{" "}
            <Link
              href="/pro/nfl/props"
              className="text-kos-gold underline-offset-2 hover:underline"
            >
              Props
            </Link>{" "}
            for the full boards.
          </div>
        ) : null}

        {desk.rows.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Matchup / Player</th>
                  <th className="px-3 py-2 font-semibold">Type</th>
                  <th className="px-3 py-2 font-semibold">KEI</th>
                  <th className="px-3 py-2 font-semibold">Book</th>
                  <th className="px-3 py-2 font-semibold">Separation</th>
                  <th className="px-3 py-2 font-semibold">Lean</th>
                  <th className="px-3 py-2 font-semibold">Kickoff (ET)</th>
                </tr>
              </thead>
              <tbody>
                {desk.rows.map((row) => (
                  <EdgeRow key={row.id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <p className="mt-4 text-xs text-kos-text/45">
        Decision support only — not picks. Edges require a joined market price;
        Kosedge-only lines stay on KEI Lines / Props.
      </p>
    </main>
  );
}

function EdgeRow({ row }: { row: DeskEdgeRow }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">{row.matchupOrPlayer}</div>
        <div className="text-xs text-kos-text/55">{row.detail}</div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {marketLabel(row.marketType)}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        {row.kosedgeLine}
      </td>
      <td className="px-3 py-3 text-kos-text/90">{row.vegasLine}</td>
      <td className="px-3 py-3 font-semibold text-edge-green">
        {row.edgeDisplay}
      </td>
      <td className="px-3 py-3 text-kos-text/85">{row.side}</td>
      <td className="px-3 py-3 text-xs text-kos-text/60">
        {formatKickoff(row.kickoff)}
      </td>
    </tr>
  );
}
