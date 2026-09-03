"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  edgeToneClass,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  formatWinProb,
} from "@/lib/nfl-board-format";
import type {
  NflFairLineRow,
  NflFairLinesResponse,
} from "@/lib/nfl-fair-lines-view-types";
import { keiRepriceDriverLine } from "@/lib/nfl-kei-driver-line";
import {
  honestEmptySlateCopy,
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";
import { formatNflBoardWeekLabel } from "@/lib/nfl-board-week-label";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { bookDisplay } from "@/lib/odds-api";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";

const PAST_WEEK_DAYS = 7;

type Slate = "week" | "season";

type Props = {
  season: number;
  slate: Slate;
  includePastDays: number;
};

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

function keiSpread(row: NflFairLineRow): number | null {
  return row.handicapSpreadHome ?? row.spreadHome;
}

function keiTotal(row: NflFairLineRow): number | null {
  return row.handicapTotal ?? row.totalMean;
}

function modelSpread(row: NflFairLineRow): number | null {
  return row.modelSpreadHome ?? keiSpread(row);
}

function modelTotal(row: NflFairLineRow): number | null {
  return row.modelTotal ?? keiTotal(row);
}

/**
 * Client-fetched KEI Lines board.
 * HTML shell is not held open on model-service fair-lines (Alex waterfall).
 */
export default function NflFairLinesClient({
  season,
  slate,
  includePastDays,
}: Props) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; board: NflFairLinesResponse }
    | { status: "error"; error?: string }
  >({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    // Bare /api/nfl/fair-lines — API already defaults season=2026. Do not append
    // ?season=2026; Alex: that URL timed out under the old 12s board cap while
    // the bare GET completed with the full 241-row board.
    const qs = new URLSearchParams();
    if (includePastDays > 0) qs.set("includePast", String(includePastDays));
    const query = qs.toString();
    const href = query ? `/api/nfl/fair-lines?${query}` : "/api/nfl/fair-lines";

    async function load() {
      setState({ status: "loading" });
      try {
        const res = await fetch(href, {
          cache: "no-store",
          headers: { accept: "application/json" },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`fair-lines ${res.status}`);
        const board = (await res.json()) as NflFairLinesResponse;
        if (cancelled) return;
        setState({ status: "ready", board });
      } catch {
        if (cancelled || controller.signal.aborted) return;
        setState({ status: "error", error: "Unable to reach KEI Lines." });
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [includePastDays]);

  const board =
    state.status === "ready"
      ? state.board
      : {
          season,
          modelVersion: "",
          asOf: null,
          oddsAsOf: null,
          currentWeek: 1,
          count: 0,
          lines: [] as NflFairLineRow[],
          window: { daysAhead: 200, includePastDays },
          diagnostics: {
            oddsFeedStatus: "unknown",
            oddsFeedError: null,
            oddsEventsSeen: 0,
            marketJoinedCount: 0,
            bookmakers: [] as string[],
            kosedgeOnly: true,
          },
          error: state.status === "error" ? state.error : undefined,
        };

  const visibleLines = useMemo(() => {
    if (slate === "season") return board.lines;
    return board.lines.filter((row) => {
      if (row.week != null && row.week === board.currentWeek) return true;
      return isInPastWindow(row.startTime, includePastDays);
    });
  }, [board.lines, board.currentWeek, slate, includePastDays]);

  const emptyHonest =
    state.status === "ready" &&
    !board.error &&
    visibleLines.length === 0 &&
    board.slateStatus &&
    board.slateStatus !== "ok";

  const hasRowsForCurrentWeek = board.lines.some(
    (row) => row.week != null && row.week === board.currentWeek,
  );
  const weekChip = formatNflBoardWeekLabel(board.currentWeek, {
    hasRowsForCurrentWeek,
    lineCount: board.lines.length,
    slateStatus: board.slateStatus,
  });

  // Model odds_as_of only (stored capture / book last_update) — PR #422.
  // Do NOT pickLatestIso row clocks — those can be fresher pull noise or invent.
  const marketAsOf =
    state.status === "ready" ? board.oddsAsOf?.trim() || null : null;
  const marketBooks = (board.diagnostics.bookmakers ?? [])
    .map((k) => bookDisplay(k))
    .filter(Boolean);
  const headerAsOf =
    state.status === "loading"
      ? "…"
      : marketAsOfHeaderSuffix({
          asOf: marketAsOf,
          kind: "lines",
        });

  return (
    <main
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10"
      data-testid="fair-lines-client"
    >
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              KEI Lines · {season} · {weekChip} · {headerAsOf}
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              KEI Lines
            </h1>
            {state.status === "ready" ? (
              <MarketAsOfStamp
                className="mt-3"
                asOf={marketAsOf}
                books={marketBooks}
                kind="lines"
                data-testid="kei-lines-asof"
              />
            ) : null}
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
              href="/edge-board/nfl"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Edge Board →
            </Link>
          </div>
        </div>
      </section>

      {state.status === "ready" &&
      shouldShowModelUnreachableBanner({
        error: board.error,
        hasContent: visibleLines.length > 0,
        slateStatus: board.slateStatus,
      }) ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {modelUnreachableCopy(board.error)}
        </section>
      ) : null}

      {state.status === "ready" && emptyHonest ? (
        <section className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/75">
          {honestEmptySlateCopy(board.slateStatus)}
        </section>
      ) : null}

      {state.status === "ready" &&
      !board.error &&
      board.diagnostics.kosedgeOnly ? (
        <section className="mt-6 rounded-2xl border border-sky-400/25 bg-sky-400/10 p-5 text-sm text-sky-100">
          Market lines unavailable — showing Kosedge lines only.
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
                    includePast:
                      includePastDays > 0 ? String(PAST_WEEK_DAYS) : undefined,
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
              includePast:
                includePastDays > 0 ? undefined : String(PAST_WEEK_DAYS),
            })}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
              includePastDays > 0
                ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-edge-green/25"
            }`}
          >
            {includePastDays > 0
              ? "Including last week ✓"
              : "Include last week"}
          </Link>
        </div>
      </section>

      {state.status === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70"
          data-testid="fair-lines-loading"
        >
          Loading KEI Lines…
        </div>
      ) : null}
      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-xl font-semibold text-kos-text">KEI Lines</h2>
          <p className="text-xs text-kos-text/60">
            {visibleLines.length} game{visibleLines.length === 1 ? "" : "s"}
            {slate === "week" ? ` · ${weekChip}` : ""}
          </p>
        </div>

        {state.status === "ready" &&
        !board.error &&
        visibleLines.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
            No lines in this window yet. Try Season slate, or wait for the next
            update.
          </div>
        ) : null}

        {state.status === "ready" && visibleLines.length > 0 ? (
          <>
            <div className="mt-4 grid gap-3 md:hidden">
              {visibleLines.map((row) => (
                <article
                  key={row.gameId}
                  className="rounded-xl border border-white/10 bg-black/35 p-4"
                >
                  <div className="text-sm font-semibold text-kos-text">
                    {row.awayAbbr} @ {row.homeAbbr}
                  </div>
                  <p className="mt-1 text-xs text-kos-text/55">
                    {formatKickoff(row.startTime)}
                  </p>
                  {keiRepriceDriverLine(row.keiReprice) ? (
                    <p className="mt-1 text-[11px] text-kos-text/45">
                      {keiRepriceDriverLine(row.keiReprice)}
                    </p>
                  ) : null}
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-kos-text/50">Model spread</div>
                      <div className="mt-0.5 text-kos-text/80">
                        {formatSpread(modelSpread(row))}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-gold/70">KEI spread</div>
                      <div className="mt-0.5 font-semibold text-kos-gold">
                        {formatSpread(keiSpread(row))}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Model total</div>
                      <div className="mt-0.5 text-kos-text/80">
                        {formatTotal(modelTotal(row))}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-gold/70">KEI total</div>
                      <div className="mt-0.5 font-semibold text-kos-gold">
                        {formatTotal(keiTotal(row))}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Fair ML</div>
                      <div className="mt-0.5 text-kos-text/80">
                        H {formatAmericanOdds(row.fairHomeMl)} / A{" "}
                        {formatAmericanOdds(row.fairAwayMl)}
                      </div>
                    </div>
                    <div>
                      <div className="text-kos-text/50">Win probs</div>
                      <div className="mt-0.5 text-kos-text/80">
                        {formatWinProb(row.homeWinProb)} /{" "}
                        {formatWinProb(row.awayWinProb)}
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
                    <th className="px-3 py-2 font-semibold">Kickoff</th>
                    <th className="px-3 py-2 font-semibold">Model spread</th>
                    <th className="px-3 py-2 font-semibold text-kos-gold/80">
                      KEI spread
                    </th>
                    <th className="px-3 py-2 font-semibold">Model total</th>
                    <th className="px-3 py-2 font-semibold text-kos-gold/80">
                      KEI total
                    </th>
                    <th className="px-3 py-2 font-semibold">Fair ML</th>
                    <th className="px-3 py-2 font-semibold">Win probs</th>
                    <th className="px-3 py-2 font-semibold">Market ML</th>
                    <th className="px-3 py-2 font-semibold">Market total</th>
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
          </>
        ) : null}
      </section>

      <p className="mt-6 text-sm text-kos-text/70">
        Weather, rest, and refs show when applied — otherwise honest
        not-applied.{" "}
        <Link
          href="/pro/model-transparency#kei-lines"
          className="text-kos-text/45 hover:text-kos-gold"
        >
          Model transparency
        </Link>
      </p>
    </main>
  );
}

function FairLineRow({ row }: { row: NflFairLineRow }) {
  const drivers = keiRepriceDriverLine(row.keiReprice);
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/5">
      <td className="px-3 py-3">
        <div className="font-semibold text-kos-text">
          {row.awayAbbr} @ {row.homeAbbr}
        </div>
        <div className="text-xs text-kos-text/55">
          {row.awayTeam} at {row.homeTeam}
        </div>
        {drivers ? (
          <div className="mt-1 max-w-xs text-[11px] leading-snug text-kos-text/40">
            {drivers}
          </div>
        ) : null}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatKickoff(row.startTime)}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatSpread(modelSpread(row))}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        {formatSpread(keiSpread(row))}
      </td>
      <td className="px-3 py-3 text-kos-text/80">
        {formatTotal(modelTotal(row))}
      </td>
      <td className="px-3 py-3 font-semibold text-kos-gold">
        {formatTotal(keiTotal(row))}
      </td>
      <td className="px-3 py-3 text-kos-text/90">
        <div>
          H {formatAmericanOdds(row.fairHomeMl)} / A{" "}
          {formatAmericanOdds(row.fairAwayMl)}
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
      <td
        className={`px-3 py-3 font-semibold ${edgeToneClass(row.mlEdgeProb)}`}
      >
        {row.mlEdgeProb === null
          ? "—"
          : `${(row.mlEdgeProb * 100).toFixed(1)}pp`}
      </td>
    </tr>
  );
}
