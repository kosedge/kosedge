import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { getKeiLines } from "@/lib/kei-lines";
import { resolveKeiGames } from "@/lib/resolve-kei-lines";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

const SPORT_FAIR_LINES_COPY: Record<
  string,
  { markets: string; pendingNote: string }
> = {
  nba: {
    markets: "spreads, totals, and moneylines",
    pendingNote:
      "NBA possession-sim fair-lines are live under /pro/nba/fair-lines. Empty offseason slate is intentional.",
  },
  nhl: {
    markets: "moneylines and totals (puck line staged next)",
    pendingNote:
      "NHL fair-lines join the desk once the hockey model board is connected to Pro.",
  },
  wnba: {
    markets: "spreads, totals, and moneylines",
    pendingNote:
      "WNBA possession-sim fair-lines are live under /pro/wnba/fair-lines. Empty offseason slate is intentional.",
  },
  cfb: {
    markets: "spreads and totals with key-number awareness",
    pendingNote:
      "CFB fair-lines join the desk once the college football model board is connected to Pro.",
  },
  ncaam: {
    markets: "spreads and totals with tempo-aware baselines",
    pendingNote:
      "CBB fair-lines join the desk once the college basketball model board is connected to Pro.",
  },
};

function fmtSpread(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n > 0 ? `+${n.toFixed(1)}` : n.toFixed(1);
}

function fmtTotal(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(1);
}

