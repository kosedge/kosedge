import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
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
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-bebas text-4xl leading-none tracking-[0.04em] text-kos-gold">
            KOSEDGE
          </p>
          <h1 className="mt-1 font-bebas text-3xl tracking-wide text-kos-text">
            Builder
          </h1>
          <p className="mt-1 text-sm text-kos-text/60">
            Rankings stay Model rank. Suggestions here are ADP-aware (take /
            wait / reach).
          </p>
        </div>
        <FantasyDeskNav active="builder" scoring={scoring} />
      </div>
      <FantasyDraftDeskClient
        board={board}
        initialScoring={scoring}
        initialTab="builder"
        compactHero
        basePath="/pro/nfl/fantasy/builder"
      />
    </main>
  );
}
