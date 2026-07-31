import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import {
  fetchNflFairLines,
  formatKickoff,
  formatSpread,
  formatTotal,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

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
              active slate. Research support only — not a pick feed. Times in
              ET.
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs">
              <Link
                href="/pro/nfl/overview"
                className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
              >
                ← NFL Overview
              </Link>
              <Link
                href="/edge-board/nfl"
                className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
              >
                Edge Board →
              </Link>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/odds/nfl"
              className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
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
              {avgTotal != null ? ` · totals ${avgTotal.toFixed(1)} pts` : ""}
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

        {/* Mobile cards */}
        <div className="mt-8 grid gap-3 md:hidden">
          {rows.map((row) => (
            <div
              key={row.gameId}
              className="rounded-xl border border-white/10 bg-black/35 p-4"
            >
              <div className="text-sm font-semibold text-kos-text">
                {row.awayAbbr} @ {row.homeAbbr}
              </div>
              <p className="mt-1 text-xs text-kos-text/55">
                {formatKickoff(row.startTime)} ET
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <div className="text-kos-text/50">Best / KEI spread</div>
                  <div className="mt-0.5 text-kos-text">
                    {formatSpread(row.bestSpreadHome ?? row.marketSpreadHome)} /{" "}
                    <span className="text-kos-gold">
                      {formatSpread(row.spreadHome)}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-kos-text/50">Best / KEI total</div>
                  <div className="mt-0.5 text-kos-text">
                    {formatTotal(row.bestTotal ?? row.marketTotal)} /{" "}
                    <span className="text-kos-gold">
                      {formatTotal(row.totalMean)}
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-2 flex gap-3 text-xs text-kos-text/65">
                <span>{dispersionLabel(row)}</span>
                <span>{priceQuality(row)}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 hidden overflow-x-auto rounded-2xl border border-white/10 bg-black/30 md:block">
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

  // Non-NFL: board-derived execution diagnostic (honest, no invented books).
  const games = await getTonightGames(sportKey);
  const withMarket = games.filter(
    (g) =>
      (g.row.bestLine?.top?.label && g.row.bestLine.top.label !== "—") ||
      (g.row.bestOU?.top?.label && g.row.bestOU.top.label !== "—"),
  );
  const withModel = games.filter(
    (g) => g.row.keiLine?.top?.label || g.row.keiOU?.top?.label,
  );
  const separations = games
    .map((g) => Math.max(g.row.edgeLineNum ?? 0, g.row.edgeOUNum ?? 0))
    .filter((n) => n > 0);
  const avgSep = mean(separations);

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Execution · ET`}
      title={`${sportName} Execution Monitor`}
      summary="Book dispersion, timing windows, and price quality from the live board. Research diagnostic — not a pick feed."
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Edge board →"
      secondaryHref={`/odds/${sportKey}`}
      secondaryLabel="Compare odds →"
    >
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">Slate coverage</h2>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {games.length}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">Games on the live board</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">Price quality</h2>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {withMarket.length}/{games.length || 0}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">
            Games with a posted Open/Best market number
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">Model join</h2>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {withModel.length}/{games.length || 0}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">
            Games with a KEI line or total
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">
            Avg separation
          </h2>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {avgSep != null ? avgSep.toFixed(1) : "—"}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">
            Mean max |model − market| where both exist
          </p>
        </div>
      </section>

      {games.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-kos-border bg-kos-surface/30 p-6 text-sm text-kos-text/70">
          No live board rows yet for {sportName}. Execution metrics populate
          when Open/Best and KEI lines join — we do not invent dispersion.
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-3 md:hidden">
            {games.map((g) => (
              <div
                key={g.slug}
                className="rounded-xl border border-white/10 bg-black/35 p-4"
              >
                <div className="text-sm font-semibold text-kos-text">
                  {g.row.teamA?.name ?? "Away"} @ {g.row.teamB?.name ?? "Home"}
                </div>
                <p className="mt-1 text-xs text-kos-text/55">
                  {g.row.time ?? "Tip TBD"} · ET
                </p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-kos-text/50">Market</div>
                    <div className="text-kos-text">
                      {g.row.bestLine?.top?.label ?? "—"} /{" "}
                      {g.row.bestOU?.top?.label ?? "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-kos-text/50">Model</div>
                    <div className="text-kos-gold">
                      {g.row.keiLine?.top?.label ?? "—"} /{" "}
                      {g.row.keiOU?.top?.label ?? "—"}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 hidden overflow-hidden rounded-2xl border border-white/10 md:block">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                <tr>
                  <th className="px-4 py-3">Matchup</th>
                  <th className="px-4 py-3">Time (ET)</th>
                  <th className="px-4 py-3">Market</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Max sep</th>
                </tr>
              </thead>
              <tbody>
                {games.map((g) => {
                  const max = Math.max(
                    g.row.edgeLineNum ?? 0,
                    g.row.edgeOUNum ?? 0,
                  );
                  return (
                    <tr
                      key={g.slug}
                      className="border-t border-white/8 hover:bg-white/[0.03]"
                    >
                      <td className="px-4 py-3 font-medium text-kos-text">
                        {g.row.teamA?.name ?? "Away"} @{" "}
                        {g.row.teamB?.name ?? "Home"}
                      </td>
                      <td className="px-4 py-3 text-xs text-kos-text/60">
                        {g.row.time ?? "—"}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {g.row.bestLine?.top?.label ?? "—"} /{" "}
                        {g.row.bestOU?.top?.label ?? "—"}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-gold">
                        {g.row.keiLine?.top?.label ?? "—"} /{" "}
                        {g.row.keiOU?.top?.label ?? "—"}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {max > 0 ? max.toFixed(1) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </SportHubShell>
  );
}
