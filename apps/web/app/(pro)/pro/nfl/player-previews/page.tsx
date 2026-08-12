import type { Metadata } from "next";
import Link from "next/link";
import {
  CurrentYtdHint,
  PlayerFutureColumnHeaders,
  PlayerFutureTripleCell,
} from "@/components/pro/nfl/PlayerFutureTripleColumns";
import {
  AWARD_SCORE_LABEL,
  AWARD_SCORE_TITLE,
  awardScoreIndex,
} from "@/lib/nfl-award-score";
import {
  fetchNflAwardProjections,
  type NflAwardProjectionRow,
  type NflAwardType,
} from "@/lib/nfl-awards";
import {
  awardOddsForPlayer,
  loadNflFuturesOdds,
  type NflFuturesOddsBundle,
} from "@/lib/nfl-futures-odds";
import {
  fetchNflFantasyDraftRankings,
  fantasyPointsPerGame,
  type NflFantasyDraftRankingRow,
} from "@/lib/nfl-fantasy-draft";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL Player Previews",
  description:
    "Kos Edge 2026 player preview index — award races plus fantasy draft outlooks for skill-position leaders.",
};

const DEFAULT_SEASON = 2026;

function awardLine(row: NflAwardProjectionRow): string {
  const parts = [
    `${row.passYardsTotal.toFixed(0)} pass yds`,
    `${row.passTdsTotal.toFixed(1)} pass TD`,
    `${row.rushYardsTotal.toFixed(0)} rush yds`,
    `${row.receivingYardsTotal.toFixed(0)} rec yds`,
  ].filter((part) => !part.startsWith("0 ") && !part.startsWith("0.0 "));
  return parts.slice(0, 3).join(" · ");
}

function fantasyLine(row: NflFantasyDraftRankingRow): string {
  const ppg = fantasyPointsPerGame(row);
  return `Rank ${row.rankOverall} · ${row.position} #${row.rankPosition} · ${ppg.toFixed(1)} PPG · ${row.tier}`;
}

