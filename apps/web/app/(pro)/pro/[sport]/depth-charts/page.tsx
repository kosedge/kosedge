import { notFound } from "next/navigation";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { NFL_DEPTH_SOURCE_STAMP } from "@/lib/nfl-surface-honesty";

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
      endpoint="depth-charts"
      title="NFL Depth Charts"
      description="Team-first depth by position group — starter → backup → depth with light usage context. Research surface for role and injury impact."
      sourceHonesty={NFL_DEPTH_SOURCE_STAMP}
      sourceHonestyTestId="nfl-depth-source-stamp"
      campHref="/pro/nfl/camp"
      emptyHint="Depth chart intel is not available yet for the selected season/week. Open a team hub for the richer chart view."
      season={season}
      week={week}
      team={team}
      columns={[
        { key: "team", label: "Team" },
        { key: "position", label: "Pos" },
        { key: "depth_order", label: "Depth" },
        { key: "player_name", label: "Player" },
        { key: "role_confidence", label: "Role" },
        { key: "fantasy_points_roy", label: "Usage (ROy)" },
      ]}
    />
  );
}
