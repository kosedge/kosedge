import { notFound, redirect } from "next/navigation";
import TeamResearchDetail from "@/components/pro/team-research/TeamResearchDetail";
import {
  findTeamInDirectory,
  getTeamDirectory,
  getTeamResearchSportConfig,
  isTeamResearchSport,
  listTeamResearchSportKeys,
  sportDisplayName,
} from "@/lib/team-research";

export function generateStaticParams() {
  const params: Array<{ sport: string; teamSlug: string }> = [];
  for (const sport of listTeamResearchSportKeys()) {
    if (sport === "nfl") continue;
    for (const team of getTeamDirectory(sport)) {
      params.push({ sport, teamSlug: team.slug });
    }
  }
  return params;
}

export default async function SportTeamResearchPage({
  params,
}: {
  params: Promise<{ sport: string; teamSlug: string }>;
}) {
  const { sport: sportKey, teamSlug } = await params;
  if (sportKey === "nfl") {
    redirect(`/pro/nfl/teams/${teamSlug.toUpperCase()}/overview`);
  }
  if (!isTeamResearchSport(sportKey)) notFound();

  const config = getTeamResearchSportConfig(sportKey);
  const team = findTeamInDirectory(sportKey, teamSlug);
  if (!config || !team) notFound();

  return (
    <TeamResearchDetail
      sportName={sportDisplayName(sportKey)}
      config={config}
      team={team}
    />
  );
}
