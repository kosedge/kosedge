import { redirect } from "next/navigation";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import OverviewSportShell from "@/components/pro/OverviewSportShell";
import { loadOverviewSlateGames } from "@/lib/overview-slate-games";

/**
 * Fallback Overview for any sport without a dedicated page.
 * NFL/NBA/MLB/NHL/WNBA/NCAAM/CFB have dedicated routes — this stays as a
 * shared shell so hubs cannot drift back to the old dual-card hero.
 */
export default async function SportOverviewPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);

  // Dedicated overviews own these keys.
  if (
    sportKey === "nfl" ||
    sportKey === "nba" ||
    sportKey === "mlb" ||
    sportKey === "nhl" ||
    sportKey === "wnba" ||
    sportKey === "ncaam" ||
    sportKey === "cfb"
  ) {
    redirect(`/pro/${sportKey}/overview`);
  }

  const sportName = sportDisplayLabel(sportKey);
  const desk = getSportDeskConfig(sportKey);
  const content = buildSportOverviewContent(sportKey, sportName);
  const slate = await loadOverviewSlateGames(sportKey);
  const edgeBoardHref = `/edge-board/${sportKey || "nfl"}`;
  const sections = buildSportOverviewSections({
    sportKey,
    base: `/pro/${sportKey || "nfl"}`,
    edgeBoardHref,
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <OverviewSportShell
      sportKey={sportKey || "nfl"}
      sportLabel={sportName}
      slate={slate}
      sections={sections}
      footerCards={desk.footerCards}
      toolsSubtitle="Power ratings, odds compare, and research desks."
    />
  );
}
