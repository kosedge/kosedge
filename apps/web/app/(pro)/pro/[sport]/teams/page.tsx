import { notFound, redirect } from "next/navigation";
import TeamDirectoryIndex from "@/components/pro/team-research/TeamDirectoryIndex";
import {
  getTeamDirectory,
  getTeamResearchSportConfig,
  isTeamResearchSport,
  sportDisplayName,
} from "@/lib/team-research";

export default async function TeamsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  if (sportKey === "nfl") redirect("/pro/nfl/teams");
  if (!isTeamResearchSport(sportKey)) notFound();

  const config = getTeamResearchSportConfig(sportKey);
  if (!config) notFound();

  const sportName = sportDisplayName(sportKey);
  const teams = getTeamDirectory(sportKey);

  return (
    <TeamDirectoryIndex
      sportName={sportName}
      base={`/pro/${sportKey}`}
      config={config}
      teams={teams}
    />
  );
}
