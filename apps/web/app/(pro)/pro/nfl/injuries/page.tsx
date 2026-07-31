import Link from "next/link";
import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { fetchEspnInjuryNews } from "@/lib/nfl-camp-desk";

export const dynamic = "force-dynamic";

function formatPublished(value: string | null): string {
  if (!value) return "";
  const ts = Date.parse(value);
  if (!Number.isFinite(ts)) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  }).format(new Date(ts));
}

export default async function NflInjuriesPage({
  searchParams,
}: {
  searchParams: Promise<{ season?: string; week?: string; team?: string }>;
}) {
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

  const injuryNews = await fetchEspnInjuryNews(8);

  return (
    <div>
      <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/5 p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-100/80">
                Camp / preseason injury intel
              </p>
              <h2 className="mt-1 text-lg font-semibold text-kos-text">
                Fresh public availability headlines
              </h2>
              <p className="mt-1 max-w-3xl text-sm text-kos-text/70">
                Weekly designation tables below may still show the latest prior
                report week until 2026 camp reports materialize. Use these ESPN
                headlines plus the Training Camp Desk for current context.
              </p>
            </div>
            <Link
              href="/pro/nfl/camp"
              className="rounded-xl border border-kos-gold/30 bg-kos-gold/10 px-4 py-2 text-sm text-kos-gold hover:border-kos-gold/50"
            >
              Training Camp Desk
            </Link>
          </div>
          {injuryNews.length === 0 ? (
            <p className="mt-4 text-sm text-kos-text/65">
              No injury-tagged ESPN headlines in the current pull. Check Camp
              Desk beats for club-specific hubs.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {injuryNews.map((item) => (
                <li key={item.id}>
                  <a
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-xl border border-white/10 bg-black/25 p-3 transition hover:border-kos-gold/35"
                  >
                    <p className="text-[11px] uppercase tracking-wide text-kos-text/50">
                      ESPN
                      {item.published
                        ? ` · ${formatPublished(item.published)}`
                        : ""}
                    </p>
                    <p className="mt-1 font-medium text-kos-text">
                      {item.headline}
                    </p>
                    {item.description ? (
                      <p className="mt-1 text-sm text-kos-text/65">
                        {item.description}
                      </p>
                    ) : null}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <NflIntelTablePage
        endpoint="injuries"
        title="NFL Team Intel · Injuries"
        description="Weekly injury designations and practice participation status. During camp / early preseason the desk may show the latest available prior report week until 2026 weekly rows materialize — that fallback is labeled in the header."
        emptyHint="Injury intel is not available yet for the selected season/week. Check Training Camp Desk for public beat updates until weekly reports land."
        season={season}
        week={week}
        team={team}
        columns={[
          { key: "team", label: "Team" },
          { key: "player_name", label: "Player" },
          { key: "report_status", label: "Report" },
          { key: "practice_status", label: "Practice" },
          { key: "injury", label: "Injury" },
          { key: "player_id", label: "Player ID" },
        ]}
      />
    </div>
  );
}
