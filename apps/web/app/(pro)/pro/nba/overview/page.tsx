import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function NbaOverviewPage() {
  const desk = getSportDeskConfig("nba");
  const content = buildSportOverviewContent("nba", "NBA");
  const slate = await loadOverviewSlateGames("nba");

  // Slate lives at top — drop the duplicate Weekly Slate link wall.
  const sections = buildSportOverviewSections({
    sportKey: "nba",
    base: "/pro/nba",
    edgeBoardHref: "/edge-board/nba",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey="nba"
      sportLabel="NBA"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Power ratings, odds compare, and NBA research desks."
    />
  );
}