export default async function NflPlayerPreviewsPage() {
  const [mvp, opoy, fantasy, oddsBundle] = await Promise.all([
    fetchNflAwardProjections({
      season: DEFAULT_SEASON,
      award: "mvp",
      limit: 12,
    }),
    fetchNflAwardProjections({
      season: DEFAULT_SEASON,
      award: "opoy",
      limit: 12,
    }),
    fetchNflFantasyDraftRankings({
      season: DEFAULT_SEASON,
      scoringProfile: "half_ppr",
      limit: 40,
    }),
    loadNflFuturesOdds(),
  ]);

  const skillFantasy = fantasy.rows
    .filter((row) => ["QB", "RB", "WR", "TE"].includes(row.position))
    .slice(0, 32);

  const error =
    mvp.error || opoy.error || fantasy.error || null;
  const total =
    mvp.rows.length + opoy.rows.length + skillFantasy.length;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            NFL Pro · Player Previews
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
            2026 player outlook index
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
            Award-race contenders and half-PPR skill-position leaders from the
            live Kos Edge player model — the dedicated player preview surface
            for camp and Week 1 prep.
          </p>
          <p className="mt-2 text-xs text-kos-text/55">
            {total} player rows · season {DEFAULT_SEASON}
            {mvp.rows[0]?.modelVersion
              ? ` · ${mvp.rows[0].modelVersion}`
              : fantasy.rows[0]?.modelVersion
                ? ` · ${fantasy.rows[0].modelVersion}`
                : ""}
          </p>
          <CurrentYtdHint className="mt-1" />
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            Back to Hub
          </Link>
          <Link
            href="/pro/nfl/awards"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Awards race
          </Link>
          <Link
            href="/pro/nfl/fantasy"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Fantasy draft
          </Link>
          <Link
            href="/pro/nfl/previews"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Team previews
          </Link>
        </div>
      </div>

      {error ? (
        <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
          {error}
        </div>
      ) : null}

      {total === 0 && !error ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
          Player outlook rows are not available yet from the model service.
          Check awards and fantasy boards after the next player-cycle materialize.
        </div>
      ) : null}

      <AwardRacePreview
        title="MVP race"
        subtitle="Weighted team success + stat composite + QB voting prior."
        award="mvp"
        rows={mvp.rows}
        oddsBundle={oddsBundle}
      />

      <AwardRacePreview
        title="OPOY race"
        subtitle="Offensive Player of the Year board from the same award model."
        award="opoy"
        rows={opoy.rows}
        oddsBundle={oddsBundle}
      />

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-kos-text">
          Skill-position draft outlook
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          Top half-PPR skill players — use as the player preview ladder into
          fantasy and props desks.
        </p>
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
              <tr>
                <th className="px-3 py-3 sm:px-4">Player</th>
                <th className="px-3 py-3 sm:px-4">Team</th>
                <th className="px-3 py-3 sm:px-4">Pos</th>
                <th className="px-3 py-3 sm:px-4">Outlook</th>
              </tr>
            </thead>
            <tbody>
              {skillFantasy.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-6 text-sm text-kos-text/60 sm:px-4"
                  >
                    Skill-position outlook table is empty for this cycle — not a
                    ready preview board. Check Fantasy Draft Desk after the next
                    player materialize.
                  </td>
                </tr>
              ) : null}
              {skillFantasy.map((row) => (
                <tr
                  key={`fan-${row.playerId}-${row.rankOverall}`}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-3 py-3 font-medium sm:px-4">
                    {row.playerName}
                    {row.isRookie ? (
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-kos-gold">
                        Rookie
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <Link
                      href={`/pro/nfl/teams/${row.team}`}
                      className="hover:text-kos-gold"
                    >
                      {row.team}
                    </Link>
                  </td>
                  <td className="px-3 py-3 sm:px-4">{row.position}</td>
                  <td className="px-3 py-3 text-kos-text/70 sm:px-4">
                    {fantasyLine(row)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function AwardRacePreview({
  title,
  subtitle,
  award,
  rows,
  oddsBundle,
}: {
  title: string;
  subtitle: string;
  award: NflAwardType;
  rows: NflAwardProjectionRow[];
  oddsBundle: NflFuturesOddsBundle;
}) {
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold text-kos-text">{title}</h2>
      <p className="mt-1 text-sm text-kos-text/65">{subtitle}</p>
      <CurrentYtdHint className="mt-1" />
      <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
            <tr>
              <th className="px-3 py-3 sm:px-4">#</th>
              <th className="px-3 py-3 sm:px-4">Player</th>
              <th className="px-3 py-3 sm:px-4">Team</th>
              <PlayerFutureColumnHeaders
                projectedLabel={AWARD_SCORE_LABEL}
                projectedTitle={AWARD_SCORE_TITLE}
              />
              <th className="px-3 py-3 sm:px-4">Outlook</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const odds = awardOddsForPlayer(
                oddsBundle,
                award,
                row.playerName,
              );
              return (
                <tr
                  key={`${award}-${row.playerId}`}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-3 py-3 sm:px-4">{row.rankOverall}</td>
                  <td className="px-3 py-3 font-medium sm:px-4">
                    {row.playerName}
                    <span className="ml-2 text-xs text-kos-text/50">
                      {row.position}
                    </span>
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <Link
                      href={`/pro/nfl/teams/${row.team}`}
                      className="hover:text-kos-gold"
                    >
                      {row.team}
                    </Link>
                  </td>
                  <PlayerFutureTripleCell
                    projected={awardScoreIndex(row.awardScore)}
                    current={null}
                    currentKind="award"
                    odds={odds}
                    projectedDigits={1}
                    projectedSubLabel={AWARD_SCORE_LABEL}
                  />
                  <td className="px-3 py-3 text-kos-text/70 sm:px-4">
                    {awardLine(row)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
