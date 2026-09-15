import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

/** In-season Fantasy landing is this week's DFS slate, not mock/draft. */
export default function NflFantasyLandingPage() {
  redirect("/pro/nfl/dfs");
}
