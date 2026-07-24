import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getSport } from "@/lib/sports";

const SPORT_TEAMS_COPY: Record<
  string,
  { summary: string; pending: string; bullets: string[] }
> = {
  mlb: {
    summary: "Club baselines for starters, bullpens, and recent form.",
    pending:
      "MLB team directory shell — roster/intel tables ship after fair-lines and edges desk.",
    bullets: [
      "Starting pitcher identity",
      "Bullpen availability",
      "Lineup confirmation status",
    ],
  },
  nba: {
    summary: "Team baselines for pace, availability, and rotation strength.",
    pending:
      "NBA team directory shell — depth and injury intel pending model board wiring.",
    bullets: [
      "Rotation stability",
      "Availability shocks",
      "Pace / efficiency tiers",
    ],
  },
  nhl: {
    summary: "Team baselines for goalie confirmation and five-on-five form.",
    pending:
      "NHL team directory shell — goalie desk and form cards pending feed wiring.",
    bullets: [
      "Confirmed starters",
      "Five-on-five rates",
      "Special-teams context",
    ],
  },
  wnba: {
    summary: "Team baselines for usage concentration and travel context.",
    pending:
      "WNBA team directory shell — usage and travel intel pending feed wiring.",
    bullets: ["Usage leaders", "Travel / rest flags", "Efficiency tiers"],
  },
  cfb: {
    summary: "Team baselines for tempo, havoc, and weekly form.",
    pending:
      "CFB team directory shell — tempo intel pending model board wiring.",
    bullets: ["Tempo profile", "Havoc / explosives", "Key-number tendencies"],
  },
  ncaam: {
    summary: "Team baselines for tempo, variance, and efficiency.",
    pending:
      "CBB team directory shell — tempo intel pending model board wiring.",
    bullets: [
      "Tempo / possession length",
      "Variance profile",
      "Efficiency tiers",
    ],
  },
};

export default async function TeamsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  if (sportKey === "nfl") redirect("/pro/nfl/teams");

  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;
  const copy = SPORT_TEAMS_COPY[sportKey] ?? {
    summary: "Team summaries, power ratings, and opponent context.",
    pending: "Shell placeholder. Wire content source.",
    bullets: ["Form", "Ratings", "Matchup context"],
  };

  return (
    <SportHubShell
      sportName={sportName}
      base={base}
      badge={`${sportName} League Intel`}
      title={`${sportName} Teams`}
      summary={copy.summary}
      primaryHref={`/pro/power-ratings/${sportKey}`}
      primaryLabel="Power ratings →"
      secondaryHref={`/edge-board/${sportKey}`}
      secondaryLabel="Edge board →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <p className="text-sm font-semibold text-kos-gold">Directory pending</p>
        <p className="mt-2 text-sm text-kos-text/70 sm:text-base">
          {copy.pending}
        </p>
        <ul className="mt-4 grid gap-2 sm:grid-cols-3">
          {copy.bullets.map((item) => (
            <li
              key={item}
              className="rounded-xl border border-white/10 bg-white/2 px-3 py-2 text-sm text-kos-text/75"
            >
              {item}
            </li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href={`/pro/kei-lines/${sportKey}`}
            className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
          >
            KEI lines →
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
