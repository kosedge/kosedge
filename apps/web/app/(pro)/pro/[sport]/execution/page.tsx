import Link from "next/link";
import { getSport } from "@/lib/sports";
import {
  fetchNflFairLines,
  formatKickoff,
  formatSpread,
  formatTotal,
} from "@/lib/nfl-fair-lines";

export const dynamic = "force-dynamic";

export default async function ExecutionPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;

  if (sportKey === "nfl") {
    const fairLines = await fetchNflFairLines({
      season: 2026,
      daysAhead: 21,
      includePastDays: 1,
    });
    const week = fairLines.currentWeek || 1;
    const rows = fairLines.lines
      .filter((row) => row.week === week || row.week === week + 1)
      .sort((a, b) => (a.startTime || "").localeCompare(b.startTime || ""));

    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-semibold text-kos-text">
              NFL Execution Monitor
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-kos-text/70">
              Best numbers by book, market-vs-model separation, and timing
              context for the active slate. Execution support only — not a
              pick feed.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Weeks {week}–{week + 1} · {rows.length} games · odds{" "}
              {fairLines.diagnostics.oddsFeedStatus} · books{" "}
              {fairLines.diagnostics.bookmakers.slice(0, 6).join(", ") || "—"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`${base}/overview`}
              className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
            >
              Back to Hub
            </Link>
            <Link
              href="/odds/nfl"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
            >
              Compare Odds
            </Link>
          </div>
        </div>

        {fairLines.error ? (
          <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
            {fairLines.error}
          </div>
        ) : null}

        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
              <tr>
                <th className="px-4 py-3">Matchup</th>
                <th className="px-4 py-3">Kickoff</th>
                <th className="px-4 py-3">Best spread</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Best total</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Tags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.gameId}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-4 py-3 font-medium">
                    {row.awayAbbr} @ {row.homeAbbr}
                  </td>
                  <td className="px-4 py-3 text-kos-text/65">
                    {formatKickoff(row.startTime)}
                  </td>
                  <td className="px-4 py-3">
                    {formatSpread(row.bestSpreadHome ?? row.marketSpreadHome)}
                    <span className="ml-1 text-xs text-kos-text/45">
                      {row.bestSpreadBook ?? ""}
                    </span>
                  </td>
                  <td className="px-4 py-3">{formatSpread(row.spreadHome)}</td>
                  <td className="px-4 py-3">
                    {formatTotal(row.bestTotal ?? row.marketTotal)}
                    <span className="ml-1 text-xs text-kos-text/45">
                      {row.bestTotalBook ?? ""}
                    </span>
                  </td>
                  <td className="px-4 py-3">{formatTotal(row.totalMean)}</td>
                  <td className="px-4 py-3 text-xs">
                    S:{row.publishTagSpread ?? "—"} · T:
                    {row.publishTagTotal ?? "—"}
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-kos-text/60"
                  >
                    No executable slate rows yet for the active week window.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">
            {sportName} Execution
          </h2>
          <p className="mt-2 text-kos-text/70">
            Best numbers by book, dispersion, timing. Execution support only.
          </p>
        </div>
        <Link
          href={`${base}/overview`}
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          Back to Hub
        </Link>
      </div>
      <div className="mt-8 rounded-2xl border border-kos-border bg-kos-surface/30 p-8">
        <p className="text-kos-text/60">
          Execution monitor is live for NFL. Other sports wire as market feeds
          clear launch quality.
        </p>
      </div>
    </main>
  );
}
