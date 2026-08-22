import { FantasyMockDraftClient } from "@/components/pro/nfl/fantasy/FantasyMockDraftClient";
import { loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import type { MockTeamCount } from "@/lib/fantasy/mock-types";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

const LIMIT = 400;

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

function parseTeams(value: string | undefined): MockTeamCount {
  return value === "10" ? 10 : 12;
}

function parseSlot(value: string | undefined, teams: MockTeamCount): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 1;
  return Math.min(Math.max(Math.round(n), 1), teams);
}

export default async function FantasyMockDraftPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const scoringRaw = firstValue(search.scoring);
  const scoring: FantasyScoringProfile = isScoringProfile(scoringRaw)
    ? scoringRaw
    : "ppr";
  const teams = parseTeams(firstValue(search.teams));
  const slot = parseSlot(firstValue(search.slot), teams);

  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    limit: LIMIT,
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <FantasyMockDraftClient
        board={board}
        initialScoring={scoring}
        initialTeams={teams}
        initialSlot={slot}
      />
    </main>
  );
}
