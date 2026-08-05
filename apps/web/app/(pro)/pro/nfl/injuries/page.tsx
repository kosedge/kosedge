import Link from "next/link";
import InjuryNewsFeedSection from "@/components/pro/InjuryNewsFeedSection";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { fetchInjuryNewsFeed } from "@/lib/nfl-injury-news";

export const dynamic = "force-dynamic";

export default async function NflInjuriesPage({
  searchParams,
}: {
  searchParams: Promise<{ season?: string; week?: string; team?: string }>;
}) {
  const filters = await searchParams;
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

  const injuryNews = await fetchInjuryNewsFeed(10);

  return (
    <div>
      <InjuryNewsFeedSection
        sportLabel="NFL"
        items={injuryNews}
        sourceSummary="Aggregated from ESPN, RotoWire, Rotoworld, and VSiN beat feeds."
        emptyHint="No injury headlines in the current multi-source pull. Check Camp Desk beats for club-specific hubs."
        campHref="/pro/nfl/camp"
      />

      <NflIntelTablePage
        endpoint="injuries"
        title="NFL Team Intel · Injuries & News"
        description="Weekly injury designations and practice participation status. During camp / early preseason the desk may show the latest available prior report week until 2026 weekly rows materialize — that fallback is labeled in the header."
        emptyHint="Injury intel is not available yet for the selected season/week. Check Training Camp Desk for public beat updates until weekly reports land."
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
    </div>
  );
}
