import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  resolveSportKey,
  sportDisplayLabel,
  supportsPropsFantasy,
} from "@/lib/sports";

const SPORT_PROPS_COPY: Record<string, string> = {
  nba: "NBA player props (points, rebounds, assists, threes) stage here once the props board is wired.",
  nhl: "NHL skater and goalie props stage here once shot and save feeds clear validation.",
  wnba: "WNBA player props stage here once usage feeds clear validation.",
  mlb: "MLB props models exist server-side; play-stake eligibility stays gated off for soft launch.",
  cfb: "College football props remain data-pending for soft launch.",
  ncaam: "College basketball props remain data-pending for soft launch.",
};

export default async function PropsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "nfl") redirect("/pro/nfl/props");
  // College sports: no props desk — send researchers to Tempo / Fair Lines.
  if (sportKey === "ncaam" || sportKey === "cfb") {
    redirect(`/pro/${sportKey}/tempo`);
  }

  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const desk = getSportDeskConfig(sportKey);
  const propsEnabled = supportsPropsFantasy(sportKey);
  const detail =
    (sportKey ? SPORT_PROPS_COPY[sportKey] : undefined) ??
    `${sportName} props are staged for this hub pending model feed validation.`;

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Betting Desk`}
      title={`${sportName} Props`}
      summary={
        propsEnabled
          ? `Prop analyzer and edge screens for ${sportName}. Desk path: ${desk.pathLabel}. Research only — you make the picks.`
          : `Props are not part of this sport’s soft-launch desk.`
      }
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Open edge board →"
      secondaryHref="/pro/props-center"
      secondaryLabel="Props center →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <p className="text-sm font-semibold text-kos-gold">
          {propsEnabled ? "Props board pending" : "Coming soon"}
        </p>
        <p className="mt-2 text-sm text-kos-text/70 sm:text-base">{detail}</p>
        <p className="mt-4 text-sm text-kos-text/60">
          NFL props are live under the NFL hub. This surface stays
          sport-specific — it will not redirect you into NFL language or
          markets.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href={`${base}/fair-lines`}
            className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
          >
            Fair lines path →
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
