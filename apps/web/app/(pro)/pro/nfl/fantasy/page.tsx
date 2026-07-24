import Link from "next/link";
import {
  draftPositionBadgeClass,
  draftTierBadgeClass,
  draftTierLabel,
  fantasyPointsPerGame,
  fetchNflFantasyDraftRankings,
  FANTASY_DRAFT_POSITIONS,
  FANTASY_SCORING_PROFILES,
  type FantasyScoringProfile,
  type NflFantasyDraftRankingRow,
} from "@/lib/nfl-fantasy-draft";

const DEFAULT_SEASON = 2026;
const POSITION_TABS = ["ALL", ...FANTASY_DRAFT_POSITIONS] as const;
const LIMIT_OPTIONS = [50, 100, 200, 300] as const;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function isScoringProfile(
  value: string | undefined,
): value is FantasyScoringProfile {
  return value === "standard" || value === "half_ppr" || value === "ppr";
}

function buildHref(base: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(base)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/pro/nfl/fantasy?${query}` : "/pro/nfl/fantasy";
}

export default async function NflFantasyDraftBoardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const position = (firstValue(search.position) ?? "ALL").toUpperCase();
  const scoringRaw = firstValue(search.scoring);
  const scoring: FantasyScoringProfile = isScoringProfile(scoringRaw)
    ? scoringRaw
    : "half_ppr";
  const rookiesOnly = firstValue(search.rookies) === "1";
  const limitRaw = Number(firstValue(search.limit));
  const limit = LIMIT_OPTIONS.includes(
    limitRaw as (typeof LIMIT_OPTIONS)[number],
  )
    ? limitRaw
    : 100;
  const season = DEFAULT_SEASON;

  const board = await fetchNflFantasyDraftRankings({
    season,
    scoringProfile: scoring,
    position: position === "ALL" ? undefined : position,
    rookiesOnly,
    limit,
  });

  const overallLeader = board.rows[0];
  const bestValue = [...board.rows].sort(
    (a, b) => b.valueOverReplacement - a.valueOverReplacement,
  )[0];
  const bestRookie = board.rows
    .filter((row) => row.isRookie)
    .sort((a, b) => a.rankOverall - b.rankOverall)[0];
  const activeQuery = {
    scoring,
    rookies: rookiesOnly ? "1" : undefined,
    limit: String(limit),
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} Fantasy Draft Board
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Beat Your Fantasy League
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Full season-long draft board across QB/RB/WR/TE/K/DST, ranked by
              Value Over Replacement (VOR) so the board mirrors how single-QB
              drafts actually play out — not just raw point totals. Switch
              scoring format and position to build your cheat sheet.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Back to NFL Overview
            </Link>
            <Link
              href="/pro/nfl/awards"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              MVP &amp; OPOY Race →
            </Link>
          </div>
        </div>
      </section>

      {board.error ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {board.error} The draft board will populate once the model service is
          reachable.
        </section>
      ) : (
        <>
          <section className="mt-6 grid gap-4 md:grid-cols-3">
            <StatCard
              label="Overall #1 Pick"
              value={
                overallLeader
                  ? `${overallLeader.playerName} (${overallLeader.team} ${overallLeader.position})`
                  : "N/A"
              }
              detail={
                overallLeader
                  ? `${overallLeader.totalPoints.toFixed(1)} projected pts · Tier ${draftTierLabel(overallLeader.tier)}`
                  : ""
              }
            />
            <StatCard
              label="Best Value Over Replacement"
              value={
                bestValue
                  ? `${bestValue.playerName} (${bestValue.team} ${bestValue.position})`
                  : "N/A"
              }
              detail={
                bestValue
                  ? `+${bestValue.valueOverReplacement.toFixed(1)} VOR vs. replacement`
                  : ""
              }
            />
            <StatCard
              label="Top Rookie"
              value={
                bestRookie
                  ? `${bestRookie.playerName} (${bestRookie.team} ${bestRookie.position})`
                  : "No qualifying rookie yet"
              }
              detail={
                bestRookie
                  ? `Overall rank #${bestRookie.rankOverall} · Pos rank #${bestRookie.rankPosition}`
                  : ""
              }
            />
          </section>

          <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <nav
                className="flex flex-wrap gap-2"
                aria-label="Position filter"
              >
                {POSITION_TABS.map((tab) => {
                  const isActive = position === tab;
                  return (
                    <Link
                      key={tab}
                      href={buildHref({
                        ...activeQuery,
                        position: tab === "ALL" ? undefined : tab,
                      })}
                      className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                        isActive
                          ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                          : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                      }`}
                    >
                      {tab}
                    </Link>
                  );
                })}
              </nav>

              <nav className="flex flex-wrap gap-2" aria-label="Scoring format">
                {FANTASY_SCORING_PROFILES.map((profile) => {
                  const isActive = scoring === profile.value;
                  return (
                    <Link
                      key={profile.value}
                      href={buildHref({
                        position: position === "ALL" ? undefined : position,
                        rookies: rookiesOnly ? "1" : undefined,
                        limit: String(limit),
                        scoring: profile.value,
                      })}
                      className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                        isActive
                          ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                          : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-edge-green/25 hover:text-kos-text"
                      }`}
                    >
                      {profile.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-kos-text/65">
              <Link
                href={buildHref({
                  position: position === "ALL" ? undefined : position,
                  scoring,
                  limit: String(limit),
                  rookies: rookiesOnly ? undefined : "1",
                })}
                className={`rounded-lg px-3 py-1.5 font-semibold transition ${
                  rookiesOnly
                    ? "border border-kos-gold/45 bg-kos-gold/15 text-kos-gold"
                    : "border border-white/10 bg-white/5 text-kos-text/70 hover:border-kos-gold/25"
                }`}
              >
                {rookiesOnly ? "Showing rookies only ✓" : "Rookies only"}
              </Link>
              <div className="flex items-center gap-2">
                <span>Rows:</span>
                {LIMIT_OPTIONS.map((option) => (
                  <Link
                    key={option}
                    href={buildHref({
                      position: position === "ALL" ? undefined : position,
                      scoring,
                      rookies: rookiesOnly ? "1" : undefined,
                      limit: String(option),
                    })}
                    className={`rounded-md px-2 py-1 font-semibold transition ${
                      limit === option
                        ? "bg-white/15 text-kos-text"
                        : "text-kos-text/60 hover:text-kos-text"
                    }`}
                  >
                    {option}
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-xl font-semibold text-kos-text">
                Draft Board
              </h2>
              <p className="text-xs text-kos-text/60">
                {board.count} player{board.count === 1 ? "" : "s"} matching
                filters
              </p>
            </div>
            {board.rows.length === 0 ? (
              <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
                No draft board rows match this filter yet. Try clearing the
                rookie filter or switching position.
              </div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full border-separate border-spacing-0">
                  <thead>
                    <tr>
                      {[
                        "Rk",
                        "Pos Rk",
                        "Player",
                        "Team",
                        "Pos",
                        "Tier",
                        "Gms",
                        "Pts",
                        "Pts/Gm",
                        "VOR",
                      ].map((label) => (
                        <th
                          key={label}
                          className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
                        >
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {board.rows.map((row) => (
                      <DraftRow key={`${row.playerId}-${row.team}`} row={row} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <p className="text-xs uppercase tracking-wide text-kos-text/60">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-kos-text">{value}</p>
      {detail ? <p className="text-sm text-kos-gold">{detail}</p> : null}
    </article>
  );
}

function DraftRow({ row }: { row: NflFantasyDraftRankingRow }) {
  return (
    <tr className="odd:bg-white/3">
      <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
        {row.rankOverall}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
        {row.position}
        {row.rankPosition}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
        {row.playerName}
        {row.isRookie ? (
          <span className="ml-2 rounded-full border border-kos-gold/40 bg-kos-gold/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-kos-gold">
            R
          </span>
        ) : null}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
        {row.team}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm">
        <span
          className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase ${draftPositionBadgeClass(
            row.position,
          )}`}
        >
          {row.position}
        </span>
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm">
        <span
          className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${draftTierBadgeClass(row.tier)}`}
        >
          {draftTierLabel(row.tier)}
        </span>
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
        {row.gamesProjected}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-gold">
        {row.totalPoints.toFixed(1)}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
        {fantasyPointsPerGame(row).toFixed(1)}
      </td>
      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
        {row.valueOverReplacement >= 0 ? "+" : ""}
        {row.valueOverReplacement.toFixed(1)}
      </td>
    </tr>
  );
}
