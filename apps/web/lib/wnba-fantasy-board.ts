import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type WnbaFantasyRow = {
  rank: number;
  playerId: string;
  playerName: string;
  team: string;
  minutes: number | null;
  pts: number | null;
  reb: number | null;
  ast: number | null;
  stl: number | null;
  blk: number | null;
  tov: number | null;
  threes: number | null;
  fantasyPts: number | null;
  seasonFantasyPts: number | null;
};

export type WnbaFantasyBoardResponse = {
  view: string;
  fantasyVersion: string;
  scoringProfile: string;
  scoringMap: Record<string, number>;
  seasonGames: number | null;
  count: number;
  rows: WnbaFantasyRow[];
  maxTeamPtsDrift: number | null;
  residualCap: number | null;
  minuteGridSum: number | null;
  message?: string;
  error?: string;
};

function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export async function fetchWnbaFantasyBoard(options?: {
  view?: "season" | "slate";
  team?: string;
  limit?: number;
}): Promise<WnbaFantasyBoardResponse> {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) {
    return {
      view: options?.view ?? "season",
      fantasyVersion: "wnba-fantasy-ch7-v1",
      scoringProfile: "kos_default_points",
      scoringMap: {},
      seasonGames: 40,
      count: 0,
      rows: [],
      maxTeamPtsDrift: null,
      residualCap: null,
      minuteGridSum: 200,
      error: "MODEL_SERVICE_URL not configured",
    };
  }

  const params = new URLSearchParams();
  params.set("view", options?.view ?? "season");
  if (options?.team) params.set("team", options.team);
  params.set("limit", String(options?.limit ?? 200));

  const url = `${base}/wnba/fantasy/board?${params.toString()}`;
  try {
    const res = await upstreamFetch(url, {
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      headers: env.INTERNAL_API_SECRET
        ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
        : undefined,
    });
    if (!res.ok) {
      return {
        view: options?.view ?? "season",
        fantasyVersion: "wnba-fantasy-ch7-v1",
        scoringProfile: "kos_default_points",
        scoringMap: {},
        seasonGames: 40,
        count: 0,
        rows: [],
        maxTeamPtsDrift: null,
        residualCap: null,
        minuteGridSum: 200,
        error: `fantasy board HTTP ${res.status}`,
      };
    }
    const raw = (await res.json()) as Record<string, unknown>;
    const rowsRaw = Array.isArray(raw.rows) ? raw.rows : [];
    const rows: WnbaFantasyRow[] = rowsRaw.map((row, idx) => {
      const r = row as Record<string, unknown>;
      return {
        rank: Number(r.rank ?? idx + 1),
        playerId: String(r.player_id ?? ""),
        playerName: String(r.player_name ?? ""),
        team: String(r.team ?? ""),
        minutes: toNumberOrNull(r.MIN),
        pts: toNumberOrNull(r.PTS),
        reb: toNumberOrNull(r.REB),
        ast: toNumberOrNull(r.AST),
        stl: toNumberOrNull(r.STL),
        blk: toNumberOrNull(r.BLK),
        tov: toNumberOrNull(r.TOV),
        threes: toNumberOrNull(r["3PM"]),
        fantasyPts: toNumberOrNull(r.fantasy_pts),
        seasonFantasyPts: toNumberOrNull(r.season_fantasy_pts),
      };
    });
    const scoringMap =
      raw.scoring_map && typeof raw.scoring_map === "object"
        ? (raw.scoring_map as Record<string, number>)
        : {};
    return {
      view: String(raw.view ?? options?.view ?? "season"),
      fantasyVersion: String(raw.fantasy_version ?? "wnba-fantasy-ch7-v1"),
      scoringProfile: String(raw.scoring_profile ?? "kos_default_points"),
      scoringMap,
      seasonGames: toNumberOrNull(raw.season_games),
      count: rows.length,
      rows,
      maxTeamPtsDrift: toNumberOrNull(raw.max_team_pts_drift),
      residualCap: toNumberOrNull(raw.WNBA_TEAM_REBASE_RESIDUAL_CAP),
      minuteGridSum: toNumberOrNull(raw.MINUTE_GRID_SUM_unchanged),
      message: typeof raw.message === "string" ? raw.message : undefined,
    };
  } catch (err) {
    return {
      view: options?.view ?? "season",
      fantasyVersion: "wnba-fantasy-ch7-v1",
      scoringProfile: "kos_default_points",
      scoringMap: {},
      seasonGames: 40,
      count: 0,
      rows: [],
      maxTeamPtsDrift: null,
      residualCap: null,
      minuteGridSum: 200,
      error: err instanceof Error ? err.message : "fantasy fetch failed",
    };
  }
}
