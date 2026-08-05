import Link from "next/link";
import { FantasyDraftDeskClient } from "@/components/pro/nfl/fantasy/FantasyDraftDeskClient";
import { loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

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

export default async function FantasyTeamBuilderPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const scoringRaw = firstValue(search.scoring);
  const scoring: FantasyScoringProfile = isScoringProfile(scoringRaw)
    ? scoringRaw
    : "half_ppr";

  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    limit: 300,
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            Phase 1 · Manual
          </p>
          <h1 className="font-bebas text-3xl tracking-wide text-kos-text">
            Team Builder
          </h1>
        </div>
        <Link
          href={`/pro/nfl/fantasy?scoring=${scoring}`}
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
        >
          ← Back to Draft Desk
        </Link>
      </div>
      <FantasyDraftDeskClient
        board={board}
        initialScoring={scoring}
        initialTab="builder"
      />
    </main>
  );
}