export default async function FairLinesPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "nfl") redirect("/pro/nfl/fair-lines");
  if (sportKey === "mlb") redirect("/pro/mlb/fair-lines");
  if (sportKey === "nba") redirect("/pro/nba/fair-lines");
  if (sportKey === "wnba") redirect("/pro/wnba/fair-lines");
  if (sportKey === "cfb") redirect("/pro/cfb/project-game");

  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const desk = getSportDeskConfig(sportKey);
  const copy = (sportKey ? SPORT_FAIR_LINES_COPY[sportKey] : undefined) ?? {
    markets: "spreads, totals, and moneylines",
    pendingNote: `${sportName} projections are not connected to this surface yet.`,
  };

  // Prefer live model-service / file KEI; file-only is the sync fallback.
  const resolvedKei = await resolveKeiGames(sportKey);
  const keiGames =
    resolvedKei.length > 0 ? resolvedKei : getKeiLines(sportKey);
  const boardGames =
    keiGames.length === 0 ? await getTonightGames(sportKey) : [];

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Betting Desk · ET`}
      title={`${sportName} Fair Lines`}
      summary={`Model reference for ${copy.markets}. Neutral presentation — no picks. Desk path: ${desk.pathLabel}.`}
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Open edge board →"
      secondaryHref={`/odds/${sportKey}`}
      secondaryLabel="Compare odds →"
    >
      {keiGames.length > 0 ? (
        <>
          <p className="mb-3 text-sm text-kos-text/65">
            {keiGames.length} KEI projections on file. Research baselines — you
            make the picks.
          </p>

          <div className="grid gap-3 md:hidden">
            {keiGames.slice(0, 40).map((g, idx) => (
              <div
                key={g.id ?? `${g.awayTeam}-${g.homeTeam}-${idx}`}
                className="rounded-xl border border-white/10 bg-black/35 p-4"
              >
                <div className="text-sm font-semibold text-kos-text">
                  {g.awayTeam} @ {g.homeTeam}
                </div>
                {g.commenceTime ? (
                  <p className="mt-1 text-xs text-kos-text/55">
                    {g.commenceTime} · ET
                  </p>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-4 text-xs">
                  <span>
                    Spread{" "}
                    <strong className="text-kos-gold">
                      {fmtSpread(g.projSpreadHome)}
                    </strong>{" "}
                    (home)
                  </span>
                  <span>
                    Total{" "}
                    <strong className="text-kos-gold">
                      {fmtTotal(g.projTotal)}
                    </strong>
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="hidden overflow-hidden rounded-2xl border border-white/10 md:block">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-xs uppercase tracking-wide text-kos-text/60">
                <tr>
                  <th className="px-4 py-3">Matchup</th>
                  <th className="px-4 py-3">Time (ET)</th>
                  <th className="px-4 py-3">KEI spread (home)</th>
                  <th className="px-4 py-3">KEI total</th>
                </tr>
              </thead>
              <tbody>
                {keiGames.slice(0, 80).map((g, idx) => (
                  <tr
                    key={g.id ?? `${g.awayTeam}-${g.homeTeam}-${idx}`}
                    className="border-t border-white/8 hover:bg-white/[0.03]"
                  >
                    <td className="px-4 py-3 font-medium text-kos-text">
                      {g.awayTeam} @ {g.homeTeam}
                    </td>
                    <td className="px-4 py-3 text-xs text-kos-text/60">
                      {g.commenceTime ?? "—"}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-kos-gold">
                      {fmtSpread(g.projSpreadHome)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-kos-gold">
                      {fmtTotal(g.projTotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href={`/pro/kei-lines/${sportKey}`}
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold"
            >
              Full KEI table →
            </Link>
            <Link
              href={`${base}/edges`}
              className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
            >
              Edges desk →
            </Link>
          </div>
        </>
      ) : (
        <div className="space-y-5">
          <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
            <p className="text-sm font-semibold text-kos-gold">
              Model board pending
            </p>
            <p className="mt-2 text-sm text-kos-text/70 sm:text-base">
              {copy.pendingNote}
            </p>
            <p className="mt-4 text-sm text-kos-text/60">
              Until then, use the public edge board and odds compare for live
              market context. We do not invent fair prices. NFL and MLB
              fair-lines boards are live under their hubs.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href={`/edge-board/${sportKey}`}
                className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
              >
                Edge board →
              </Link>
              <Link
                href={`/odds/${sportKey}`}
                className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/35"
              >
                Compare odds →
              </Link>
            </div>
          </div>

          {boardGames.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold text-kos-text">
                Market lines on the board
              </h2>
              <p className="mt-1 text-sm text-kos-text/65">
                Sportsbook open/best from the live board — not KEI fair prices.
                Research context only.
              </p>
              <div className="mt-4 grid gap-3 md:hidden">
                {boardGames.slice(0, 24).map((g) => (
                  <div
                    key={g.slug}
                    className="rounded-xl border border-white/10 bg-black/35 p-4"
                  >
                    <div className="text-sm font-semibold text-kos-text">
                      {g.row.teamA?.name ?? "Away"} @{" "}
                      {g.row.teamB?.name ?? "Home"}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-kos-text/70">
                      <span>
                        Spread{" "}
                        <strong className="text-kos-text">
                          {g.row.bestLine?.top?.label ??
                            g.row.openLine?.top?.label ??
                            "—"}
                        </strong>
                      </span>
                      <span>
                        Total{" "}
                        <strong className="text-kos-text">
                          {g.row.bestOU?.top?.label ??
                            g.row.openOU?.top?.label ??
                            "—"}
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
                    </tr>
                  </thead>
                  <tbody>
                    {boardGames.slice(0, 40).map((g) => (
                      <tr
                        key={g.slug}
                        className="border-t border-white/8 hover:bg-white/[0.03]"
                      >
                        <td className="px-4 py-3 font-medium text-kos-text">
                          {g.row.teamA?.name ?? "Away"} @{" "}
                          {g.row.teamB?.name ?? "Home"}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-kos-text/80">
                          {g.row.bestLine?.top?.label ??
                            g.row.openLine?.top?.label ??
                            "—"}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-kos-text/80">
                          {g.row.bestOU?.top?.label ??
                            g.row.openOU?.top?.label ??
                            "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>
      )}
    </SportHubShell>
  );
}
