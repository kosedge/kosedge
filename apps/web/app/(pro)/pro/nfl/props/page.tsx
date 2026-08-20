import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import {
  fetchNflPropsBoard,
  formatAmericanOdds,
  formatConfidence,
  formatEdgeProb,
  formatPropNumber,
  propMarketLabel,
  type NflPropBoardRow,
} from "@/lib/nfl-props-board";
import {
  NFL_WEEKLY_PROPS_GATE_BODY,
  NFL_WEEKLY_PROPS_GATE_TITLE,
  NFL_WEEKLY_PROPS_LIVE,
  NFL_WEEKLY_PROPS_METHODS,
} from "@/lib/nfl-weekly-props-live";
import {
  PRIMARY_BOARD_MARKETS,
  PROPS_ELIGIBILITY_NOTE,
} from "@/lib/nfl-props-eligibility";
import {
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";
import { formatNflWeekLabel } from "@/lib/nfl-truth-label";

/** Soft-launch default: current season board — never archive-week CTAs. */
const DEFAULT_SEASON = 2026;
const DEFAULT_WEEK = 1;
const MARKET_TABS = ["ALL", ...PRIMARY_BOARD_MARKETS] as const;
const LIMIT_OPTIONS = [100, 250, 500] as const;
const KOSEDGE_DATE = "August 11, 2026";

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

function asOfLabel(rows: NflPropBoardRow[]): string {
  const stamps = rows
    .map((r) => r.updatedAt)
    .filter((v): v is string => Boolean(v))
    .map((v) => Date.parse(v))
    .filter((n) => Number.isFinite(n));
  if (stamps.length === 0) return KOSEDGE_DATE;
  const latest = new Date(Math.max(...stamps));
  return latest.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export default async function NflPropsBoardPage({
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
  const market = (firstValue(search.market) ?? "ALL").toLowerCase();
  const team = (firstValue(search.team) ?? "").toUpperCase();
  const limitRaw = Number(firstValue(search.limit));
  const limit = LIMIT_OPTIONS.includes(
    limitRaw as (typeof LIMIT_OPTIONS)[number],
  )
    ? limitRaw
    : 250;

  const board = await fetchNflPropsBoard({
    season,
    week,
    marketKey: market === "all" ? undefined : market,
    team: team || undefined,
    limit,
  });

  const hasRows = board.rows.length > 0;
  const filteredEmpty =
    !board.error &&
    !hasRows &&
    (board.diagnostics.eligibilityDropped ?? 0) > 0;
  const activeQuery = {
    season: String(season),
    week: String(week),
            market: market === "all" ? undefined : market,
            team: team || undefined,
    limit: String(limit),
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Betting Desk · Props research
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Props
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              Weekly player means from the production spine, with bands and
              market edge when a book is joined. Research rows — not a bet card.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Date: {KOSEDGE_DATE}
              {hasRows ? ` · Board as of ${asOfLabel(board.rows)}` : null}
              {` · ${season} ${formatNflWeekLabel(week, { season })}`}
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-44">
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-edge-green/40 bg-edge-green/12 px-4 py-2.5 text-center text-sm font-semibold text-edge-green hover:border-edge-green/60"
            >
              Edge Board →
            </Link>
            <Link
              href="/pro/nfl/game-boxes"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Game Boxes
            </Link>
            <Link
              href="/pro/nfl/edges"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Edges
            </Link>
          </div>
        </div>
      </section>

      {shouldShowModelUnreachableBanner({
        error: board.error,
        hasContent: hasRows,
      }) ? (
        <div className="mt-6">
          <HonestStatusBanner title="Model service unreachable" tone="amber">
            <p>{modelUnreachableCopy(board.error)}</p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {!NFL_WEEKLY_PROPS_LIVE ? (
        <div className="mt-6">
          <HonestStatusBanner title={NFL_WEEKLY_PROPS_GATE_TITLE} tone="amber">
            <p>{NFL_WEEKLY_PROPS_GATE_BODY}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href="/pro/nfl/fantasy"
                className="rounded-lg border border-edge-green/35 bg-edge-green/10 px-3 py-1.5 text-xs font-semibold text-edge-green"
              >
                Fantasy desk
              </Link>
              <Link
                href="/pro/nfl/projections"
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
              >
                Season projections
              </Link>
              <Link
                href="/edge-board/nfl"
                className="rounded-lg border border-edge-green/35 bg-edge-green/10 px-3 py-1.5 text-xs font-semibold text-edge-green"
              >
                Edge Board
              </Link>
            </div>
          </HonestStatusBanner>
        </div>
      ) : null}

      {NFL_WEEKLY_PROPS_LIVE && !board.error && !hasRows && !filteredEmpty ? (
        <div className="mt-6">
          <HonestStatusBanner
            title="Player props board fills when markets + model hooks are live"
            tone="sky"
          >
            <p>
              No live prop rows for {season} week {week} yet. Use Edge Board for
              game lines and Game Boxes for matchup depth — we don&apos;t
              backfill fake rows or wrong-week archives here.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href="/edge-board/nfl"
                className="rounded-lg border border-edge-green/35 bg-edge-green/10 px-3 py-1.5 text-xs font-semibold text-edge-green"
              >
                Edge Board
              </Link>
              <Link
                href="/pro/nfl/game-boxes"
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
              >
                Game Boxes
              </Link>
              <Link
                href="/pro/nfl/edges"
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
              >
                Edges
              </Link>
            </div>
          </HonestStatusBanner>
        </div>
      ) : null}

      {NFL_WEEKLY_PROPS_LIVE && (hasRows || filteredEmpty) ? (
        <>
          {!board.error && board.diagnostics.kosedgeOnly ? (
            <div className="mt-6">
              <HonestStatusBanner title="Model means only" tone="sky">
                <p>
                  Showing model means and fair prices. Book edge columns stay
                  blank until markets join.
                </p>
              </HonestStatusBanner>
            </div>
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
                      className={`min-h-10 rounded-lg px-3 py-2 text-sm font-semibold transition ${
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
                      limit === option
                        ? "bg-white/15 text-kos-text"
                        : "text-kos-text/60 hover:text-kos-text"
                    }`}
                  >
                    {option}
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-xl font-semibold text-kos-text">Props Board</h2>
              <p className="text-xs text-kos-text/60">
                {board.count} prop{board.count === 1 ? "" : "s"}
              </p>
            </div>

            {filteredEmpty ? (
              <p className="mt-4 text-sm text-kos-text/70">
                No investable props for this filter yet.
              </p>
            ) : (
              <>
            {/* Mobile cards */}
            <ul className="mt-4 space-y-3 md:hidden">
              {board.rows.map((row, index) => (
                <PropCard
                  key={`${row.playerId ?? row.playerName}-${row.marketKey}-${index}`}
                  row={row}
                />
              ))}
            </ul>

            {/* Desktop table */}
            <div className="mt-4 hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr className="border-b border-white/10">
                    <th className="px-3 py-2 font-semibold">Player</th>
                    <th className="px-3 py-2 font-semibold">Market</th>
                    <th className="px-3 py-2 font-semibold">Line</th>
                    <th className="px-3 py-2 font-semibold">Model mean</th>
                    <th className="px-3 py-2 font-semibold">Floor</th>
                    <th className="px-3 py-2 font-semibold">Ceiling</th>
                    <th className="px-3 py-2 font-semibold">Fair over</th>
                    <th className="px-3 py-2 font-semibold">Fair under</th>
                    <th className="px-3 py-2 font-semibold">Edge over</th>
                    <th className="px-3 py-2 font-semibold">Edge under</th>
                    <th className="px-3 py-2 font-semibold">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {board.rows.map((row, index) => (
                    <PropRow
                      key={`${row.playerId ?? row.playerName}-${row.marketKey}-${index}`}
                      row={row}
                    />
                  ))}
                </tbody>
              </table>
            </div>
              </>
            )}

            <p className="mt-4 text-xs text-kos-text/50">
              {PROPS_ELIGIBILITY_NOTE}{" "}
              {NFL_WEEKLY_PROPS_METHODS.join(" ")} For matchup depth, open{" "}
              <Link
                href="/pro/nfl/game-boxes"
                className="font-semibold text-kos-gold hover:underline"
              >
                Game Boxes
              </Link>{" "}
              or{" "}
              <Link
                href="/pro/nfl/edges"
                className="font-semibold text-kos-gold hover:underline"
              >
                Edges
              </Link>
              .
            </p>
          </section>
        </>
      ) : null}
    </main>
  );
}

function formatBand(value: number | null): string {
  return formatPropNumber(value);
}

function PropCard({ row }: { row: NflPropBoardRow }) {
  return (
    <li className="rounded-xl border border-white/10 bg-white/3 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-kos-text">{row.playerName}</p>
          <p className="text-xs text-kos-text/55">
            {row.team}
            {row.position ? ` · ${row.position}` : ""} ·{" "}
            {propMarketLabel(row.marketKey)}
          </p>
        </div>
        <span className="text-sm font-semibold text-kos-text">
          {formatPropNumber(row.line)}
        </span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-kos-text/70">
        <span>
          Model:{" "}
          <span className="font-semibold text-kos-gold">
            {formatPropNumber(row.modelMean)}
          </span>
        </span>
        <span>
          Band: {formatBand(row.modelFloor)}–{formatBand(row.modelCeiling)}
        </span>
        <span>
          Conf:{" "}
          <span className="text-edge-green">
            {formatConfidence(row.confidence)}
          </span>
        </span>
        <span>
          Edge O/U:{" "}
          {row.marketJoined
            ? `${formatEdgeProb(row.edgeOver)} / ${formatEdgeProb(row.edgeUnder)}`
            : "no mkt"}
        </span>
      </div>
    </li>
  );
}

function PropRow({ row }: { row: NflPropBoardRow }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">{row.playerName}</div>
        <div className="text-xs text-kos-text/55">
          {row.team}
          {row.position ? ` · ${row.position}` : ""}
          {row.projectionSource
            ? ` · ${row.projectionSource === "box_score" ? "MC" : "base"}`
            : ""}
        </div>
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {propMarketLabel(row.marketKey)}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-text">
        {formatPropNumber(row.line)}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        {formatPropNumber(row.modelMean)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatBand(row.modelFloor)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatBand(row.modelCeiling)}
      </td>
      <td className="px-3 py-3 text-kos-text/90">
        {formatAmericanOdds(row.fairOverPrice)}
      </td>
      <td className="px-3 py-3 text-kos-text/90">
        {formatAmericanOdds(row.fairUnderPrice)}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined ? (
          formatEdgeProb(row.edgeOver)
        ) : (
          <span className="text-kos-text/40">no mkt</span>
        )}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {row.marketJoined ? (
          formatEdgeProb(row.edgeUnder)
        ) : (
          <span className="text-kos-text/40">no mkt</span>
        )}
      </td>
      <td className="px-3 py-3 text-edge-green">
        {formatConfidence(row.confidence)}
      </td>
    </tr>
  );
}
