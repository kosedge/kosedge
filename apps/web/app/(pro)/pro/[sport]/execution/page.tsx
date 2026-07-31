import Link from "next/link";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import {
  fetchNflFairLines,
  formatKickoff,
  formatSpread,
  formatTotal,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";

export const dynamic = "force-dynamic";

function absOrNull(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value)) return null;
  return Math.abs(value);
}

function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((s, v) => s + v, 0) / values.length;
}

function dispersionLabel(row: NflFairLineRow): string {
  const spreadGap = absOrNull(
    (row.bestSpreadHome ?? row.marketSpreadHome) != null &&
      row.spreadHome != null
      ? (row.bestSpreadHome ?? row.marketSpreadHome)! - row.spreadHome
      : null,
  );
  const totalGap = absOrNull(
    (row.bestTotal ?? row.marketTotal) != null && row.totalMean != null
      ? (row.bestTotal ?? row.marketTotal)! - row.totalMean
      : null,
  );
  const max = Math.max(spreadGap ?? 0, totalGap ?? 0);
  if (max >= 2.5) return "Wide";
  if (max >= 1.0) return "Moderate";
  if (spreadGap != null || totalGap != null) return "Tight";
  return "—";
}

function priceQuality(row: NflFairLineRow): string {
  if (!row.marketJoined) return "Model only";
  const books = [row.bestSpreadBook, row.bestTotalBook].filter(Boolean);
  if (books.length >= 1) return "Joined";
  return "Partial";
}

export default async function ExecutionPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;

  if (sportKey === "nfl") {
    const fairLines = await fetchNflFairLines({
      season: 2026,
      daysAhead: 120,
      includePastDays: 1,
    });
    const week = fairLines.currentWeek || 1;
    const weekRows = fairLines.lines.filter(
      (row) => row.week === week || row.week === week + 1,
    );
    const rows = (
      weekRows.length > 0
        ? weekRows
        : fairLines.lines.filter((row) => (row.week ?? 99) <= 2)
    ).sort((a, b) => (a.startTime || "").localeCompare(b.startTime || ""));

    const spreadGaps = rows
      .map((r) =>
        absOrNull(
          r.spreadHome != null &&
            (r.bestSpreadHome ?? r.marketSpreadHome) != null
            ? (r.bestSpreadHome ?? r.marketSpreadHome)! - r.spreadHome
            : null,
        ),
      )
      .filter((v): v is number => v != null);
    const totalGaps = rows
      .map((r) =>
        absOrNull(
          r.totalMean != null && (r.bestTotal ?? r.marketTotal) != null
            ? (r.bestTotal ?? r.marketTotal)! - r.totalMean
            : null,
        ),
      )
      .filter((v): v is number => v != null);
    const joined = rows.filter((r) => r.marketJoined).length;
    const avgSpread = mean(spreadGaps);
    const avgTotal = mean(totalGaps);

    return (
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Week {week} · 2026 · Research diagnostic
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-kos-text">
              Execution Monitor
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-kos-text/70">
              Market dispersion, price quality, and timing context for the
              active slate. Research support only — not a pick feed.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
            >
              NFL Overview
            </Link>
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Edge Board
            </Link>
            <Link
              href="/odds/nfl"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
            >
              Compare Odds
            </Link>
          </div>
        </div>

        <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-white/10 bg-black/35 p-4">
            <h2 className="text-sm font-semibold text-kos-gold">
              Market Dispersion
            </h2>
            <p className="mt-2 text-2xl font-semibold text-kos-text">
              {avgSpread != null ? avgSpread.toFixed(1) : "—"}
              <span className="text-sm font-normal text-kos-text/50">
                {" "}
                pts avg
              </span>
            </p>
            <p className="mt-1 text-xs text-kos-text/55">
              Mean |KEI − best book| on spreads
              {avgTotal != null
                ? ` · totals ${avgTotal.toFixed(1)} pts`
                : ""}
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/35 p-4">
            <h2 className="text-sm font-semibold text-kos-gold">Price Quality</h2>
            <p className="mt-2 text-2xl font-semibold text-kos-text">
              {joined}/{rows.length}
            </p>
            <p className="mt-1 text-xs text-kos-text/55">
              Games with a joined sportsbook price · feed{" "}
              {fairLines.diagnostics.oddsFeedStatus}
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/35 p-4">
            <h2 className="text-sm font-semibold text-kos-gold">
              Line Movement & Timing
            </h2>
            <p className="mt-2 text-sm text-kos-text/75">
              Kickoffs shown in ET. Movement history populates as snapshot
              retention expands — current board shows best available number.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/35 p-4">
            <h2 className="text-sm font-semibold text-kos-gold">Book Snapshot</h2>
            <p className="mt-2 text-sm text-kos-text/75">
              {fairLines.diagnostics.bookmakers.slice(0, 8).join(" · ") ||
                "No books joined yet"}
            </p>
          </div>
        </section>

        {fairLines.error ? (
          <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
            Model service unreachable for this diagnostic window.
          </div>
        ) : null}

        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
              <tr>
                <th className="px-4 py-3">Matchup</th>
                <th className="px-4 py-3">Kickoff (ET)</th>
                <th className="px-4 py-3">Best spread</th>
                <th className="px-4 py-3">KEI</th>
                <th className="px-4 py-3">Best total</th>
                <th className="px-4 py-3">KEI</th>
                <th className="px-4 py-3">Dispersion</th>
                <th className="px-4 py-3">Price quality</th>
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
                  <td className="px-4 py-3 text-kos-gold">
                    {formatSpread(row.spreadHome)}
                  </td>
                  <td className="px-4 py-3">
                    {formatTotal(row.bestTotal ?? row.marketTotal)}
                    <span className="ml-1 text-xs text-kos-text/45">
                      {row.bestTotalBook ?? ""}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-kos-gold">
                    {formatTotal(row.totalMean)}
                  </td>
                  <td className="px-4 py-3 text-xs">{dispersionLabel(row)}</td>
                  <td className="px-4 py-3 text-xs">{priceQuality(row)}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-8 text-center text-kos-text/60"
                  >
                    No slate rows yet for the active week window.
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
