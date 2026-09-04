"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { formatKickoff } from "@/lib/nfl-board-format";
import type {
  DeskEdgeRow,
  DeskMarketType,
  NflEdgesDeskResponse,
} from "@/lib/nfl-edges-desk-types";
import { EDGES_DESK_MIN_CONF_OPTIONS } from "@/lib/nfl-dead-tiers";
import {
  NFL_EDGES_DESK_SUMMARY,
  NFL_EDGES_DESK_TITLE,
} from "@/lib/edges-desk-honesty";
import { nflPropsSurfaceCopy } from "@/lib/nfl-props-surface";
import {
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { bookDisplay } from "@/lib/odds-api";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";

const MARKET_TABS: DeskMarketType[] = ["all", "ml", "spread", "total", "props"];
const MIN_EDGE_OPTIONS = [
  { label: "1pp / 0.5pt", prob: 0.01, line: 0.5 },
  { label: "2pp / 1pt", prob: 0.02, line: 1.0 },
  { label: "3pp / 1.5pt", prob: 0.03, line: 1.5 },
] as const;
const MIN_CONF_OPTIONS = EDGES_DESK_MIN_CONF_OPTIONS;

type Props = {
  season: number;
  week: number;
  market: DeskMarketType;
  minEdgeIdx: number;
  minConfidence: number;
};

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

/**
 * Client-fetched Edges desk.
 * HTML shell is not held open on fair-lines ∥ today ∥ props (Alex waterfall).
 */
export default function NflEdgesDeskClient({
  season,
  week,
  market,
  minEdgeIdx,
  minConfidence,
}: Props) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; desk: NflEdgesDeskResponse }
    | { status: "error" }
  >({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const qs = new URLSearchParams({
      season: String(season),
      week: String(week),
      minEdge: String(minEdgeIdx),
    });
    if (market !== "all") qs.set("market", market);
    if (minConfidence > 0) qs.set("minConf", String(minConfidence));

    async function load() {
      setState({ status: "loading" });
      try {
        const res = await fetch(`/api/nfl/edges-desk?${qs}`, {
          cache: "no-store",
          headers: { accept: "application/json" },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`edges-desk ${res.status}`);
        const desk = (await res.json()) as NflEdgesDeskResponse;
        if (cancelled) return;
        setState({ status: "ready", desk });
      } catch {
        if (cancelled || controller.signal.aborted) return;
        setState({ status: "error" });
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [season, week, market, minEdgeIdx, minConfidence]);

  const activeQuery = {
    season: String(season),
    week: String(week),
    market: market === "all" ? undefined : market,
    minEdge: String(minEdgeIdx),
    minConf: minConfidence > 0 ? String(minConfidence) : undefined,
  };

  const deskReady = state.status === "ready" ? state.desk : null;

  const fetchError =
    deskReady &&
    deskReady.diagnostics.fairLinesError &&
    deskReady.diagnostics.edgesTodayError &&
    deskReady.diagnostics.propsError
      ? deskReady.diagnostics.fairLinesError
      : state.status === "error"
        ? "Unable to reach edges desk."
        : undefined;
  const propsCopy = deskReady
    ? nflPropsSurfaceCopy(deskReady.propsSurface)
    : null;
  const headerAsOf =
    state.status === "loading"
      ? "…"
      : marketAsOfHeaderSuffix({
          asOf: deskReady?.marketAsOf ?? null,
          kind: "market",
        });

  return (
    <main
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10"
      data-testid="edges-desk-client"
    >
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              Week {week} · {season} · {headerAsOf}
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              {NFL_EDGES_DESK_TITLE}
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              {NFL_EDGES_DESK_SUMMARY}
            </p>
            {deskReady ? (
              <MarketAsOfStamp
                className="mt-3"
                asOf={deskReady.marketAsOf}
                books={deskReady.marketBooks.map((k) => bookDisplay(k))}
                kind="market"
                data-testid="edges-desk-asof"
              />
            ) : null}
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

      {shouldShowModelUnreachableBanner({
        error: fetchError,
        hasContent: (deskReady?.rows.length ?? 0) > 0,
      }) ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {modelUnreachableCopy(fetchError)}
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
            Edges · Week {week} · {season} · {headerAsOf}
          </h2>
        </div>

        {state.status === "loading" ? (
          <div
            className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70"
            data-testid="edges-desk-loading"
          >
            Loading edges…
          </div>
        ) : null}

        {deskReady && deskReady.propsSurface !== "book-joined" && propsCopy ? (
          <p className="mt-3 text-xs text-kos-text/55">
            Props: {propsCopy.title}. {propsCopy.body}{" "}
            <Link
              href="/pro/nfl/props"
              className="text-kos-gold/80 hover:text-kos-gold hover:underline"
            >
              Props board
            </Link>
          </p>
        ) : null}

        {deskReady && !fetchError && deskReady.rows.length === 0 ? (
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

        {deskReady && deskReady.rows.length > 0 ? (
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
                {deskReady.rows.map((row) => (
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
      <td className="px-3 py-3 text-kos-text/90">{row.marketLine}</td>
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
