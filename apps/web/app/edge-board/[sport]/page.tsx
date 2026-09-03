import Link from "next/link";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import SportProHeader from "@/components/pro/SportProHeader";
import { TruthStateBadges } from "@/components/pro/TruthStateBadge";
import {
  loadAssembledEdgeBoardRows,
  normalizeNflEdgeBoardSlate,
} from "@/lib/build-edge-board-rows";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";
import { filterNflStrictWeekRows } from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { MODEL_TRANSPARENCY_HREF } from "@/lib/model-transparency-hub";
import { resolveSportKey, sportDisplayLabel, SPORTS } from "@/lib/sports";
import { getSportOverviewHref } from "@/lib/sport-pro-nav";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { marketAsOfHeaderSuffix, pickLatestIso } from "@/lib/market-asof-stamp";

export const dynamic = "force-dynamic";

async function getRows(
  sport: string,
  slate: "week1" | "full",
): Promise<EdgeBoardRow[]> {
  // Direct assemble for every sport — avoids serverless self-HTTP + empty Odds pulls.
  try {
    return await loadAssembledEdgeBoardRows(sport, { slate });
  } catch {
    return [];
  }
}

function gameCount(rows: EdgeBoardRow[]): number {
  return new Set(rows.map((r) => r.game).filter(Boolean)).size;
}

