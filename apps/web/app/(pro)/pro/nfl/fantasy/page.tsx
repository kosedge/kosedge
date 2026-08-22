import { FantasyDraftDeskClient } from "@/components/pro/nfl/fantasy/FantasyDraftDeskClient";
import { loadFantasyDraftDesk } from "@/lib/fantasy/load-desk";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";
import { FANTASY_DRAFT_POSITIONS } from "@/lib/nfl-fantasy-draft-shared";

const POSITION_TABS = ["ALL", ...FANTASY_DRAFT_POSITIONS] as const;
const LIMIT = 250;

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

export default async function NflFantasyDraftDeskPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const positionRaw = (firstValue(search.position) ?? "ALL").toUpperCase();
  const position = (POSITION_TABS as readonly string[]).includes(positionRaw)
    ? positionRaw
    : "ALL";
  const scoringRaw = firstValue(search.scoring);
  const scoring: FantasyScoringProfile = isScoringProfile(scoringRaw)
    ? scoringRaw
    : "ppr";
  const rookiesOnly = firstValue(search.rookies) === "1";

  const board = await loadFantasyDraftDesk({
    season: 2026,
    scoringProfile: scoring,
    rookiesOnly,
    limit: LIMIT,
  });

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <FantasyDraftDeskClient
        board={board}
        initialPosition={position}
        initialScoring={scoring}
        initialTab="draft"
        basePath="/pro/nfl/fantasy"
      />
    </main>
  );
}
