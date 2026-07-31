import Link from "next/link";
import { notFound } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

/**
 * NHL Goalie Desk — starter confirmation framing for ML / totals / puck line.
 */
export default async function NhlGoalieDeskPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey !== "nhl") notFound();

  const sportName = sportDisplayLabel(sportKey);
  const games = await getTonightGames(sportKey);

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base="/pro/nhl"
      badge="NHL Betting Desk"
      title="Goalie Desk"
      summary="Starter confirmation sensitivity for moneylines and totals. Confirm the net before locking totals research — you make the picks."
      primaryHref="/edge-board/nhl"
      primaryLabel="Edge board →"
      secondaryHref="/pro/nhl/fair-lines"
      secondaryLabel="KEI Lines →"
    >
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          {
            title: "Confirmation",
            body: "Expected starter status drives ML and total baselines more than almost any other NHL input.",
          },
          {
            title: "Totals sensitivity",
            body: "Backup or uncertain starts widen totals bands — treat unconfirmed nets as research risk.",
          },
          {
            title: "Puck line",
            body: "Goalie quality shifts win probability and cover rates on −1.5 / +1.5.",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="rounded-xl border border-white/10 bg-black/35 p-4"
          >
            <h3 className="text-sm font-semibold text-kos-gold">{card.title}</h3>
            <p className="mt-2 text-xs leading-relaxed text-kos-text/70">
              {card.body}
            </p>
          </div>
        ))}
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold text-kos-text">Tonight’s slate</h2>
        <p className="mt-1 text-sm text-kos-text/65">
          {games.length > 0
            ? "Matchups from the live board. Dedicated starter confirmation feed joins here when available — we do not invent goalie names."
            : "No live NHL board rows yet. Desk remains ready without fabricated starter cards."}
        </p>

        {games.length > 0 ? (
          <>
            <div className="mt-4 grid gap-3 md:hidden">
              {games.map((g) => (
                <div
                  key={g.slug}
                  className="rounded-xl border border-white/10 bg-black/35 p-4"
                >
                  <div className="text-sm font-semibold text-kos-text">
                    {g.row.teamA?.name ?? "Away"} @{" "}
                    {g.row.teamB?.name ?? "Home"}
                  </div>
                  <p className="mt-2 text-xs text-kos-text/65">
                    Starter confirmation:{" "}
                    <span className="text-kos-gold">Pending feed</span>
                  </p>
                  <p className="mt-1 text-xs text-kos-text/55">
                    Total{" "}
                    {g.row.bestOU?.top?.label ??
                      g.row.keiOU?.top?.label ??
                      "—"}{" "}
                    · Research via Edge Board
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-4 hidden overflow-hidden rounded-2xl border border-white/10 md:block">
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                  <tr>
                    <th className="px-4 py-3">Matchup</th>
                    <th className="px-4 py-3">Away starter</th>
                    <th className="px-4 py-3">Home starter</th>
                    <th className="px-4 py-3">Total context</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((g) => (
                    <tr
                      key={g.slug}
                      className="border-t border-white/8 hover:bg-white/[0.03]"
                    >
                      <td className="px-4 py-3 font-medium text-kos-text">
                        {g.row.teamA?.name ?? "Away"} @{" "}
                        {g.row.teamB?.name ?? "Home"}
                      </td>
                      <td className="px-4 py-3 text-kos-text/55">
                        Confirmation pending
                      </td>
                      <td className="px-4 py-3 text-kos-text/55">
                        Confirmation pending
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {g.row.bestOU?.top?.label ??
                          g.row.keiOU?.top?.label ??
                          "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="mt-4 rounded-2xl border border-kos-border bg-kos-surface/30 p-6 text-sm text-kos-text/70">
            When the goalie confirmation feed is connected, expected starters
            and confirmation status will populate this desk. Until then, use
            Edge Board and team pages for market context.
          </div>
        )}
      </section>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href="/pro/nhl/edges"
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
        >
          Edges desk
        </Link>
        <Link
          href="/pro/nhl/teams"
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
        >
          Team research
        </Link>
      </div>
    </SportHubShell>
  );
}
