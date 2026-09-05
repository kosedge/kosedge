import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function WnbaOverviewPage() {
  const desk = getSportDeskConfig("wnba");
  const content = buildSportOverviewContent("wnba", "WNBA");
  const slate = await loadOverviewSlateGames("wnba");

  const sections = buildSportOverviewSections({
    sportKey: "wnba",
    base: "/pro/wnba",
    edgeBoardHref: "/edge-board/wnba",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey="wnba"
      sportLabel="WNBA"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Fantasy, props dark, and WNBA research desks."
    />
  );
}
