import Link from "next/link";
import { awardStatLine, fetchNflAwardProjections, type NflAwardProjectionRow } from "@/lib/nfl-awards";

const DEFAULT_SEASON = 2026;

function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export default async function NflAwardsPage() {
  const season = DEFAULT_SEASON;
  const [mvp, opoy] = await Promise.all([
    fetchNflAwardProjections({ season, award: "mvp", limit: 10 }),
    fetchNflAwardProjections({ season, award: "opoy", limit: 10 }),
  ]);
  const error = mvp.error ?? opoy.error;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} Award Race
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              MVP &amp; Offensive Player of the Year
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Real projected contenders ranked by team success, position voting history, and season stat projections —
              with the exact supporting numbers behind each ranking, not just a name.
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
              href="/pro/nfl/fantasy"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Fantasy Draft Board →
            </Link>
          </div>
        </div>
      </section>

      {error ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {error} The award boards will populate once the model service is reachable.
        </section>
      ) : (
        <section className="mt-6 grid gap-6 xl:grid-cols-2">
          <AwardBoard
            title="MVP Favorites"
            subtitle="Weighted 45% team success, 35% player stat composite, 20% QB voting-history prior — a merely-good QB season on a great team still edges a middling non-QB season."
            rows={mvp.rows}
          />
          <AwardBoard
            title="Offensive Player of the Year Favorites"
            subtitle="Weighted 65% player stat composite, 35% team success — no QB bias. Any offensive position can win purely on statistical dominance."
            rows={opoy.rows}
          />
        </section>
      )}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/70">
        <p>
          Team success score blends each contender&apos;s projected regular-season win total and division-title
          probability from the current season Monte Carlo. Stat composite compares each player only against
          same-position peers, so a QB&apos;s passing yardage is never compared directly to a WR&apos;s receiving
          yardage — only each player&apos;s standing within their own position group feeds the cross-position score.
        </p>
      </section>
    </main>
  );
}

function AwardBoard({ title, subtitle, rows }: { title: string; subtitle: string; rows: NflAwardProjectionRow[] }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
      <h2 className="text-xl font-semibold text-kos-text">{title}</h2>
      <p className="mt-1 text-sm text-kos-text/70">{subtitle}</p>
      {rows.length === 0 ? (
        <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
          No qualifying candidates yet for this award — season stats may still be materializing.
        </div>
      ) : (
        <ol className="mt-4 space-y-3">
          {rows.map((row) => (
            <li
              key={`${row.award}-${row.playerId}`}
              className={`rounded-xl border p-3 ${
                row.rankOverall === 1
                  ? "border-kos-gold/40 bg-kos-gold/10"
                  : "border-white/10 bg-white/3"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-baseline gap-2">
                  <span
                    className={`text-lg font-bold ${row.rankOverall === 1 ? "text-kos-gold" : "text-kos-text/60"}`}
                  >
                    #{row.rankOverall}
                  </span>
                  <span className="text-base font-semibold text-kos-text">{row.playerName}</span>
                  <span className="text-xs text-kos-text/60">
                    {row.team} · {row.position}
                  </span>
                </div>
                <span className="rounded-full border border-kos-gold/30 bg-kos-gold/10 px-2 py-0.5 text-[11px] font-semibold text-kos-gold">
                  {(row.awardScore * 100).toFixed(1)} score
                </span>
              </div>
              <p className="mt-2 text-sm text-kos-text/80">{awardStatLine(row)}</p>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-kos-text/65">
                <span>Team wins: {row.teamExpectedWins.toFixed(1)}</span>
                <span>Div title: {percent(row.teamDivisionTitleProb)}</span>
                <span>Playoffs: {percent(row.teamPlayoffProb)}</span>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-kos-text/55">
                <span>Team success score: {row.teamSuccessScore.toFixed(2)}</span>
                <span>Stat composite: {row.statComposite.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
