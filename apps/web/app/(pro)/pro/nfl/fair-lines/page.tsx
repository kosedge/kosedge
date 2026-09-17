import SportHubShell from "@/components/pro/SportHubShell";
import FootballNumbersUnavailable from "@/components/FootballNumbersUnavailable";
import { isNflFairLinesCustomerSurfaceClosed } from "@/lib/cfb-edge-board-public";
import NflFairLinesClient from "@/components/pro/nfl/NflFairLinesClient";

export const dynamic = "force-dynamic";

const DEFAULT_SEASON = 2026;
const PAST_WEEK_DAYS = 7;

type SearchValue = string | string[] | undefined;
type Slate = "week" | "season";

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/**
 * KEI Lines — SSR shell parses filters only.
 * Board client-fetches /api/nfl/fair-lines so HTML is not held open on
 * model-service (Alex waterfall). As-of = model oddsAsOf only (#422).
 */
export default async function NflFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  if (isNflFairLinesCustomerSurfaceClosed()) {
    return (
      <SportHubShell
        sportKey="nfl"
        sportName="NFL"
        base="/pro/nfl"
        badge="NFL Betting Desk"
        title="NFL Fair Lines"
        summary="Coming soon"
      >
        <FootballNumbersUnavailable sport="nfl" title="NFL KEI Lines" />
      </SportHubShell>
    );
  }

  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010
      ? seasonRaw
      : DEFAULT_SEASON;
  const slate: Slate =
    firstValue(search.slate) === "season" ? "season" : "week";
  const includePastRaw = firstValue(search.includePast);
  const includePastDays =
    includePastRaw === "7" || includePastRaw === "3" || includePastRaw === "1"
      ? PAST_WEEK_DAYS
      : 0;

  return (
    <NflFairLinesClient
      season={season}
      slate={slate}
      includePastDays={includePastDays}
    />
  );
}
