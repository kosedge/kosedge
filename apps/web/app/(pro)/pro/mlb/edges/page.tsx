import Link from "next/link";
import {
  fetchMlbEdgesDesk,
  formatQuality,
  formatStakeFraction,
  type MlbDeskEdgeRow,
  type MlbDeskMarketType,
} from "@/lib/mlb-edges";

const MARKET_TABS: MlbDeskMarketType[] = ["all", "ml", "total", "run_line"];
const MIN_EDGE_OPTIONS = [
  { label: "1pp / 0.5 run", prob: 0.01, line: 0.5 },
  { label: "2pp / 0.75 run", prob: 0.02, line: 0.75 },
  { label: "3pp / 1.0 run", prob: 0.03, line: 1.0 },
] as const;
const MIN_QUALITY_OPTIONS = [0, 55, 62, 70] as const;

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
  return query ? `/pro/mlb/edges?${query}` : "/pro/mlb/edges";
}

function marketLabel(market: MlbDeskMarketType): string {
  switch (market) {
    case "all":
      return "All";
    case "ml":
      return "ML";
    case "total":
      return "Total";
    case "run_line":
      return "Run line";
  }
}

export default async function MlbEdgesDeskPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const marketRaw = (firstValue(search.market) ?? "all").toLowerCase();
  const market = (
    MARKET_TABS.includes(marketRaw as MlbDeskMarketType) ? marketRaw : "all"
  ) as MlbDeskMarketType;
  const minEdgeIdxRaw = Number(firstValue(search.minEdge));
  const minEdgeIdx =
    Number.isFinite(minEdgeIdxRaw) &&
    minEdgeIdxRaw >= 0 &&
    minEdgeIdxRaw < MIN_EDGE_OPTIONS.length
      ? minEdgeIdxRaw
      : 1;
  const minEdge = MIN_EDGE_OPTIONS[minEdgeIdx];
  const minQualityRaw = Number(firstValue(search.minQuality));
  const minQuality = MIN_QUALITY_OPTIONS.includes(
    minQualityRaw as (typeof MIN_QUALITY_OPTIONS)[number],
  )
    ? minQualityRaw
    : 0;
  const gameDate = firstValue(search.date);

  const desk = await fetchMlbEdgesDesk({
    market,
    minProbEdge: minEdge.prob,
    minLineEdge: minEdge.line,
    minQuality,
    gameDate,
  });

  const activeQuery = {
    date: gameDate,
    market: market === "all" ? undefined : market,
    minEdge: String(minEdgeIdx),
    minQuality: minQuality > 0 ? String(minQuality) : undefined,
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              MLB Betting Desk · Edges
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Actionable MLB Edges
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Fair Lines → Edges → Run Line. Today’s ML and total edges with
              quality score and stake fraction; run-line leans surface from fair
              cover probability when extreme.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/mlb/fair-lines"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              ← Fair Lines
            </Link>
            <Link
              href="/pro/mlb/fair-lines?focus=run-line"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Run Line Board →
            </Link>
          </div>
        </div>
      </section>

      {desk.diagnostics.edgesTodayError ? (
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
          <span>Min quality:</span>
          {MIN_QUALITY_OPTIONS.map((option) => (
            <Link
              key={option}
              href={buildHref({
                ...activeQuery,
                minQuality: option > 0 ? String(option) : undefined,
              })}
              className={`rounded-md px-2 py-1 font-semibold transition ${
                minQuality === option
                  ? "bg-white/15 text-kos-text"
                  : "text-kos-text/60 hover:text-kos-text"
              }`}
            >
              {option === 0 ? "Any" : String(option)}
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">Edges Board</h2>
          <p className="text-xs text-kos-text/60">
            {desk.count} edge{desk.count === 1 ? "" : "s"}
            {desk.modelVersion ? ` · ${desk.modelVersion}` : ""}
          </p>
        </div>

        {!desk.diagnostics.edgesTodayError && desk.rows.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No edges clear the current thresholds. Lower min edge / quality,
            widen market type, or check{" "}
            <Link
              href="/pro/mlb/fair-lines"
              className="text-kos-gold underline-offset-2 hover:underline"
            >
              Fair Lines
            </Link>{" "}
            for the full board.
          </div>
        ) : null}

        {desk.rows.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Matchup</th>
                  <th className="px-3 py-2 font-semibold">Market</th>
                  <th className="px-3 py-2 font-semibold">Kosedge</th>
                  <th className="px-3 py-2 font-semibold">Vegas</th>
                  <th className="px-3 py-2 font-semibold">Edge</th>
                  <th className="px-3 py-2 font-semibold">Side</th>
                  <th className="px-3 py-2 font-semibold">Quality</th>
                  <th className="px-3 py-2 font-semibold">Stake</th>
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
        Decision support only — not picks. ML/total edges require a joined
        market price from today&apos;s odds feed; run-line leans are model-cover
        signals until books join.
      </p>
    </main>
  );
}

function EdgeRow({ row }: { row: MlbDeskEdgeRow }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">{row.matchup}</div>
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
      <td className="px-3 py-3 text-edge-green">{row.side}</td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatQuality(row.qualityScore)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatStakeFraction(row.stakeFraction)}
      </td>
    </tr>
  );
}
