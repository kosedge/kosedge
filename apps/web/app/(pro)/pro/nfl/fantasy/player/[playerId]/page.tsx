import Link from "next/link";
import { notFound } from "next/navigation";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import { findDeskPlayer, loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";
import {
  draftPositionBadgeClass,
  draftTierBadgeClass,
  draftTierLabel,
} from "@/lib/nfl-fantasy-draft-shared";

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

export default async function FantasyPlayerDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ playerId: string }>;
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const { playerId } = await params;
  const search = await searchParams;
  const scoringRaw = firstValue(search.scoring);
  const scoring: FantasyScoringProfile = isScoringProfile(scoringRaw)
    ? scoringRaw
    : "half_ppr";

  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    limit: 400,
  });
  const row = findDeskPlayer(board, playerId);
  if (!row) notFound();

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <FantasyDeskNav active="rankings" scoring={scoring} />

      <section className="mt-4 overflow-hidden rounded-3xl border border-kos-gold/30 bg-[radial-gradient(ellipse_at_top,_rgba(212,175,55,0.16),_transparent_55%),#0b0d10] p-6 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          Fantasy Expert · Player card
        </p>
        <h1 className="mt-2 font-bebas text-4xl tracking-wide text-kos-text sm:text-5xl">
          {row.playerName}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span
            className={`rounded border px-2 py-0.5 text-xs font-semibold ${draftPositionBadgeClass(row.position)}`}
          >
            {row.position}
            {row.rankPosition}
          </span>
          <span className="text-sm text-kos-text/70">{row.team}</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${draftTierBadgeClass(row.tier)}`}
          >
            {draftTierLabel(row.tier)}
          </span>
          <span className="text-sm text-kos-text/60">
            Overall #{row.rankOverall}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3 text-center">
          <Stat label="Floor" value={row.floorPoints.toFixed(0)} />
          <Stat label="Median" value={row.medianPoints.toFixed(0)} gold />
          <Stat label="Ceiling" value={row.ceilingPoints.toFixed(0)} />
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Stat
            label="Model rank / ADP"
            value={`#${row.rankOverall} / ${row.adp == null ? "—" : row.adp.toFixed(1)}`}
          />
          <Stat
            label="Value Δ (ADP − model)"
            value={
              row.valueDelta == null
                ? "—"
                : `${row.valueDelta >= 0 ? "+" : ""}${row.valueDelta.toFixed(1)}`
            }
          />
          <Stat label="VOR" value={`+${row.valueOverReplacement.toFixed(1)}`} />
          <Stat
            label="Games projected"
            value={String(row.gamesProjected)}
          />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-black/35 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Why the model ranks them here
          </p>
          <ul className="mt-3 space-y-2">
            {row.drivers.map((driver) => (
              <li key={driver} className="text-sm text-kos-text/80">
                · {driver}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-black/35 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Fantasy Expert
          </p>
          <p className="mt-3 text-sm leading-relaxed text-kos-text/80">
            {row.expertBlurb}
          </p>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-black/35 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
            Schedule · risk
          </p>
          <p className="mt-2 text-sm font-semibold text-kos-text">
            {row.schedule.label}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">{row.schedule.detail}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {row.riskFlags.length === 0 ? (
              <span className="text-xs text-kos-text/50">No major flags</span>
            ) : (
              row.riskFlags.map((flag) => (
                <div
                  key={flag.kind + flag.label}
                  className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2"
                >
                  <p className="text-xs font-semibold text-amber-100">
                    {flag.label}
                  </p>
                  <p className="mt-0.5 text-[11px] text-amber-100/70">
                    {flag.detail}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Link
            href={`/pro/nfl/fantasy/builder?scoring=${scoring}`}
            className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-sm font-semibold text-kos-gold"
          >
            Open Builder
          </Link>
          <Link
            href={`/pro/nfl/fantasy/mock?scoring=${scoring}`}
            className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text"
          >
            Start Mock
          </Link>
          <Link
            href={`/pro/nfl/teams/${row.team.toLowerCase()}`}
            className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text"
          >
            Team page
          </Link>
        </div>
      </section>
    </main>
  );
}

function Stat({
  label,
  value,
  gold,
}: {
  label: string;
  value: string;
  gold?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-3 ${
        gold
          ? "border-kos-gold/35 bg-kos-gold/10"
          : "border-white/10 bg-black/30"
      }`}
    >
      <p className="text-[10px] uppercase tracking-wide text-kos-text/45">
        {label}
      </p>
      <p
        className={`mt-1 text-lg font-semibold ${gold ? "text-kos-gold" : "text-kos-text"}`}
      >
        {value}
      </p>
    </div>
  );
}