export default async function EdgeBoardSportPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ sport?: string }>)
      : ((params as { sport?: string }) ?? {});
  const sportKey = resolveSportKey(resolved?.sport, "ncaam");
  const sportName = sportDisplayLabel(sportKey);
  const keiCode = getKeiCode(sportKey);

  const sp =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<
          Record<string, string | string[] | undefined>
        >)
      : ((searchParams as Record<string, string | string[] | undefined>) ?? {});
  const slateRaw = Array.isArray(sp.slate) ? sp.slate[0] : sp.slate;
  const slate =
    sportKey === "nfl" ? normalizeNflEdgeBoardSlate(slateRaw) : "week1";
  const cfbWeekRaw = Array.isArray(sp.week) ? sp.week[0] : sp.week;
  // Live desk defaults to Week 1; Week 0 remains via ?week=0 (finals).
  const cfbWeek = sportKey === "cfb" ? (cfbWeekRaw === "0" ? 0 : 1) : 0;

  // NFL: one full assemble, then derive Week 1 (counts stay cheap; no double pull).
  let rows: EdgeBoardRow[] = [];
  let week0Count = 0;
  let week1Count = 0;
  let fullCount = 0;
  if (sportKey === "nfl") {
    // Assemble once (full), stamp schedule-pack weeks, ensure complete W1
    // membership, then derive Week 1. Schedule is the driver — never show 13
    // when the pack has 16 REG Week 1 games.
    const fullRows = ensureNflScheduleWeekOnBoard(
      stampNflEdgeBoardWeeksFromSchedule(await getRows("nfl", "full")),
      1,
    );
    const week1Rows = filterNflStrictWeekRows(fullRows, 1);
    week1Count = gameCount(week1Rows);
    fullCount = gameCount(fullRows);
    rows = slate === "full" ? fullRows : week1Rows;
  } else if (sportKey === "cfb") {
    const all = stampCfbEdgeBoardWeek(await getRows("cfb", "week1"));
    week0Count = gameCount(all.filter((r) => r.week === 0));
    week1Count = gameCount(all.filter((r) => r.week === 1));
    rows = all.filter((r) => r.week === cfbWeek);
  } else {
    rows = await getRows(sportKey, "week1");
  }

  const games = gameCount(rows);
  const nflWeeks = [
    ...new Set(
      rows
        .map((r) => (r as { week?: number }).week)
        .filter(
          (w): w is number => typeof w === "number" && Number.isFinite(w),
        ),
    ),
  ].sort((a, b) => a - b);

  const isNfl = sportKey === "nfl";
  const marketsOnly = sportIsMarketsOnlyEdgeBoard(sportKey);
  const nflLinesAsOf = isNfl
    ? pickLatestIso(...rows.map((r) => (r as { linesAsOf?: string }).linesAsOf))
    : null;
  const headerAsOf = isNfl
    ? marketAsOfHeaderSuffix({ asOf: nflLinesAsOf, kind: "lines" })
    : null;

  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb" ? "Weekly Slate" : "Daily Slate";

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      <SportProHeader activeSport={sportKey} />
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-edge-green/12 blur-3xl animate-pulse-slow" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-edge-green/10 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-56 -right-56 h-[640px] w-[640px] rounded-full bg-kos-gold/8 blur-3xl animate-pulse-slow" />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(57,255,20,0.16) 1px, transparent 1px), linear-gradient(to bottom, rgba(57,255,20,0.08) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        <div className="absolute inset-0 bg-linear-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-6 pb-16 sm:pt-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div>
            <div className="text-sm text-gray-400">
              {sportName} ·{" "}
              {marketsOnly
                ? "Markets only"
                : `KEI vs Market · ${getKeiProductLabel(sportKey)}`}
              {isNfl ? <> · {headerAsOf}</> : <> · ET</>}
            </div>
            {marketsOnly ? (
              <div className="mt-2">
                <TruthStateBadges
                  states={["LIVE"]}
                  testId={
                    sportKey === "cfb" ? "cfb-truth-state" : "truth-state"
                  }
                />
              </div>
            ) : null}
            <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-edge-green">
              {sportName} Edge Board
            </h1>
            {!isNfl ? (
              <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
                {marketsOnly
                  ? `${keiCode} handicap is not shipped — KEI stays blank (books ≠ KEI). Research board, not picks.`
                  : `KEI vs market. Model is research-fair. Tags never use Model vs market.`}{" "}
                <Link
                  href={MODEL_TRANSPARENCY_HREF}
                  className="text-kos-gold/80 hover:text-kos-gold hover:underline"
                >
                  Model transparency
                </Link>
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={getSportOverviewHref(sportKey)}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              {sportName} Overview
            </Link>
            <Link
              href={`/pro/${sportKey}/slate/today`}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              {slateLabel}
            </Link>
            <Link
              href={`/odds/${sportKey}`}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              Compare Odds
            </Link>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {SPORTS.map((s) => (
            <Link
              key={s.key}
              href={`/edge-board/${s.key}`}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                s.key === sportKey
                  ? "bg-edge-green/20 border border-edge-green/50 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                  : "bg-black/30 border border-white/12 hover:border-edge-green/35 text-gray-300"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>

        {sportKey === "cfb" ? (
          <div className="mt-3 space-y-1.5">
            <div
              className="flex flex-wrap gap-2"
              role="tablist"
              aria-label="CFB week"
            >
              <Link
                href="/edge-board/cfb?week=0"
                role="tab"
                aria-selected={cfbWeek === 0}
                className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                  cfbWeek === 0
                    ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                    : "bg-black/30 border border-white/12 text-gray-300"
                }`}
              >
                Week 0{week0Count ? ` (${week0Count})` : ""}
              </Link>
              <Link
                href="/edge-board/cfb?week=1"
                role="tab"
                aria-selected={cfbWeek === 1}
                className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                  cfbWeek === 1
                    ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                    : "bg-black/30 border border-white/12 text-gray-300"
                }`}
              >
                Week 1{week1Count ? ` (${week1Count})` : ""}
              </Link>
            </div>
            <p className="text-[11px] text-gray-500">
              Week {cfbWeek} · Tag = KEI vs trusted market · Model is
              research-only ·{" "}
              <Link
                href={MODEL_TRANSPARENCY_HREF}
                className="text-kos-gold/80 hover:text-kos-gold hover:underline"
              >
                Model transparency
              </Link>
            </p>
          </div>
        ) : null}

        {sportKey === "nfl" ? (
          <div
            className="mt-3 flex flex-wrap gap-2"
            role="tablist"
            aria-label="NFL Edge Board slate"
          >
            <Link
              href="/edge-board/nfl?slate=week1"
              role="tab"
              aria-selected={slate === "week1"}
              className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                slate === "week1"
                  ? "bg-edge-green/20 border border-edge-green/40 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              Week 1{week1Count ? ` (${week1Count})` : ""}
            </Link>
            <Link
              href="/edge-board/nfl?slate=full"
              role="tab"
              aria-selected={slate === "full"}
              className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                slate === "full"
                  ? "bg-edge-green/20 border border-edge-green/40 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              Full slate{fullCount ? ` (${fullCount})` : ""}
            </Link>
          </div>
        ) : null}

        {isNfl ? (
          <MarketAsOfStamp
            className="mt-3"
            asOf={nflLinesAsOf}
            kind="lines"
            data-testid="edge-board-asof"
          />
        ) : null}

        <EdgeBoard
          variant="full"
          rows={rows}
          sportKey={sportKey}
          slateWeek={slate === "week1" ? 1 : (nflWeeks[0] ?? null)}
          emptyHint={
            isNfl && slate === "week1"
              ? "No Week 1 REG schedule games resolved. We do not fall through to later weeks or the full slate. Switch to Full slate for the multi-week board."
              : sportKey === "cfb"
                ? "KEI rows load from the bundled W0/W1 pack. Open/Best stay empty until The Odds API returns NCAAF — we do not invent book prices."
                : undefined
          }
        />

        <p className="mt-6 text-xs text-gray-500">
          {rows.length
            ? `${games} games${
                sportKey === "nfl"
                  ? slate === "week1"
                    ? " · Week 1 REG"
                    : " · full slate"
                  : sportKey === "cfb"
                    ? ` · Week ${cfbWeek}${
                        rows.some((r) => r.best || r.open)
                          ? ""
                          : " · waiting on Odds API for Open/Best"
                      }`
                    : ""
              }`
            : isNfl && slate === "week1"
              ? "No Week 1 REG games yet — board stays empty (no silent full-slate fallthrough)."
              : "No slate rows yet — waiting on fair-lines / Odds (or offseason empty). Boards never invent book prices."}
        </p>
      </main>
    </div>
  );
}
