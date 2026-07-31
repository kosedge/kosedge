import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";
import {
  fetchNflFairLines,
  formatAmericanOdds,
  formatKickoff,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";

export const dynamic = "force-dynamic";

type SearchValue = string | string[] | undefined;
type MarketMode = "ml" | "total";

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function mlDiff(
  kei: number | null | undefined,
  market: number | null | undefined,
): number | null {
  if (kei == null || market == null) return null;
  return kei - market;
}

function discrepancyScore(row: NflFairLineRow, mode: MarketMode): number {
  if (mode === "total") {
    const kei = row.totalMean;
    const mkt = row.bestTotal ?? row.marketTotal;
    if (kei == null || mkt == null) return 0;
    return Math.abs(kei - mkt);
  }
  const home = mlDiff(row.fairHomeMl, row.marketHomeMl);
  const away = mlDiff(row.fairAwayMl, row.marketAwayMl);
  return Math.max(Math.abs(home ?? 0), Math.abs(away ?? 0));
}

export default async function PredictionMarketPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, SearchValue>>;
}) {
  const sp = searchParams ? await searchParams : {};
  const mode: MarketMode =
    firstValue(sp.market) === "total" ? "total" : "ml";
  const weekRaw = Number(firstValue(sp.week));

  const board = await fetchNflFairLines({
    season: 2026,
    daysAhead: 120,
    includePastDays: 0,
  });
  const week =
    Number.isFinite(weekRaw) && weekRaw >= 1
      ? weekRaw
      : (board.currentWeek ?? 1);

  const rows = board.lines
    .filter((row) => row.week == null || row.week === week)
    .slice()
    .sort(
      (a, b) =>
        discrepancyScore(b, mode) - discrepancyScore(a, mode) ||
        (a.startTime ?? "").localeCompare(b.startTime ?? ""),
    );

  const largest = rows
    .filter((r) => discrepancyScore(r, mode) > 0)
    .slice(0, 5);

  const weeks = Array.from(
    new Set(
      board.lines
        .map((r) => r.week)
        .filter((w): w is number => typeof w === "number"),
    ),
  )
    .sort((a, b) => a - b)
    .slice(0, 8);

  return (
    <NflProShell
      pageTitle="Prediction Markets"
      pageSubtitle="Research comparison of KEI moneylines/totals vs sportsbooks and prediction-market venues. Kalshi, Polymarket, and Novig columns stay clean until feeds are live."
    >
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-kos-text/55">Week</span>
          {(weeks.length > 0 ? weeks : [week]).map((w) => (
            <Link
              key={w}
              href={`/pro/prediction-market?week=${w}&market=${mode}`}
              className={
                w === week
                  ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-2.5 py-1 text-xs font-semibold text-kos-gold"
                  : "rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-kos-text/70"
              }
            >
              Week {w} · 2026
            </Link>
          ))}
          <span className="mx-1 text-kos-text/25">|</span>
          <Link
            href={`/pro/prediction-market?week=${week}&market=ml`}
            className={
              mode === "ml"
                ? "rounded-md border border-edge-green/40 bg-edge-green/10 px-2.5 py-1 text-xs font-semibold text-edge-green"
                : "rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-kos-text/70"
            }
          >
            ML
          </Link>
          <Link
            href={`/pro/prediction-market?week=${week}&market=total`}
            className={
              mode === "total"
                ? "rounded-md border border-edge-green/40 bg-edge-green/10 px-2.5 py-1 text-xs font-semibold text-edge-green"
                : "rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-kos-text/70"
            }
          >
            Total
          </Link>
        </div>

        <section className="mt-6">
          <h2 className="text-lg font-semibold text-kos-text">
            Largest discrepancies
          </h2>
          <div className="mt-3 grid gap-3 md:grid-cols-5">
            {largest.length === 0 ? (
              <p className="text-sm text-kos-text/60 md:col-span-5">
                No joined market separations in this window yet.
              </p>
            ) : (
              largest.map((row) => (
                <div
                  key={row.gameId}
                  className="rounded-xl border border-white/10 bg-black/35 p-3"
                >
                  <p className="text-sm font-semibold text-kos-text">
                    {row.awayAbbr} @ {row.homeAbbr}
                  </p>
                  <p className="mt-1 text-xs text-kos-text/55">
                    {formatKickoff(row.startTime)}
                  </p>
                  <p className="mt-2 text-sm text-kos-gold">
                    Δ{" "}
                    {discrepancyScore(row, mode).toFixed(
                      mode === "total" ? 1 : 0,
                    )}
                    {mode === "total" ? " pts" : ""}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
                <th className="px-3 py-3">Matchup</th>
                <th className="px-3 py-3">Kickoff (ET)</th>
                <th className="px-3 py-3">
                  {mode === "ml" ? "KEI ML" : "KEI Total"}
                </th>
                <th className="px-3 py-3">
                  {mode === "ml" ? "Best SB ML" : "Best SB Total"}
                </th>
                <th className="px-3 py-3">Kalshi</th>
                <th className="px-3 py-3">Polymarket</th>
                <th className="px-3 py-3">Novig</th>
                <th className="px-3 py-3">KEI vs Best SB</th>
                <th className="px-3 py-3">KEI vs Pred Markets</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const bookTotal = row.bestTotal ?? row.marketTotal;
                const kei =
                  mode === "ml"
                    ? `${formatAmericanOdds(row.fairAwayMl)} / ${formatAmericanOdds(row.fairHomeMl)}`
                    : row.totalMean != null
                      ? row.totalMean.toFixed(1)
                      : "—";
                const bestSb =
                  mode === "ml"
                    ? `${formatAmericanOdds(row.marketAwayMl)} / ${formatAmericanOdds(row.marketHomeMl)}`
                    : bookTotal != null
                      ? bookTotal.toFixed(1)
                      : "—";
                const vsSb =
                  mode === "ml"
                    ? mlDiff(row.fairHomeMl, row.marketHomeMl)
                    : row.totalMean != null && bookTotal != null
                      ? row.totalMean - bookTotal
                      : null;
                return (
                  <tr
                    key={row.gameId}
                    className="border-b border-white/5 odd:bg-white/[0.02]"
                  >
                    <td className="px-3 py-2.5 font-medium text-kos-text">
                      {row.awayAbbr} @ {row.homeAbbr}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-kos-text/60">
                      {formatKickoff(row.startTime)}
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-kos-gold">
                      {kei}
                    </td>
                    <td className="px-3 py-2.5 text-kos-text/80">{bestSb}</td>
                    <td className="px-3 py-2.5 text-kos-text/35">—</td>
                    <td className="px-3 py-2.5 text-kos-text/35">—</td>
                    <td className="px-3 py-2.5 text-kos-text/35">—</td>
                    <td className="px-3 py-2.5 text-kos-text/80">
                      {vsSb == null
                        ? "—"
                        : mode === "total"
                          ? vsSb.toFixed(1)
                          : String(Math.round(vsSb))}
                    </td>
                    <td className="px-3 py-2.5 text-kos-text/35">—</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 ? (
            <p className="p-6 text-sm text-kos-text/60">
              No games in this week window yet.
            </p>
          ) : null}
        </section>

        <p className="mt-4 text-xs text-kos-text/45">
          Kalshi / Polymarket / Novig are clean research placeholders until
          venue feeds connect. Informational only — not a trading desk.
        </p>
      </main>
    </NflProShell>
  );
}
