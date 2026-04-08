import Link from "next/link";
import { headers } from "next/headers";
import { env } from "@/lib/config/env";
import { getSport, SPORTS } from "@/lib/sports";
import type { OddsComparisonRow } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

/** Sports that have the live odds widget (key kept server-side). Rest show shell. */
const WIDGET_SPORTS: string[] = ["ncaam"];

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
  if (!res.ok)
    return { rows: [], books: [] };
  const data = (await res.json()) as CompareApiResponse;
  return {
    rows: Array.isArray(data.rows) ? data.rows : [],
    books: Array.isArray(data.books) ? data.books : [],
  };
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
  const sportKey = String(resolved?.sport ?? "ncaam");
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const hasWidget =
    env.ODDS_WIDGET_ACCESS_KEY?.trim() && WIDGET_SPORTS.includes(sportKey);

  const origin = await getRequestOrigin();
  const { rows, books } = await getOddsData(sportKey, origin);

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-10 pb-16">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div>
            <div className="text-sm text-gray-400">{sportName} • Odds</div>
            <h1 className="text-5xl font-bebas tracking-tight text-kos-gold">
              Live Odds
            </h1>
            <p className="mt-2 text-sm text-gray-200/80 max-w-2xl">
              Widget and comparison by book. Key is kept server-side.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
            >
              ← Home
            </Link>
            <Link
              href={`/edge-board/${sportKey}`}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 transition font-semibold"
            >
              Edge Board
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

        {/* Live odds widget (proxied so key never hits the client) or shell */}
        <section className="mt-6">
          <h2 className="text-lg font-bebas text-kos-gold tracking-wide mb-3">
            Live odds widget
          </h2>
          {hasWidget ? (
            <div className="rounded-2xl border border-white/12 bg-black/30 overflow-hidden shadow-xl">
              <iframe
                title={`${sportName} odds`}
                src={`${origin}/api/odds-widget/${sportKey}`}
                className="w-full min-h-[25rem] border-0"
                style={{ height: "28rem" }}
              />
            </div>
          ) : (
            <div className="rounded-2xl border border-white/12 bg-black/30 border-dashed p-12 text-center text-gray-500">
              {WIDGET_SPORTS.includes(sportKey)
                ? "Set ODDS_WIDGET_ACCESS_KEY in .env to show the widget."
                : "Widget for this sport coming soon. Add your widget URL when ready."}
            </div>
          )}
        </section>

        {/* Compare odds table */}
        <section className="mt-8">
          <h2 className="text-lg font-bebas text-kos-gold tracking-wide mb-3">
            Compare odds by book
          </h2>
          <div className="mt-3 bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
            <div className="overflow-x-auto">
              {rows.length > 0 ? (
                <table className="min-w-[900px] w-full text-sm tabular-nums">
                  <thead className="bg-white/5 text-gray-300 uppercase tracking-wide text-xs">
                    <tr className="text-left">
                      <th className="py-3 px-4 sticky left-0 bg-white/5 z-10">
                        Game
                      </th>
                      <th className="py-3 px-2">Time</th>
                      {books.map((b) => (
                        <th
                          key={b.key}
                          colSpan={2}
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
                          key={b.key}
                          colSpan={2}
                          className="py-1 px-2 text-center border-l border-white/10"
                        >
                          Spread | Total
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
                        <td className="py-3 px-2 text-gray-400">{r.time}</td>
                        {books.map((b) => {
                          const spread = r.spread[b.key];
                          const total = r.total[b.key];
                          return (
                            <td
                              key={b.key}
                              colSpan={2}
                              className="py-3 px-2 text-center border-l border-white/10"
                            >
                              <span className="text-kos-gold">
                                {spread?.away ?? "—"}
                              </span>
                              <span className="text-gray-500 mx-1">/</span>
                              <span>{total ?? "—"}</span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-12 text-center text-gray-400">
                  No odds data. Add ODDS_API_KEY and ensure games are in season.
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
