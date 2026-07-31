import Link from "next/link";
import { notFound } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

/**
 * Tempo / Havoc desk for college sports (NCAAM, CFB).
 * Uses board totals context when tempo feeds are not yet joined — honest UI.
 */
export default async function SportTempoPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey !== "ncaam" && sportKey !== "cfb") notFound();

  const sportName = sportDisplayLabel(sportKey);
  const isCfb = sportKey === "cfb";
  const games = await getTonightGames(sportKey);

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={`/pro/${sportKey}`}
      badge={`${sportName} Signals Desk`}
      title={isCfb ? "Tempo & Havoc" : "Tempo Signals"}
      summary={
        isCfb
          ? "Pace and disruption context for weekly key-number translation. Research framing — not picks."
          : "Tempo and variance context for daily totals research. Conference-aware framing — not picks."
      }
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Edge board →"
      secondaryHref={`/pro/${sportKey}/fair-lines`}
      secondaryLabel="KEI Lines →"
    >
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          {
            title: "Tempo",
            body: isCfb
              ? "Possessions and play-pace profiles that stretch or compress totals bands."
              : "Adjusted tempo and possession expectation for each matchup environment.",
          },
          {
            title: isCfb ? "Havoc" : "Variance",
            body: isCfb
              ? "TFL / pressure / turnover signals that create game-script volatility."
              : "Shot and possession variance that widens totals uncertainty bands.",
          },
          {
            title: "Market translation",
            body: "Use these signals beside KEI Lines and Edge Board — never as standalone picks.",
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
        <h2 className="text-lg font-semibold text-kos-text">
          Slate tempo context
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          {games.length > 0
            ? "Totals environment from the live board while dedicated tempo feeds finish join."
            : "No live slate rows yet — desk shell stays ready without inventing pace numbers."}
        </p>

        {games.length > 0 ? (
          <div className="mt-4 grid gap-3 md:hidden">
            {games.slice(0, 12).map((g) => (
              <div
                key={g.slug}
                className="rounded-xl border border-white/10 bg-black/35 p-4"
              >
                <div className="text-sm font-semibold text-kos-text">
                  {g.row.teamA?.name ?? "Away"} @ {g.row.teamB?.name ?? "Home"}
                </div>
                <div className="mt-2 text-xs text-kos-text/65">
                  Board total:{" "}
                  <span className="tabular-nums text-kos-text">
                    {g.row.bestOU?.top?.label ??
                      g.row.keiOU?.label ??
                      "—"}
                  </span>
                  {" · "}
                  KEI:{" "}
                  <span className="tabular-nums text-kos-gold">
                    {g.row.keiOU?.label ?? "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {games.length > 0 ? (
          <div className="mt-4 hidden overflow-hidden rounded-2xl border border-white/10 md:block">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                <tr>
                  <th className="px-4 py-3">Matchup</th>
                  <th className="px-4 py-3">Market total</th>
                  <th className="px-4 py-3">KEI total</th>
                  <th className="px-4 py-3">Signal</th>
                </tr>
              </thead>
              <tbody>
                {games.slice(0, 20).map((g) => {
                  const market = g.row.bestOU?.top?.label ?? "—";
                  const kei = g.row.keiOU?.label ?? "—";
                  const sep = g.row.edgeOUNum;
                  return (
                    <tr
                      key={g.slug}
                      className="border-t border-white/8 hover:bg-white/[0.03]"
                    >
                      <td className="px-4 py-3 font-medium text-kos-text">
                        {g.row.teamA?.name ?? "Away"} @{" "}
                        {g.row.teamB?.name ?? "Home"}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-text/80">
                        {market}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-kos-gold">
                        {kei}
                      </td>
                      <td className="px-4 py-3 text-xs text-kos-text/65">
                        {sep != null && sep >= 1
                          ? `Totals separation ${sep.toFixed(1)}`
                          : "Monitoring discovery"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-kos-border bg-kos-surface/30 p-6 text-sm text-kos-text/70">
            Dedicated tempo/havoc model columns will populate this desk when the
            college feed join lands. Until then, Edge Board totals remain the
            honest research path.
          </div>
        )}
      </section>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href={`/pro/${sportKey}/edges`}
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
        >
          Edges desk
        </Link>
        <Link
          href={`/pro/${sportKey}/teams`}
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
        >
          Team research
        </Link>
      </div>
    </SportHubShell>
  );
}
