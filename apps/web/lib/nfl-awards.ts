import "server-only";
import { env } from "@/lib/config/env";
import { loadPlayerSeasonTotalsSpine } from "@/lib/nfl-player-season-totals-spine";

export type NflAwardType = "mvp" | "opoy";

export type NflAwardProjectionRow = {
  season: number;
  award: NflAwardType;
  modelVersion: string;
  playerId: string;
  playerUid: string | null;
  playerName: string;
  team: string;
  position: string;
  rankOverall: number;
  awardScore: number;
  teamSuccessScore: number;
  statComposite: number;
  teamExpectedWins: number;
  teamDivisionTitleProb: number;
  teamPlayoffProb: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  methodologyPayload: Record<string, unknown> | null;
  updatedAt: string | null;
};

export type NflAwardProjectionsResponse = {
  count: number;
  rows: NflAwardProjectionRow[];
  error?: string;
};

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function normalizeAwardRow(
  raw: Record<string, unknown>,
): NflAwardProjectionRow {
  return {
    season: toNumber(raw.season),
    award: raw.award === "opoy" ? "opoy" : "mvp",
    modelVersion: String(raw.model_version ?? ""),
    playerId: String(raw.player_id ?? ""),
    playerUid: typeof raw.player_uid === "string" ? raw.player_uid : null,
    playerName: String(raw.player_name ?? "Unknown player"),
    team: String(raw.team ?? "—"),
    position: String(raw.position ?? "—"),
    rankOverall: toNumber(raw.rank_overall),
    awardScore: toNumber(raw.award_score),
    teamSuccessScore: toNumber(raw.team_success_score),
    statComposite: toNumber(raw.stat_composite),
    teamExpectedWins: toNumber(raw.team_expected_wins),
    teamDivisionTitleProb: toNumber(raw.team_division_title_prob),
    teamPlayoffProb: toNumber(raw.team_playoff_prob),
    passYardsTotal: toNumber(raw.pass_yards_total),
    rushYardsTotal: toNumber(raw.rush_yards_total),
    receivingYardsTotal: toNumber(raw.receiving_yards_total),
    passTdsTotal: toNumber(raw.pass_tds_total),
    rushTdsTotal: toNumber(raw.rush_tds_total),
    recTdsTotal: toNumber(raw.rec_tds_total),
    methodologyPayload:
      raw.methodology_payload && typeof raw.methodology_payload === "object"
        ? (raw.methodology_payload as Record<string, unknown>)
        : null,
    updatedAt: typeof raw.updated_at === "string" ? raw.updated_at : null,
  };
}

export async function fetchNflAwardProjections(params: {
  season: number;
  award?: NflAwardType;
  modelVersion?: string;
  limit?: number;
}): Promise<NflAwardProjectionsResponse> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      count: 0,
      rows: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/awards/projections`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("model_version", params.modelVersion ?? "nfl-player-v1");
  if (params.award) url.searchParams.set("award", params.award);
  url.searchParams.set("limit", String(params.limit ?? 20));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(url.toString(), {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      return {
        count: 0,
        rows: [],
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      count?: number;
      rows?: Array<Record<string, unknown>>;
    };
    const rows = Array.isArray(payload.rows)
      ? payload.rows.map(normalizeAwardRow)
      : [];
    // Overlay spine yards/TDs so awards print the same numbers as fantasy /
    // projections (award_score ranking stays from the awards materializer).
    const spine = await loadPlayerSeasonTotalsSpine({
      season: params.season,
      limit: 500,
    });
    if (spine.source === "spine-fantasy" && spine.rows.length > 0) {
      const byId = new Map(
        spine.rows.map((r) => [`${r.team.toUpperCase()}:${r.playerKey}`, r]),
      );
      const byName = new Map(
        spine.rows.map((r) => [
          `${r.team.toUpperCase()}:${r.playerName.toLowerCase().replace(/[^a-z0-9]+/g, "")}`,
          r,
        ]),
      );
      for (const row of rows) {
        const hit =
          byId.get(`${row.team.toUpperCase()}:${row.playerId}`) ||
          byName.get(
            `${row.team.toUpperCase()}:${row.playerName.toLowerCase().replace(/[^a-z0-9]+/g, "")}`,
          );
        if (!hit) continue;
        row.passYardsTotal = hit.passYardsTotal;
        row.rushYardsTotal = hit.rushYardsTotal;
        row.receivingYardsTotal = hit.receivingYardsTotal;
        row.passTdsTotal = hit.passTdsTotal;
        row.rushTdsTotal = hit.rushTdsTotal;
        row.recTdsTotal = hit.recTdsTotal;
      }
    }
    return {
      count: typeof payload.count === "number" ? payload.count : rows.length,
      rows,
    };
  } catch {
    return { count: 0, rows: [], error: "Unable to reach model service." };
  } finally {
    clearTimeout(timeout);
  }
}

export function awardStatLine(row: NflAwardProjectionRow): string {
  const isPasser = row.position === "QB";
  if (isPasser) {
    const parts = [
      `${row.passYardsTotal.toFixed(0)} pass yds`,
      `${row.passTdsTotal.toFixed(1)} pass TD`,
    ];
    if (row.rushYardsTotal >= 50)
      parts.push(`${row.rushYardsTotal.toFixed(0)} rush yds`);
    if (row.rushTdsTotal >= 1)
      parts.push(`${row.rushTdsTotal.toFixed(1)} rush TD`);
    return parts.join(" · ");
  }
  const parts: string[] = [];
  if (row.rushYardsTotal >= 25)
    parts.push(`${row.rushYardsTotal.toFixed(0)} rush yds`);
  if (row.receivingYardsTotal >= 25)
    parts.push(`${row.receivingYardsTotal.toFixed(0)} rec yds`);
  const totalTds = row.rushTdsTotal + row.recTdsTotal;
  parts.push(`${totalTds.toFixed(1)} total TD`);
  return parts.join(" · ");
}
