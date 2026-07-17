import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";

export default async function StandingsPage({
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
      endpoint="standings"
      title="NFL Team Intel · Standings"
      description="Derived weekly standings from completed schedule results."
      emptyHint="Standings intel is not available yet for the selected season/week."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "record", label: "Record" },
        { key: "win_pct", label: "Pct" },
        { key: "points_for", label: "PF" },
        { key: "points_against", label: "PA" },
        { key: "point_diff", label: "Diff" },
        { key: "conference", label: "Conf" },
        { key: "division", label: "Div" },
      ]}
    />
  );
}
