import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import {
  selectGuillotineHighUpside,
  selectGuillotineSafeFloor,
} from "@/lib/fantasy/guillotine";
import { loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import type { FantasyDeskRow, FantasyScoringProfile } from "@/lib/fantasy/types";

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

export default async function NflGuillotinePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const scoring = parseScoring(firstValue(search.scoring));
  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    limit: 200,
  });

  const isPreseason = board.source === "preseason-fallback";
  const safeFloor = selectGuillotineSafeFloor(board.rows);
  const highUpside = selectGuillotineHighUpside(board.rows);
  const hasLists = safeFloor.length > 0 || highUpside.length > 0;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Fantasy · Guillotine desk
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Guillotine League
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              Last place is eliminated each week — waivers and adds matter as
              much as your draft. Use season-long ranks and schedule softness to
              stay alive; a fuller weekly guillotine tool can deepen later.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">Date: {KOSEDGE_DATE}</p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-44">
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Fantasy Draft Desk →
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
            researchActive="guillotine"
          />
        </div>
      </section>

      {isPreseason ? (
        <div className="mt-6">
          <HonestStatusBanner title="Preseason sim board" tone="sky">
            <p>
              Safe-floor and upside lists below are labeled preseason sim —
              useful for draft and early-season thinking, not a locked weekly
              guillotine waiver engine.
            </p>
          </HonestStatusBanner>
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h2 className="text-lg font-semibold text-kos-text">
            What guillotine is
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-kos-text/75">
            <li>
              Each week, the lowest-scoring team is cut — roster survival beats
              season-long points races.
            </li>
            <li>
              Waivers and opportunistic adds matter weekly; dead weight gets you
              eliminated.
            </li>
            <li>
              Think Survivor-style pathing: maximize stay-alive probability,
              then chase upside when safe.
            </li>
          </ul>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h2 className="text-lg font-semibold text-kos-text">
            How KosEdge helps today
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-kos-text/75">
            <li>
              Season-long ranks and floor/ceiling bands from the fantasy desk.
            </li>
            <li>
              Schedule softness (early vs playoff windows) for who to lean on
              week to week.
            </li>
            <li>
              Survivor-style path thinking on the Season Model — stay alive
              first.
            </li>
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
            >
              Rankings
            </Link>
            <Link
              href="/pro/nfl/model"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Season Model
            </Link>
            <Link
              href="/pro/nfl/game-boxes"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Game Boxes
            </Link>
            <Link
              href="/pro/nfl/survivor"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
            >
              Survivor
            </Link>
          </div>
        </article>
      </section>

      {hasLists ? (
        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          <NameList
            title="Safe floor"
            subtitle={
              isPreseason
                ? "Preseason sim — higher floor bands for stay-alive weeks"
                : "Higher floor bands for stay-alive weeks"
            }
            rows={safeFloor}
          />
          <NameList
            title="High upside"
            subtitle={
              isPreseason
                ? "Preseason sim — ceiling chase / waiver-style adds"
                : "Ceiling chase / waiver-style adds"
            }
            rows={highUpside}
          />
        </section>
      ) : (
        <div className="mt-6">
          <HonestStatusBanner title="Fantasy board unavailable" tone="neutral">
            <p>
              Open the Draft Desk once rankings load — guillotine lists pull
              from the same board.
            </p>
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="mt-3 inline-flex rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
            >
              Fantasy Draft Desk
            </Link>
          </HonestStatusBanner>
        </div>
      )}
    </main>
  );
}

function NameList({
  title,
  subtitle,
  rows,
}: {
  title: string;
  subtitle: string;
  rows: FantasyDeskRow[];
}) {
  if (rows.length === 0) {
    return (
      <article className="rounded-2xl border border-dashed border-white/15 bg-black/25 p-4 sm:p-5">
        <h2 className="text-lg font-semibold text-kos-text">{title}</h2>
        <p className="mt-1 text-sm text-kos-text/60">No names for this cut yet.</p>
      </article>
    );
  }

  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
      <h2 className="text-lg font-semibold text-kos-text">{title}</h2>
      <p className="mt-1 text-sm text-kos-text/65">{subtitle}</p>
      <ol className="mt-4 space-y-2">
        {rows.map((row) => (
          <li
            key={row.playerId}
            className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/3 px-3 py-2.5"
          >
            <div className="min-w-0">
              <p className="truncate font-semibold text-kos-text">
                {row.playerName}
              </p>
              <p className="text-xs text-kos-text/55">
                {row.team} · {row.position}
                {row.rankPosition} · model #{row.rankOverall}
              </p>
              {row.drivers[0] ? (
                <p className="mt-1 text-xs text-kos-text/70">{row.drivers[0]}</p>
              ) : null}
            </div>
            <div className="shrink-0 text-right text-xs tabular-nums text-kos-text/65">
              <div>Floor {row.floorPoints.toFixed(0)}</div>
              <div className="text-kos-gold">
                Ceil {row.ceilingPoints.toFixed(0)}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}
