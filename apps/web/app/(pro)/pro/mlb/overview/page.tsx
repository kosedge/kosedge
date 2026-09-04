import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function MlbOverviewPage() {
  const desk = getSportDeskConfig("mlb");
  const content = buildSportOverviewContent("mlb", "MLB");
  const slate = await loadOverviewSlateGames("mlb");

  // Slate lives at top — drop the duplicate Weekly Slate link wall.
  const sections = buildSportOverviewSections({
    sportKey: "mlb",
    base: "/pro/mlb",
    edgeBoardHref: "/edge-board/mlb",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey="mlb"
      sportLabel="MLB"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Power ratings, odds compare, and MLB research desks."
    />
  );
}
