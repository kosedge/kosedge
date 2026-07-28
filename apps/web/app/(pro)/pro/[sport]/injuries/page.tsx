import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";

export default async function InjuriesPage({
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
      endpoint="injuries"
      title="NFL Team Intel · Injuries"
      description="Weekly injury designations and practice participation status."
      emptyHint="Injury intel is not available yet for the selected season/week."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "player_name", label: "Player" },
        { key: "report_status", label: "Report" },
        { key: "practice_status", label: "Practice" },
        { key: "injury", label: "Injury" },
        { key: "player_id", label: "Player ID" },
      ]}
    />
  );
}
