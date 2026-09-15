import SportHubShell from "@/components/pro/SportHubShell";
import FootballNumbersUnavailable from "@/components/FootballNumbersUnavailable";
import { isFootballPublicNumbersDisabled } from "@/lib/cfb-edge-board-public";
import NflEdgesDeskClient from "@/components/pro/nfl/NflEdgesDeskClient";
import { EDGES_DESK_MIN_CONF_OPTIONS } from "@/lib/nfl-dead-tiers";
import type { DeskMarketType } from "@/lib/nfl-edges-desk-types";

export const dynamic = "force-dynamic";

const DEFAULT_SEASON = 2026;
const DEFAULT_WEEK = 1;
const MARKET_TABS: DeskMarketType[] = ["all", "ml", "spread", "total", "props"];
const MIN_EDGE_OPTIONS_LEN = 3;
const MIN_CONF_OPTIONS = EDGES_DESK_MIN_CONF_OPTIONS;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/**
 * Edges desk — SSR shell parses filters only.
 * Desk data client-fetches /api/nfl/edges-desk (fair ∥ today ∥ props) so HTML
 * is not held open on model-service (Alex waterfall).
 */
export default async function NflEdgesDeskPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  if (isFootballPublicNumbersDisabled("nfl")) {
    return (
      <SportHubShell
        sportKey="nfl"
        sportName="NFL"
        base="/pro/nfl"
        badge="NFL Betting Desk"
        title="NFL Edges"
        summary="Coming soon"
      >
        <FootballNumbersUnavailable sport="nfl" title="NFL Edges" />
      </SportHubShell>
    );
  }

  const search = await searchParams;
  const seasonRaw = Number(firstValue(search.season));
  const weekRaw = Number(firstValue(search.week));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010
      ? seasonRaw
      : DEFAULT_SEASON;
  const week =
    Number.isFinite(weekRaw) && weekRaw >= 1 && weekRaw <= 25
      ? weekRaw
      : DEFAULT_WEEK;
  const marketRaw = (firstValue(search.market) ?? "all").toLowerCase();
  const market = (
    MARKET_TABS.includes(marketRaw as DeskMarketType) ? marketRaw : "all"
  ) as DeskMarketType;
  const minEdgeIdxRaw = Number(firstValue(search.minEdge));
  const minEdgeIdx =
    Number.isFinite(minEdgeIdxRaw) &&
    minEdgeIdxRaw >= 0 &&
    minEdgeIdxRaw < MIN_EDGE_OPTIONS_LEN
      ? minEdgeIdxRaw
      : 1;
  const minConfRaw = Number(firstValue(search.minConf));
  const minConfidence = MIN_CONF_OPTIONS.includes(
    minConfRaw as (typeof MIN_CONF_OPTIONS)[number],
  )
    ? minConfRaw
    : 0;

  return (
    <NflEdgesDeskClient
      season={season}
      week={week}
      market={market}
      minEdgeIdx={minEdgeIdx}
      minConfidence={minConfidence}
    />
  );
}
