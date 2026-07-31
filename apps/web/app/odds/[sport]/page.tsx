import Link from "next/link";
import { headers } from "next/headers";
import type { ReactNode } from "react";
import NflProHeader from "@/components/pro/nfl/NflProHeader";
import {
  resolveSportKey,
  sportDisplayLabel,
  SPORTS,
} from "@/lib/sports";
import type { OddsComparisonRow } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

async function getRequestOrigin(): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

type CompareApiResponse = {
  rows: OddsComparisonRow[];
  books: { key: string; label: string }[];
};

/** Use cached API so we don't burn Odds API credits on every page load. */
async function getOddsData(
  sportKey: string,
  origin: string,
): Promise<CompareApiResponse> {
  const res = await fetch(`${origin}/api/odds/${sportKey}/compare`, {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!res.ok) return { rows: [], books: [] };
  const data = (await res.json()) as CompareApiResponse;
  return {
    rows: Array.isArray(data.rows) ? data.rows : [],
    books: Array.isArray(data.books) ? data.books : [],
  };
}

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

export default async function OddsComparePage({
  params,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ sport?: string }>)
      : ((params as { sport?: string }) ?? {});
  const sportKey = resolveSportKey(resolved?.sport, "nfl");
  const sportName = sportDisplayLabel(sportKey);

  const origin = await getRequestOrigin();
  const { rows, books } = await getOddsData(sportKey, origin);
  const isNfl = sportKey === "nfl";

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      {isNfl ? <NflProHeader activeSport="nfl" /> : null}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-8 pb-16">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div>
            <div className="text-sm text-gray-400">
              {sportName} · Market research
            </div>
            <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-kos-gold">
              Compare Odds
            </h1>
            <p className="mt-2 text-sm text-gray-200/80 max-w-2xl">
              Best numbers across books with KEI context when available. Gold
              marks the best away spread, best ML prices, and best O/U number.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {isNfl ? (
              <Link
                href="/pro/nfl/overview"
                className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
              >
                NFL Overview
              </Link>
            ) : (
              <Link
                href="/"
                className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
              >
                ← Home
              </Link>
            )}
            <Link
              href={`/edge-board/${sportKey}`}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
            >
              Edge Board
            </Link>
            {isNfl ? (
              <Link
                href="/pro/nfl/fair-lines"
                className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
              >
                KEI Lines
              </Link>
            ) : null}
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
            Books: {books.map((b) => b.label).join(" · ")}
          </p>
        ) : null}

        <section className="mt-8">
          <h2 className="text-lg font-bebas text-kos-gold tracking-wide mb-3">
            Odds by book
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            Per book: away spread · moneyline (away / home) · total (Over). Main
            markets only — no live widget.
          </p>
          <div className="mt-3 bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
            <div className="overflow-x-auto">
              {rows.length > 0 && books.length > 0 ? (
                <table className="min-w-[1400px] w-full text-sm tabular-nums">
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
                          {b.label}
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
                          const spread = r.spread[b.key];
                          const ml = r.moneyline?.[b.key];
                          const total = r.total[b.key];
                          const isBestSpread = r.bestSpreadBook === b.key;
                          const isBestTotal = r.bestTotalBook === b.key;
                          const isBestMl =
                            r.bestMlAwayBook === b.key ||
                            r.bestMlHomeBook === b.key;
                          return [
                            <BookCell key={`${b.key}-s`} highlight={isBestSpread}>
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
                            <BookCell key={`${b.key}-t`} highlight={isBestTotal}>
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
          <p className="mt-3 text-xs text-gray-500">
            Best spread = highest away number (better juice wins ties). Best ML =
            highest American price for that side. Best O/U = highest total
            (better Over juice wins ties).
          </p>
        </section>
      </main>
    </div>
  );
}
