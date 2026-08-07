import { notFound } from "next/navigation";
import InjuryNewsFeedSection from "@/components/pro/InjuryNewsFeedSection";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import {
  fetchSportInjuryNewsFeed,
  getSportInjuryNewsConfig,
} from "@/lib/sport-injury-news";

const NFL_INTEL_COLUMNS = [
  { key: "team", label: "Team" },
  { key: "player_name", label: "Player" },
  { key: "report_status", label: "Report" },
  { key: "practice_status", label: "Practice" },
  { key: "injury", label: "Injury" },
  { key: "player_id", label: "Player ID" },
] as const;

export default async function InjuriesPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams: Promise<{ season?: string; week?: string; team?: string }>;
}) {
  const { sport } = await params;
  const sportKey = sport.toLowerCase();
  const config = getSportInjuryNewsConfig(sportKey);
  if (!config) notFound();

  const filters = await searchParams;
  const parsedSeason = Number(filters.season);
  const season =
    Number.isFinite(parsedSeason) &&
    parsedSeason >= 2010 &&
    parsedSeason <= 2100
      ? parsedSeason
      : undefined;
  const parsedWeek = Number(filters.week);
  const week =
    Number.isFinite(parsedWeek) && parsedWeek >= 1 && parsedWeek <= 25
      ? parsedWeek
      : undefined;
  const team =
    typeof filters.team === "string" && filters.team.trim().length > 0
      ? filters.team.trim().toUpperCase()
      : undefined;

  const injuryNews = await fetchSportInjuryNewsFeed(sportKey, 10);

  if (sportKey === "nfl") {
    return (
      <div>
        <InjuryNewsFeedSection
          sportLabel={config.sportLabel}
          items={injuryNews}
          sourceSummary={config.sourceSummary}
          emptyHint={config.emptyHint}
          campHref={config.campHref}
        />
        <NflIntelTablePage
          endpoint="injuries"
          title="NFL Team Intel · Injuries & News"
          description="Weekly injury designations and practice participation status. During camp / early preseason the desk may show the latest available prior report week until 2026 weekly rows materialize — that fallback is labeled in the header."
          emptyHint="Injury intel is not available yet for the selected season/week. Check Camp Desk for live practice notes until weekly reports land."
          season={season}
          week={week}
          team={team}
          columns={[...NFL_INTEL_COLUMNS]}
        />
      </div>
    );
  }

  return (
    <main className="pb-10">
      <InjuryNewsFeedSection
        sportLabel={config.sportLabel}
        items={injuryNews}
        sourceSummary={config.sourceSummary}
        emptyHint={config.emptyHint}
        campHref={config.campHref}
      />
      <section className="mx-auto max-w-7xl px-4 pb-8 sm:px-6">
        <div className="rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6">
          <h2 className="text-lg font-semibold text-kos-text">
            {config.sportLabel} designation tables
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-kos-text/70">
            Weekly injury designations and practice participation for{" "}
            {config.sportLabel} will populate here when the model intel tables
            are wired for this sport. Headlines above stay live from public
            feeds — KosEdge does not invent injury status.
          </p>
          <p className="mt-4 text-sm font-medium text-kos-gold/90">
            Empty designation · intel pipeline pending
          </p>
        </div>
      </section>
    </main>
  );
}
