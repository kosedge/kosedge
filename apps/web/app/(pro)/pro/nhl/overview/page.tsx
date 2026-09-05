import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function NhlOverviewPage() {
  const desk = getSportDeskConfig("nhl");
  const content = buildSportOverviewContent("nhl", "NHL");
  const slate = await loadOverviewSlateGames("nhl");

  const sections = buildSportOverviewSections({
    sportKey: "nhl",
    base: "/pro/nhl",
    edgeBoardHref: "/edge-board/nhl",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey="nhl"
      sportLabel="NHL"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Goalie desk, fantasy, props dark, and NHL research desks."
    />
  );
}
