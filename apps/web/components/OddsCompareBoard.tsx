"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";
import type {
  OddsCompareBoardPayload,
  OddsCompareBoardRow,
} from "@/lib/odds-api";
import {
  getKeiLinesBoardHref,
  getSportOverviewHref,
} from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";

type Props = {
  sportKey: string;
  sportName: string;
};

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: OddsCompareBoardPayload }
  | { status: "error" };

function BookCell({
  children,
  highlight,
}: {
  children: ReactNode;
  highlight?: boolean;
}) {
  return (
    <td
      className={[
        "py-2 px-1.5 text-center border-l border-white/10 align-top min-w-[4.25rem]",
        highlight ? "bg-kos-gold/15 text-kos-gold font-semibold" : "",
      ].join(" ")}
    >
      {children}
    </td>
  );
}

/**
 * Client-fetched Compare Odds surface.
 * Keeps multi-book lines out of the document HTML (SSR shell only).
 * As-of stamps stay honest (PR 416) — filled after the compare API returns.
 */
export default function OddsCompareBoard({ sportKey, sportName }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setState({ status: "loading" });
      try {
        const res = await fetch(`/api/odds/${sportKey}/compare`, {
          cache: "no-store",
          headers: { accept: "application/json" },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`compare ${res.status}`);
        const data = (await res.json()) as OddsCompareBoardPayload;
        if (cancelled) return;
        setState({
          status: "ready",
          data: {
            rows: Array.isArray(data.rows) ? data.rows : [],
            books: Array.isArray(data.books) ? data.books : [],
            asOf: data.asOf ?? null,
            bookAsOf: Array.isArray(data.bookAsOf) ? data.bookAsOf : [],
          },
        });
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
  }, [sportKey]);

  const rows: OddsCompareBoardRow[] =
    state.status === "ready" ? state.data.rows : [];
  const books = state.status === "ready" ? state.data.books : [];
  const asOf = state.status === "ready" ? state.data.asOf : null;
  const bookAsOf = state.status === "ready" ? state.data.bookAsOf : [];
  const stampBooks = bookAsOf
    .filter((b) => b.asOf && b.feedStatus !== "not_carried")
    .map((b) => b.label);
  // NFL always stamps; other sports stamp when rows loaded.
  const showMarketStamp =
    state.status === "ready" && (sportKey === "nfl" || rows.length > 0);
  const headerAsOf =
    state.status === "loading"
      ? "…"
      : state.status === "error"
        ? marketAsOfHeaderSuffix({ asOf: null, kind: "odds" })
        : marketAsOfHeaderSuffix({ asOf: asOf ?? null, kind: "odds" });

  return (
    <div data-testid="odds-compare-board">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div>
          <div className="text-sm text-gray-400">
            {sportName} · Market research · {headerAsOf}
          </div>
          <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-kos-gold">
            Compare Odds
          </h1>
          <p className="mt-2 text-sm text-gray-200/80 max-w-2xl">
            Best numbers across books with KEI context when available. Gold
            marks the best away spread, best ML prices, and best O/U number.
            Research surface — you make the picks.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href={getSportOverviewHref(sportKey)}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold inline-flex items-center"
          >
            {sportName} Overview
          </Link>
          <Link
            href={`/edge-board/${sportKey}`}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold inline-flex items-center"
          >
            Edge Board
          </Link>
          <Link
            href={getKeiLinesBoardHref(sportKey)}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold inline-flex items-center"
          >
            KEI Lines
          </Link>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {SPORTS.map((s) => (
          <Link
            key={s.key}
            href={`/odds/${s.key}`}
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

      {books.length > 0 ? (
        <p className="mt-4 text-xs text-gray-400">
          Books:{" "}
          {books
            .map((b) =>
              b.feedStatus === "not_carried"
                ? `${b.label} (not on feed)`
                : b.label,
            )
            .join(" · ")}
        </p>
      ) : null}
      {showMarketStamp ? (
        <MarketAsOfStamp
          className="mt-2"
          asOf={asOf}
          books={stampBooks}
          kind="odds"
          data-testid="compare-odds-asof"
        />
      ) : null}

      <section className="mt-8">
        <h2 className="text-lg font-bebas text-kos-gold tracking-wide mb-3">
          Odds by book
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Per book: away spread · moneyline (away / home) · total (Over). Main
          markets only — no live widget.
        </p>

        {state.status === "loading" ? (
          <div
            className="mt-3 rounded-2xl border border-white/12 bg-black/30 p-12 text-center text-gray-400"
            data-testid="odds-compare-loading"
          >
            Loading odds…
          </div>
        ) : null}

        {state.status === "error" ? (
          <div className="mt-3 rounded-2xl border border-white/12 bg-black/30 p-12 text-center text-gray-400">
            Odds temporarily unavailable. Refresh to try again.
          </div>
        ) : null}

        {state.status === "ready" && rows.length > 0 ? (
          <div className="mt-3 grid gap-3 lg:hidden">
            {rows.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-white/12 bg-black/40 p-4"
              >
                <div className="text-sm font-semibold text-gray-100">
                  {r.game}
                </div>
                <div className="mt-1 text-xs text-gray-400">{r.time} ET</div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div className="rounded-lg border border-white/10 bg-white/5 p-2">
                    <div className="text-[10px] uppercase text-gray-500">
                      Best spread
                    </div>
                    <div className="mt-1 font-semibold text-kos-gold tabular-nums">
                      {r.bestSpreadBook
                        ? (r.spread[r.bestSpreadBook]?.away ?? "—")
                        : "—"}
                    </div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/5 p-2">
                    <div className="text-[10px] uppercase text-gray-500">
                      Best total
                    </div>
                    <div className="mt-1 font-semibold text-kos-gold tabular-nums">
                      {r.bestTotalBook && r.total[r.bestTotalBook]?.line
                        ? `o${r.total[r.bestTotalBook]!.line}`
                        : "—"}
                    </div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/5 p-2">
                    <div className="text-[10px] uppercase text-gray-500">
                      Books
                    </div>
                    <div className="mt-1 font-semibold text-gray-200">
                      {books.length}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {state.status === "ready" ? (
          <div className="mt-3 hidden bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl lg:block">
            <div className="overflow-x-auto">
              {rows.length > 0 && books.length > 0 ? (
                <table
                  className="min-w-[1400px] w-full text-sm tabular-nums"
                  data-testid="odds-compare-table"
                >
                  <thead className="bg-white/5 text-gray-300 uppercase tracking-wide text-xs">
                    <tr className="text-left">
                      <th className="py-3 px-4 sticky left-0 bg-white/5 z-10">
                        Game
                      </th>
                      <th className="py-3 px-2">Time</th>
                      {books.map((b) => (
                        <th
                          key={b.key}
                          colSpan={3}
                          className="py-3 px-2 text-center border-l border-white/10"
                        >
                          <div>{b.label}</div>
                          {b.feedStatus === "not_carried" ? (
                            <div className="mt-0.5 text-[9px] font-normal normal-case tracking-normal text-gray-500">
                              not on feed
                            </div>
                          ) : null}
                        </th>
                      ))}
                    </tr>
                    <tr className="text-left text-gray-500 text-[10px]">
                      <th className="py-1 px-4 sticky left-0 bg-white/5 z-10" />
                      <th className="py-1 px-2" />
                      {books.map((b) => (
                        <th
                          key={`${b.key}-sub`}
                          colSpan={3}
                          className="py-1 px-2 text-center border-l border-white/10 font-normal"
                        >
                          Spread · ML · O/U
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10 text-gray-200">
                    {rows.map((r) => (
                      <tr key={r.id} className="hover:bg-white/5">
                        <td className="py-3 px-4 sticky left-0 bg-black/30 z-10 font-semibold">
                          {r.game}
                        </td>
                        <td className="py-3 px-2 text-gray-400 whitespace-nowrap text-xs">
                          {r.time}
                        </td>
                        {books.map((b) => {
                          const notCarried = b.feedStatus === "not_carried";
                          const spread = r.spread[b.key];
                          const ml = r.moneyline?.[b.key];
                          const total = r.total[b.key];
                          const isBestSpread =
                            !notCarried && r.bestSpreadBook === b.key;
                          const isBestTotal =
                            !notCarried && r.bestTotalBook === b.key;
                          const isBestMl =
                            !notCarried &&
                            (r.bestMlAwayBook === b.key ||
                              r.bestMlHomeBook === b.key);
                          if (notCarried) {
                            return [
                              <BookCell key={`${b.key}-s`}>
                                <div className="text-[11px] leading-tight text-gray-500">
                                  n/a
                                </div>
                              </BookCell>,
                              <BookCell key={`${b.key}-ml`}>
                                <div className="text-[11px] leading-tight text-gray-500">
                                  feed
                                </div>
                              </BookCell>,
                              <BookCell key={`${b.key}-t`}>
                                <div className="text-[11px] leading-tight text-gray-500">
                                  n/a
                                </div>
                              </BookCell>,
                            ];
                          }
                          return [
                            <BookCell
                              key={`${b.key}-s`}
                              highlight={isBestSpread}
                            >
                              <div className="text-[12px] leading-tight">
                                {spread?.away ?? "—"}
                              </div>
                              {spread?.awayJuice ? (
                                <div
                                  className={`text-[10px] ${isBestSpread ? "text-kos-gold/80" : "text-gray-500"}`}
                                >
                                  ({spread.awayJuice})
                                </div>
                              ) : null}
                            </BookCell>,
                            <BookCell key={`${b.key}-ml`} highlight={isBestMl}>
                              <div className="text-[11px] leading-tight">
                                {ml ? `${ml.away}` : "—"}
                              </div>
                              <div
                                className={`text-[11px] leading-tight ${isBestMl ? "text-kos-gold/90" : "text-gray-400"}`}
                              >
                                {ml ? ml.home : ""}
                              </div>
                            </BookCell>,
                            <BookCell
                              key={`${b.key}-t`}
                              highlight={isBestTotal}
                            >
                              <div className="text-[12px] leading-tight">
                                {total?.line ? `o${total.line}` : "—"}
                              </div>
                              {total?.overJuice ? (
                                <div
                                  className={`text-[10px] ${isBestTotal ? "text-kos-gold/80" : "text-gray-500"}`}
                                >
                                  ({total.overJuice})
                                </div>
                              ) : null}
                            </BookCell>,
                          ];
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-12 text-center text-gray-400">
                  No odds data yet. Ensure ODDS_API_KEY is set and games are
                  posted at the books.
                </div>
              )}
            </div>
          </div>
        ) : null}

        <p className="mt-3 text-xs text-gray-500">
          Best spread = highest away number (better juice wins ties; fresher
          stamp breaks remaining ties). Best ML = highest American price for
          that side. Best O/U = highest total (better Over juice wins ties).
          Columns marked “not on feed” are designated books The Odds API does
          not carry for this sport — not empty book posts.
        </p>
      </section>
    </div>
  );
}
