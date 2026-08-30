import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import { AdpQaFlagChip } from "@/components/pro/nfl/fantasy/AdpQaFlagChip";
import { formatAdp } from "@/lib/fantasy/adp-proxy";
import { loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import {
  formatSleeperGap,
  selectSleeperRows,
  sleeperWhyLine,
} from "@/lib/fantasy/sleepers";
import type {
  FantasyDeskRow,
  FantasyScoringProfile,
} from "@/lib/fantasy/types";

const KOSEDGE_DATE = "August 11, 2026";

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function parseScoring(raw: string | undefined): FantasyScoringProfile {
  if (raw === "standard" || raw === "ppr" || raw === "half_ppr") return raw;
  return "half_ppr";
}

export default async function NflSleepersPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const scoring = parseScoring(firstValue(search.scoring));
  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    limit: 250,
  });

  const sleepers = selectSleeperRows(board.rows);
  const isPreseason = board.source === "preseason-fallback";
  const hasRows = sleepers.length > 0;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Fantasy · Sleepers
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Sleepers
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              Late-round and ADP-value names from KosEdge ranks vs FantasyPros
              ADP. Gap stays — when ADP is unmatched — no fake precision.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Date: {KOSEDGE_DATE}
              {board.adpOrigin !== "none"
                ? ` · ${board.adpSourceLabel} · ${board.adpFreshnessLabel}`
                : null}
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-44">
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Draft Desk →
            </Link>
            <Link
              href={`/pro/nfl/fantasy/mock?scoring=${scoring}`}
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Mock Draft
            </Link>
          </div>
        </div>
        <div className="mt-5">
          <FantasyDeskNav
            active="rankings"
            scoring={scoring}
            researchActive="sleepers"
          />
        </div>
      </section>

      {isPreseason ? (
        <div className="mt-6">
          <HonestStatusBanner title="Preseason sim board" tone="sky">
            <p>
              Sleepers below use the preseason fantasy board vs FantasyPros ADP.
              Treat gaps as research signals — camp moves still shift roles.
            </p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {board.adpOrigin === "none" ? (
        <div className="mt-6">
          <HonestStatusBanner title="Market ADP unavailable" tone="amber">
            <p>
              FantasyPros ADP isn&apos;t loaded — Value Δ / Gap stays blank
              until the feed returns. Model ranks still show.
            </p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {!hasRows ? (
        <div className="mt-6">
          <HonestStatusBanner title="No sleeper rows yet" tone="neutral">
            <p>
              Late-round value names appear when the fantasy desk + ADP match.
              Open Draft Desk or Mock while the board loads.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href={`/pro/nfl/fantasy?scoring=${scoring}`}
                className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
              >
                Draft Desk
              </Link>
              <Link
                href={`/pro/nfl/fantasy/mock?scoring=${scoring}`}
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
              >
                Mock
              </Link>
            </div>
          </HonestStatusBanner>
        </div>
      ) : (
        <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-xl font-semibold text-kos-text">
              Late-round value board
            </h2>
            <p className="text-xs text-kos-text/55">
              {sleepers.length} name{sleepers.length === 1 ? "" : "s"} ·{" "}
              {scoring.replace("_", " ")}
            </p>
          </div>

          {/* Mobile cards */}
          <ul className="mt-4 space-y-3 md:hidden">
            {sleepers.map((row) => (
              <SleeperCard key={row.playerId} row={row} scoring={scoring} />
            ))}
          </ul>

          {/* Desktop table */}
          <div className="mt-4 hidden overflow-x-auto md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 font-semibold">Player</th>
                  <th className="px-3 py-2 font-semibold">Pos</th>
                  <th className="px-3 py-2 font-semibold">Team</th>
                  <th className="px-3 py-2 font-semibold">Model</th>
                  <th className="px-3 py-2 font-semibold">ADP</th>
                  <th className="px-3 py-2 font-semibold">Gap</th>
                  <th className="px-3 py-2 font-semibold">Why</th>
                </tr>
              </thead>
              <tbody>
                {sleepers.map((row) => (
                  <tr
                    key={row.playerId}
                    className="border-b border-white/5 hover:bg-white/5"
                  >
                    <td className="px-3 py-3">
                      <Link
                        href={`/pro/nfl/fantasy/player/${encodeURIComponent(row.playerId)}?scoring=${scoring}`}
                        className="font-semibold text-kos-text hover:text-kos-gold"
                      >
                        {row.playerName}
                      </Link>
                      <div className="mt-1">
                        <AdpQaFlagChip flag={row.adpQaFlag} />
                      </div>
                    </td>
                    <td className="px-3 py-3 text-kos-text/80">
                      {row.position}
                      {row.rankPosition}
                    </td>
                    <td className="px-3 py-3 text-kos-text/80">{row.team}</td>
                    <td className="px-3 py-3 font-semibold tabular-nums text-kos-gold">
                      #{row.rankOverall}
                    </td>
                    <td className="px-3 py-3 tabular-nums text-kos-text/80">
                      {formatAdp(row.adp)}
                    </td>
                    <td className="px-3 py-3 font-semibold tabular-nums text-edge-green">
                      {formatSleeperGap(row.valueDelta)}
                    </td>
                    <td className="max-w-md px-3 py-3 text-kos-text/70">
                      {sleeperWhyLine(row)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}

function SleeperCard({
  row,
  scoring,
}: {
  row: FantasyDeskRow;
  scoring: FantasyScoringProfile;
}) {
  return (
    <li className="rounded-xl border border-white/10 bg-white/3 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Link
            href={`/pro/nfl/fantasy/player/${encodeURIComponent(row.playerId)}?scoring=${scoring}`}
            className="font-semibold text-kos-text hover:text-kos-gold"
          >
            {row.playerName}
          </Link>
          <div className="mt-1">
            <AdpQaFlagChip flag={row.adpQaFlag} />
          </div>
          <p className="text-xs text-kos-text/55">
            {row.position}
            {row.rankPosition} · {row.team}
          </p>
        </div>
        <div className="shrink-0 text-right text-xs tabular-nums">
          <div className="font-semibold text-kos-gold">#{row.rankOverall}</div>
          <div className="text-kos-text/55">ADP {formatAdp(row.adp, 0)}</div>
          <div className="font-semibold text-edge-green">
            Gap {formatSleeperGap(row.valueDelta)}
          </div>
        </div>
      </div>
      <p className="mt-2 text-sm text-kos-text/75">{sleeperWhyLine(row)}</p>
    </li>
  );
}
