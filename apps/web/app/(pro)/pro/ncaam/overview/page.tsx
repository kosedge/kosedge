import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

export default async function NcaamOverviewPage() {
  const desk = getSportDeskConfig("ncaam");
  const content = buildSportOverviewContent("ncaam", "CBB");
  const slate = await loadOverviewSlateGames("ncaam");

  const sections = buildSportOverviewSections({
    sportKey: "ncaam",
    base: "/pro/ncaam",
    edgeBoardHref: "/edge-board/ncaam",
    content,
  }).filter((section) => {
    if (section.title === "Weekly Slate") return false;
    if (section.title.toLowerCase().includes("props")) return false;
    return true;
  });

  return (
    <OverviewSportShell
      sportKey="ncaam"
      sportLabel="CBB"
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Tempo, fair lines, and college basketball research desks."
    />
  );
}
