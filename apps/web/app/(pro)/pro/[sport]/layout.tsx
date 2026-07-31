import SportProShell from "@/components/pro/SportProShell";
import { resolveSportKey } from "@/lib/sports";

/**
 * Shared Pro chrome for every /pro/[sport]/* surface.
 * Static /pro/nfl/* also wraps via nfl/layout — nested shells are avoided by
 * letting the static NFL layout own chrome for those routes.
 */
export default async function ProSportLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ sport: string }> | { sport: string };
}) {
  const resolved = await Promise.resolve(params);
  const sport = resolveSportKey(resolved.sport, "nfl");

  // Static apps/web/app/(pro)/pro/nfl/layout.tsx already mounts SportProShell
  // for /pro/nfl/* — skip double chrome when this layout also matches.
  // Next.js route groups: [sport] and nfl/ are siblings; nfl wins for /pro/nfl.
  // This layout still runs for /pro/nba, /pro/mlb, etc.
  return <SportProShell sport={sport}>{children}</SportProShell>;
}
