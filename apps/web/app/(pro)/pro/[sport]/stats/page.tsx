import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";

export default async function StatsPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams: Promise<{ season?: string; week?: string; team?: string }>;
}) {
  const { sport } = await params;
  const filters = await searchParams;
  if (sport !== "nfl") notFound();
  const parsedSeason = Number(filters.season);
  const season =
    Number.isFinite(parsedSeason) &&
    parsedSeason >= 2010 &&
    parsedSeason <= 2100
      ? parsedSeason
      : undefined;
  const parsedWeek = Number(filters.week);
  const week =
    Number.isFinite(parsedWeek) && parsedWeek >= 1 && parsedWeek <= 25
      ? parsedWeek
      : undefined;
  const team =
    typeof filters.team === "string" && filters.team.trim().length > 0
      ? filters.team.trim().toUpperCase()
      : undefined;

  return (
    <NflIntelTablePage
      endpoint="stats"
      title="NFL Team Intel · Stats"
      description="Weekly situational team profile merged with derived standings context."
      emptyHint="Stats intel is not available yet for the selected season/week."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "record", label: "Record" },
        { key: "pass_rate", label: "Pass Rate" },
        { key: "early_down_pass_rate", label: "Early Pass" },
        { key: "red_zone_td_rate", label: "RZ TD Rate" },
        { key: "epa_per_play_offense", label: "Off EPA/Play" },
        { key: "epa_per_play_defense_allowed", label: "Def EPA Allowed" },
      ]}
    />
  );
}
