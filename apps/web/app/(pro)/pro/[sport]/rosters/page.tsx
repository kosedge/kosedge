import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";

export default async function RostersPage({
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
  const season = Number.isFinite(parsedSeason) && parsedSeason >= 2010 && parsedSeason <= 2100 ? parsedSeason : undefined;
  const parsedWeek = Number(filters.week);
  const week = Number.isFinite(parsedWeek) && parsedWeek >= 1 && parsedWeek <= 25 ? parsedWeek : undefined;
  const team = typeof filters.team === "string" && filters.team.trim().length > 0 ? filters.team.trim().toUpperCase() : undefined;

  return (
    <NflIntelTablePage
      endpoint="rosters"
      title="NFL Team Intel · Rosters"
      description="Team roster context with inferred role hierarchy and current injury status."
      emptyHint="Roster intel is not available yet for the selected season/week."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "position", label: "Pos" },
        { key: "player_name", label: "Player" },
        { key: "jersey_number", label: "#" },
        { key: "depth_slot", label: "Role" },
        { key: "depth_order", label: "Order" },
        { key: "role_confidence", label: "Confidence" },
        { key: "report_status", label: "Report" },
        { key: "injury", label: "Injury" },
      ]}
    />
  );
}
