import Link from "next/link";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import SportProHeader from "@/components/pro/SportProHeader";
import { NflDataFreshnessBanner } from "@/components/pro/NflDataFreshnessBanner";
import { loadAssembledEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";
import {
  resolveSportKey,
  sportDisplayLabel,
  SPORTS,
} from "@/lib/sports";
import { getSportOverviewHref } from "@/lib/sport-pro-nav";

export const dynamic = "force-dynamic";

async function getRows(
  sport: string,
  slate: "live" | "all",
): Promise<EdgeBoardRow[]> {
  // Direct assemble for every sport — avoids serverless self-HTTP + empty Odds pulls.
  try {
    return await loadAssembledEdgeBoardRows(sport, { slate });
  } catch {
    return [];
  }
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
  const slate: "live" | "all" =
    sportKey === "nfl" && slateRaw === "all" ? "all" : "live";

  const rows = await getRows(sportKey, slate);
  const gameCount = new Set(rows.map((r) => r.game).filter(Boolean)).size;
  const nflWeeks = [
    ...new Set(
      rows
        .map((r) => (r as { week?: number }).week)
        .filter((w): w is number => typeof w === "number" && Number.isFinite(w)),
    ),
  ].sort((a, b) => a - b);
  const nflWeekLabel =
    nflWeeks.length === 1
      ? `Week ${nflWeeks[0]} REG`
      : nflWeeks.length > 1
        ? `Weeks ${nflWeeks[0]}–${nflWeeks[nflWeeks.length - 1]} REG`
        : "REG";

  const isNfl = sportKey === "nfl";
  const marketsOnly = sportIsMarketsOnlyEdgeBoard(sportKey);

  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb" ? "Weekly Slate" : "Daily Slate";

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      <SportProHeader activeSport={sportKey} />
      {isNfl ? <NflDataFreshnessBanner /> : null}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-kos-green/10 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-56 -right-56 h-[640px] w-[640px] rounded-full bg-kos-gold/10 blur-3xl animate-pulse-slow" />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(245,185,66,0.18) 1px, transparent 1px), linear-gradient(to bottom, rgba(245,185,66,0.10) 1px, transparent 1px)",
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
                : `KEI vs Market · ${getKeiProductLabel(sportKey)}`}{" "}
              · ET
            </div>
            <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-kos-gold">
              {sportName} Edge Board
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
              {marketsOnly
                ? `Sportsbook Open/Best when available. ${keiCode} handicap is not shipped yet — KEI columns stay blank (no invented numbers). Research board, not picks.`
                : isNfl
                  ? slate === "live"
                    ? `${nflWeekLabel} research board (${gameCount || "—"} games). ${keiCode} = published fair line; Model vs KEI on Fair Lines when the blend splits. Open/Best when books post. PRE exhibitions filtered out. You make the picks.`
                    : `Forward REG slate (${nflWeekLabel}, ${gameCount || "—"} games with books). ${keiCode} = published fair line. Research board — not a picks feed. PRE filtered out.`
                  : `KEI (handicap) vs market. Live Open/Best when books post. ${keiCode} Line / Moneyline / O/U are Kosedge handicap projections — research, not picks.`}
            </p>
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

        <div className="mt-6 flex flex-wrap gap-2">
          {SPORTS.map((s) => (
            <Link
              key={s.key}
              href={`/edge-board/${s.key}`}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                s.key === sportKey
                  ? "bg-kos-gold/20 border border-kos-gold/50 text-kos-gold"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>

        {sportKey === "nfl" ? (
          <div className="mt-4 space-y-2">
            <div className="flex flex-wrap gap-2">
              <Link
                href="/edge-board/nfl"
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  slate === "live"
                    ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                    : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
                }`}
              >
                Current week
              </Link>
              <Link
                href="/edge-board/nfl?slate=all"
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  slate === "all"
                    ? "bg-kos-gold/20 border border-kos-gold/50 text-kos-gold"
                    : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
                }`}
              >
                Odds slate
              </Link>
            </div>
            <p className="text-[11px] text-gray-500 max-w-3xl">
              REG fair-lines only · Week 1 live on Current week · Odds slate =
              forward weeks with books · PRE filtered out · totals sides-only
              (no Total PLAY) · empty Open/Best means books have not posted
            </p>
          </div>
        ) : null}

        <EdgeBoard variant="full" rows={rows} sportKey={sportKey} />

        <p className="mt-6 text-xs text-gray-500">
          {rows.length
            ? `${gameCount} games${
                sportKey === "nfl"
                  ? slate === "live"
                    ? " · current week"
                    : " · with sportsbook odds"
                  : ""
              }`
            : "No slate rows yet — waiting on fair-lines / Odds (or offseason empty). Boards never invent book prices."}
        </p>
      </main>
    </div>
  );
}
