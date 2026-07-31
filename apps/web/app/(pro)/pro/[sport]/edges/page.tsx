import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

/**
 * Shared Edges desk for sports without a dedicated model edges feed yet.
 * Surfaces board-derived separations honestly — never invents edge numbers.
 */
export default async function SportEdgesPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "nfl") redirect("/pro/nfl/edges");
  if (sportKey === "mlb") redirect("/pro/mlb/edges");

  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey}`;
  const desk = getSportDeskConfig(sportKey);
  const games = await getTonightGames(sportKey);

  const rows = games
    .map((g) => {
      const lineEdge = g.row.edgeLineNum ?? null;
      const totalEdge = g.row.edgeOUNum ?? null;
      const max =
        lineEdge == null && totalEdge == null
          ? null
          : Math.max(lineEdge ?? 0, totalEdge ?? 0);
      return {
        slug: g.slug,
        away: g.row.teamA?.name ?? "Away",
        home: g.row.teamB?.name ?? "Home",
        lineEdge,
        totalEdge,
        max,
        marketSpread:
          g.row.bestLine?.top?.label ?? g.row.openLine?.top?.label ?? "—",
        marketTotal:
          g.row.bestOU?.top?.label ?? g.row.openOU?.top?.label ?? "—",
        keiSpread: g.row.keiLine?.top?.label ?? "—",
        keiTotal: g.row.keiOU?.top?.label ?? "—",
        tip: g.row.time ?? null,
      };
    })
    .sort((a, b) => (b.max ?? -1) - (a.max ?? -1));

  const quantified = rows.filter((r) => r.max != null && (r.max as number) > 0);

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Betting Desk`}
      title={`${sportName} Edges`}
      summary={`Thresholded model-vs-market separations for the current slate. Desk path: ${desk.pathLabel}. Research only — you make the picks.`}
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Open edge board →"
      secondaryHref={`/pro/${sportKey}/fair-lines`}
      secondaryLabel="KEI Lines →"
    >
      {games.length === 0 ? (
        <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6">
          <p className="text-sm font-semibold text-kos-gold">
            No quantified edges on the live board yet
          </p>
          <p className="mt-2 text-sm text-kos-text/70">
            When Open/Best and KEI lines are both present, separations appear
            here. Until then, use Edge Board and Compare Odds for market
            context — we do not invent edge numbers.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href={`/edge-board/${sportKey}`}
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold"
            >
              Edge Board
            </Link>
            <Link
              href={`/odds/${sportKey}`}
              className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
            >
              Compare Odds
            </Link>
          </div>
        </div>
      ) : (
        <>
          {quantified.length > 0 ? (
            <>
              <p className="mb-3 text-sm text-kos-text/65">
                {quantified.length} matchups with model-vs-market separation on
                the current board.
              </p>
              <div className="hidden overflow-hidden rounded-2xl border border-white/10 md:block">
                <table className="w-full text-sm">
                  <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                    <tr>
                      <th className="px-4 py-3">Matchup</th>
                      <th className="px-4 py-3">Spread sep</th>
                      <th className="px-4 py-3">Total sep</th>
                      <th className="px-4 py-3">Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quantified.map((r) => (
                      <tr
                        key={r.slug}
                        className="border-t border-white/8 hover:bg-white/[0.03]"
                      >
                        <td className="px-4 py-3">
                          <Link
                            href={`/edge-board/${sportKey}`}
                            className="font-medium text-kos-text hover:text-kos-gold"
                          >
                            {r.away} @ {r.home}
                          </Link>
                        </td>
                        <td className="px-4 py-3 tabular-nums text-kos-text/80">
                          {r.lineEdge != null ? r.lineEdge.toFixed(1) : "—"}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-kos-text/80">
                          {r.totalEdge != null ? r.totalEdge.toFixed(1) : "—"}
                        </td>
                        <td className="px-4 py-3 tabular-nums font-semibold text-kos-gold">
                          {r.max != null ? r.max.toFixed(1) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="grid gap-3 md:hidden">
                {quantified.map((r) => (
                  <Link
                    key={r.slug}
                    href={`/edge-board/${sportKey}`}
                    className="rounded-xl border border-white/10 bg-black/35 p-4 transition hover:border-kos-gold/40"
                  >
                    <div className="text-sm font-semibold text-kos-text">
                      {r.away} @ {r.home}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-kos-text/70">
                      <span>
                        Spread{" "}
                        <strong className="text-kos-text">
                          {r.lineEdge != null ? r.lineEdge.toFixed(1) : "—"}
                        </strong>
                      </span>
                      <span>
                        Total{" "}
                        <strong className="text-kos-text">
                          {r.totalEdge != null ? r.totalEdge.toFixed(1) : "—"}
                        </strong>
                      </span>
                      <span>
                        Max{" "}
                        <strong className="text-kos-gold">
                          {r.max != null ? r.max.toFixed(1) : "—"}
                        </strong>
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </>
          ) : (
            <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-5">
              <p className="text-sm font-semibold text-kos-gold">
                Board slate live — model separations pending
              </p>
              <p className="mt-2 text-sm text-kos-text/70">
                {rows.length} matchups are on the board with market lines. KEI
                join is required before we publish separation numbers — we do
                not invent edges.
              </p>
            </div>
          )}

          <section className="mt-6">
            <h2 className="text-lg font-semibold text-kos-text">
              Slate market context
            </h2>
            <p className="mt-1 text-sm text-kos-text/65">
              Open/best from the board for research. Not a pick list.
            </p>
            <div className="mt-4 grid gap-3 md:hidden">
              {rows.slice(0, 20).map((r) => (
                <div
                  key={`m-${r.slug}`}
                  className="rounded-xl border border-white/10 bg-black/35 p-4"
                >
                  <div className="text-sm font-semibold text-kos-text">
                    {r.away} @ {r.home}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-kos-text/70">
                    <span>
                      Mkt spread <strong>{r.marketSpread}</strong>
                    </span>
                    <span>
                      Mkt total <strong>{r.marketTotal}</strong>
                    </span>
                    <span>
                      KEI{" "}
                      <strong className="text-kos-gold">
                        {r.keiSpread}/{r.keiTotal}
                      </strong>
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 hidden overflow-hidden rounded-2xl border border-white/10 md:block">
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                  <tr>
                    <th className="px-4 py-3">Matchup</th>
                    <th className="px-4 py-3">Market spread</th>
                    <th className="px-4 py-3">Market total</th>
                    <th className="px-4 py-3">KEI</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 40).map((r) => (
                    <tr
                      key={`d-${r.slug}`}
                      className="border-t border-white/8 hover:bg-white/[0.03]"
                    >
                      <td className="px-4 py-3 font-medium text-kos-text">
                        {r.away} @ {r.home}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {r.marketSpread}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {r.marketTotal}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-gold">
                        {r.keiSpread} / {r.keiTotal}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </SportHubShell>
  );
}
