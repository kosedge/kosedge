import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function NflOverviewPage() {
  const desk = getSportDeskConfig("nfl");
  const content = buildSportOverviewContent("nfl", "NFL");
  const slate = await loadOverviewSlateGames("nfl");
  // Weekly Slate section links (Camp / Previews) stay below; elevated slate is Edge Board.
  const sections = buildSportOverviewSections({
    sportKey: "nfl",
    base: "/pro/nfl",
    edgeBoardHref: "/edge-board/nfl",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey="nfl"
      sportLabel="NFL"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Season engine, previews, governance, and schedule tools."
    />
  );
}
