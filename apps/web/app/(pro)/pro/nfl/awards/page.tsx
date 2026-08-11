import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import {
  awardStatLine,
  fetchNflAwardProjections,
  type NflAwardProjectionRow,
  type NflAwardType,
} from "@/lib/nfl-awards";
import {
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";

const DEFAULT_SEASON = 2026;
const KOSEDGE_DATE = "August 11, 2026";

/** Only races the award engine actually materializes — never placeholder tabs. */
const LIVE_AWARD_META: {
  id: NflAwardType;
  label: string;
  subtitle: string;
}[] = [
  {
    id: "mvp",
    label: "MVP",
    subtitle:
      "Weighted 45% team success, 35% player stat composite, 20% QB voting-history prior.",
  },
  {
    id: "opoy",
    label: "OPOY",
    subtitle:
      "Weighted 65% player stat composite, 35% team success — no QB bias.",
  },
];

function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function lineageNote(rows: NflAwardProjectionRow[]): string | null {
  const version = rows.find((r) => r.modelVersion)?.modelVersion;
  const updated = rows
    .map((r) => r.updatedAt)
    .filter((v): v is string => Boolean(v))
    .map((v) => Date.parse(v))
    .filter((n) => Number.isFinite(n));
  const parts: string[] = [];
  if (version) parts.push(version);
  if (updated.length > 0) {
    const latest = new Date(Math.max(...updated));
    parts.push(
      `as of ${latest.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })}`,
    );
  }
  return parts.length ? parts.join(" · ") : null;
}

function shortNote(row: NflAwardProjectionRow): string {
  const stats = awardStatLine(row);
  return `${stats} · ~${row.teamExpectedWins.toFixed(1)} team wins, ${percent(row.teamPlayoffProb)} playoff.`;
}

export default async function NflAwardsPage() {
  const season = DEFAULT_SEASON;

  const boards = await Promise.all(
    LIVE_AWARD_META.map(async (meta) => {
      const result = await fetchNflAwardProjections({
        season,
        award: meta.id,
        limit: 10,
      });
      return { ...meta, ...result };
    }),
  );

  const error = boards.find((b) => b.error)?.error;
  const liveBoards = boards.filter((b) => b.rows.length > 0);
  const anyRows = liveBoards.length > 0;
  const lineage = lineageNote(liveBoards.flatMap((b) => b.rows));

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Betting Desk · Award races
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              MVP / Awards
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              Contenders from the player + season model — win/production signal
              blended with team success. Research board, not a voting forecast.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Date: {KOSEDGE_DATE}
              {lineage ? ` · ${lineage}` : null}
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-44">
            <Link
              href="/pro/nfl/model"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Season Model →
            </Link>
            <Link
              href="/pro/power-ratings/nfl"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Power Ratings
            </Link>
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              NFL Overview
            </Link>
          </div>
        </div>
      </section>

      {shouldShowModelUnreachableBanner({
        error,
        hasContent: anyRows,
      }) ? (
        <div className="mt-6">
          <HonestStatusBanner title="Model service unreachable" tone="amber">
            <p>{modelUnreachableCopy(error)}</p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {!error && !anyRows ? (
        <div className="mt-6">
          <HonestStatusBanner
            title="Award boards fill when season-sim production rates land"
            tone="sky"
          >
            <p>
              MVP / OPOY favorites publish from the active award materialization
              run. DPOY / OROY / coach races stay off this page until those
              engines ship — no placeholder tabs.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href="/pro/nfl/model"
                className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
              >
                Season Model
              </Link>
              <Link
                href="/pro/power-ratings/nfl"
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
              >
                Power Ratings
              </Link>
            </div>
          </HonestStatusBanner>
        </div>
      ) : null}

      {liveBoards.length > 0 ? (
        <div className="mt-6 space-y-6">
          {liveBoards.map((board) => (
            <AwardBoard
              key={board.id}
              title={`${board.label} Favorites`}
              subtitle={board.subtitle}
              rows={board.rows}
            />
          ))}
        </div>
      ) : null}

      {anyRows ? (
        <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/60">
          <p className="text-xs font-semibold uppercase tracking-wide text-kos-text/45">
            Methodology
          </p>
          <p className="mt-2">
            Team success blends projected wins and division-title probability
            from the Monte Carlo. Stat composite compares same-position peers
            only. Races without live coverage are omitted — not stubbed.
          </p>
        </section>
      ) : null}
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

      {/* Mobile cards */}
      <ol className="mt-4 space-y-3 sm:hidden">
        {rows.map((row) => (
          <li
            key={`${row.award}-${row.playerId}`}
            className={`rounded-xl border p-3 ${
              row.rankOverall === 1
                ? "border-kos-gold/40 bg-kos-gold/10"
                : "border-white/10 bg-white/3"
            }`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="font-semibold text-kos-text">
                <span className="text-kos-gold">#{row.rankOverall}</span>{" "}
                {row.playerName}
              </p>
              <span className="text-[11px] font-semibold text-kos-gold">
                {(row.awardScore * 100).toFixed(1)}
              </span>
            </div>
            <p className="mt-1 text-xs text-kos-text/55">
              {row.team} · {row.position}
            </p>
            <p className="mt-2 text-sm text-kos-text/80">{shortNote(row)}</p>
          </li>
        ))}
      </ol>

      {/* Desktop table */}
      <div className="mt-4 hidden overflow-x-auto sm:block">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-kos-text/55">
            <tr className="border-b border-white/10">
              <th className="px-3 py-2 font-semibold">#</th>
              <th className="px-3 py-2 font-semibold">Player</th>
              <th className="px-3 py-2 font-semibold">Team</th>
              <th className="px-3 py-2 font-semibold">Signal</th>
              <th className="px-3 py-2 font-semibold">Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${row.award}-${row.playerId}`}
                className="border-b border-white/5 hover:bg-white/5"
              >
                <td className="px-3 py-3 font-semibold text-kos-gold">
                  {row.rankOverall}
                </td>
                <td className="px-3 py-3">
                  <div className="font-semibold text-kos-text">
                    {row.playerName}
                  </div>
                  <div className="text-xs text-kos-text/55">{row.position}</div>
                </td>
                <td className="px-3 py-3 text-kos-text/80">{row.team}</td>
                <td className="px-3 py-3 font-semibold text-kos-gold">
                  {(row.awardScore * 100).toFixed(1)}
                  <div className="text-xs font-normal text-kos-text/55">
                    wins {row.teamExpectedWins.toFixed(1)} · playoff{" "}
                    {percent(row.teamPlayoffProb)}
                  </div>
                </td>
                <td className="px-3 py-3 text-kos-text/75">{shortNote(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
