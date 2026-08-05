import Link from "next/link";
import {
  awardStatLine,
  fetchNflAwardProjections,
  type NflAwardProjectionRow,
} from "@/lib/nfl-awards";
import {
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";

const DEFAULT_SEASON = 2026;

function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

const AWARD_TABS = [
  { id: "mvp", label: "MVP", live: true },
  { id: "opoy", label: "OPOY", live: true },
  { id: "dpoy", label: "DPOY", live: false },
  { id: "oroy", label: "OROY", live: false },
  { id: "droy", label: "DROY", live: false },
  { id: "coach", label: "Coach", live: false },
] as const;

export default async function NflAwardsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const season = DEFAULT_SEASON;
  const sp = searchParams ? await searchParams : {};
  const tabRaw = Array.isArray(sp.tab) ? sp.tab[0] : sp.tab;
  const tab =
    AWARD_TABS.find((t) => t.id === (tabRaw ?? "").toLowerCase())?.id ?? "mvp";

  const [mvp, opoy] = await Promise.all([
    fetchNflAwardProjections({ season, award: "mvp", limit: 10 }),
    fetchNflAwardProjections({ season, award: "opoy", limit: 10 }),
  ]);
  const error = mvp.error ?? opoy.error;
  const liveRows = tab === "opoy" ? opoy.rows : mvp.rows;
  const isLive = tab === "mvp" || tab === "opoy";

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              {season} Awards · Research
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Award Races
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Ranked contenders with team success and stat evidence. MVP and
              OPOY are live from the player model; other races stay listed until
              their engines ship.
            </p>
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              NFL Overview
            </Link>
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
            >
              Edge Board →
            </Link>
          </div>
        </div>
        <nav className="mt-5 flex flex-wrap gap-2" aria-label="Award races">
          {AWARD_TABS.map((item) => (
            <Link
              key={item.id}
              href={`/pro/nfl/awards?tab=${item.id}`}
              className={
                tab === item.id
                  ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                  : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
              }
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </section>

      <section className="mt-6 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">At a Glance</h2>
          <p className="mt-2 text-sm text-kos-text/75">
            {isLive
              ? `${liveRows[0]?.playerName ?? "—"} leads the ${tab.toUpperCase()} board`
              : `${tab.toUpperCase()} board pending model coverage`}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4 sm:col-span-2">
          <h2 className="text-sm font-semibold text-kos-gold">
            Top contenders
          </h2>
          <p className="mt-2 text-sm text-kos-text/75">
            {isLive
              ? liveRows
                  .slice(0, 3)
                  .map((r) => `#${r.rankOverall} ${r.playerName}`)
                  .join(" · ") || "—"
              : "Placeholder race — methodology below."}
          </p>
        </div>
      </section>

      {shouldShowModelUnreachableBanner({
        error,
        hasContent: liveRows.length > 0,
      }) ? (
        <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100">
          {modelUnreachableCopy(error)}
        </section>
      ) : isLive ? (
        <section className="mt-6">
          <AwardBoard
            title={tab === "opoy" ? "OPOY Favorites" : "MVP Favorites"}
            subtitle={
              tab === "opoy"
                ? "Weighted 65% player stat composite, 35% team success — no QB bias."
                : "Weighted 45% team success, 35% player stat composite, 20% QB voting-history prior."
            }
            rows={liveRows}
          />
        </section>
      ) : (
        <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
          {tab.toUpperCase()} rankings will publish when the corresponding award
          engine is live. MVP and OPOY are available now.
        </section>
      )}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/60">
        <p className="text-xs font-semibold uppercase tracking-wide text-kos-text/45">
          Methodology (secondary)
        </p>
        <p className="mt-2">
          Team success blends projected wins and division-title probability from
          the Monte Carlo. Stat composite compares same-position peers only.
        </p>
      </section>
    </main>
  );
}

function AwardBoard({
  title,
  subtitle,
  rows,
}: {
  title: string;
  subtitle: string;
  rows: NflAwardProjectionRow[];
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
      <h2 className="text-xl font-semibold text-kos-text">{title}</h2>
      <p className="mt-1 text-sm text-kos-text/70">{subtitle}</p>
      {rows.length === 0 ? (
        <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-5 text-sm text-kos-text/70">
          No qualifying candidates yet for this award — season stats may still
          be materializing.
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
                  <span className="text-base font-semibold text-kos-text">
                    {row.playerName}
                  </span>
                  <span className="text-xs text-kos-text/60">
                    {row.team} · {row.position}
                  </span>
                </div>
                <span className="rounded-full border border-kos-gold/30 bg-kos-gold/10 px-2 py-0.5 text-[11px] font-semibold text-kos-gold">
                  {(row.awardScore * 100).toFixed(1)} score
                </span>
              </div>
              <p className="mt-2 text-sm text-kos-text/80">
                {awardStatLine(row)}
              </p>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-kos-text/65">
                <span>Team wins: {row.teamExpectedWins.toFixed(1)}</span>
                <span>Div title: {percent(row.teamDivisionTitleProb)}</span>
                <span>Playoffs: {percent(row.teamPlayoffProb)}</span>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-kos-text/55">
                <span>
                  Team success score: {row.teamSuccessScore.toFixed(2)}
                </span>
                <span>Stat composite: {row.statComposite.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
