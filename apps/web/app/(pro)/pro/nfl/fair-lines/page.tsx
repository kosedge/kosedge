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
 * model-service (Alex waterfall).
 */
export default async function NflFairLinesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
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
