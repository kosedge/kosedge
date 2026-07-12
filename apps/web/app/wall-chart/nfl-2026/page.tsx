import type { Metadata } from "next";
import { NflWallChart2026 } from "@/components/wall-chart/NflWallChart2026";
import { NFL_WALL_CHART_SEASON } from "@/lib/nfl-wall-chart-2026";

export const metadata: Metadata = {
  title: `${NFL_WALL_CHART_SEASON} NFL Wall Chart`,
  description: `Printable Kosedge ${NFL_WALL_CHART_SEASON} NFL wall chart for 24×18 laminated paper with wet-erase tracking.`,
};

export default function NflWallChart2026Page() {
  return <NflWallChart2026 />;
}
