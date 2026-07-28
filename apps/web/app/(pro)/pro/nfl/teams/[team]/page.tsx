import { redirect } from "next/navigation";
import { firstQueryValue } from "@/lib/nfl-team-intel";

export default async function NflTeamPage({
  params,
  searchParams,
}: {
  params: Promise<{ team: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { team } = await params;
  const rawSearch = await searchParams;
  const query = new URLSearchParams();
  const season = firstQueryValue(rawSearch.season);
  const week = firstQueryValue(rawSearch.week);
  if (season) query.set("season", season);
  if (week) query.set("week", week);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  redirect(`/pro/nfl/teams/${team.toUpperCase()}/overview${suffix}`);
}
