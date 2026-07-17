import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";

export default async function DepthChartsPage({
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
      endpoint="depth-charts"
      title="NFL Team Intel · Depth Charts"
      description="Skill-priority depth chart hierarchy with fantasy-relevant usage stats and rest-of-year projection context."
      emptyHint="Depth chart intel is not available yet for the selected season/week."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "position", label: "Pos" },
        { key: "depth_slot", label: "Slot" },
        { key: "depth_order", label: "Order" },
        { key: "player_name", label: "Player" },
        { key: "pass_yards", label: "Pass Yds" },
        { key: "pass_touchdowns", label: "Pass TD" },
        { key: "rush_yards", label: "Rush Yds" },
        { key: "receiving_yards", label: "Rec Yds" },
        { key: "receptions", label: "Rec" },
        { key: "touchdowns_scored", label: "TD" },
        { key: "fantasy_points_roy", label: "ROy FPTS" },
        { key: "pass_yards_mean", label: "ROy Pass Yds" },
        { key: "rush_yards_mean", label: "ROy Rush Yds" },
        { key: "receiving_yards_mean", label: "ROy Rec Yds" },
        { key: "receptions_mean", label: "ROy Rec" },
        { key: "anytime_td_prob", label: "ROy TD Prob" },
        { key: "role_confidence", label: "Confidence" },
        { key: "inferred_source", label: "Source" },
      ]}
    />
  );
}
