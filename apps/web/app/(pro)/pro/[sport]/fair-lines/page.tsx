import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

const SPORT_FAIR_LINES_COPY: Record<
  string,
  { markets: string; pendingNote: string }
> = {
  nba: {
    markets: "spreads, totals, and moneylines",
    pendingNote:
      "NBA fair-lines join the desk once the basketball model board is connected to Pro.",
  },
  nhl: {
    markets: "moneylines and totals (puck line staged next)",
    pendingNote:
      "NHL fair-lines join the desk once the hockey model board is connected to Pro.",
  },
  wnba: {
    markets: "spreads, totals, and moneylines",
    pendingNote:
      "WNBA fair-lines join the desk once the model board is connected to Pro.",
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

export default async function FairLinesPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "nfl") redirect("/pro/nfl/fair-lines");
  if (sportKey === "mlb") redirect("/pro/mlb/fair-lines");

  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const desk = getSportDeskConfig(sportKey);
  const copy = (sportKey ? SPORT_FAIR_LINES_COPY[sportKey] : undefined) ?? {
    markets: "spreads, totals, and moneylines",
    pendingNote: `${sportName} projections are not connected to this surface yet.`,
  };

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Betting Desk`}
      title={`${sportName} Fair Lines`}
      summary={`Model reference for ${copy.markets}. Neutral presentation — no picks. Desk path: ${desk.pathLabel}.`}
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Open edge board →"
      secondaryHref={`/odds/${sportKey}`}
      secondaryLabel="Compare odds →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <p className="text-sm font-semibold text-kos-gold">
          Model board pending
        </p>
        <p className="mt-2 text-sm text-kos-text/70 sm:text-base">
          {copy.pendingNote}
        </p>
        <p className="mt-4 text-sm text-kos-text/60">
          Until then, use the public edge board and odds compare for live market
          context. NFL and MLB fair-lines boards are live under their hubs.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href={`/pro/kei-lines/${sportKey}`}
            className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
          >
            KEI projections →
          </Link>
          <Link
            href={`${base}/overview`}
            className="inline-flex rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/35"
          >
            Hub overview →
          </Link>
        </div>
      </div>
    </SportHubShell>
  );
}
