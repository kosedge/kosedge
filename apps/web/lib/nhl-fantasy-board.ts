import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type NhlFantasyRow = {
  rank: number;
  playerId: string;
  playerName: string;
  team: string;
  playerType: "skater" | "goalie" | string;
  toi: number | null;
  g: number | null;
  a: number | null;
  p: number | null;
  sog: number | null;
  startShare: number | null;
  saves: number | null;
  fantasyPts: number | null;
  seasonFantasyPts: number | null;
};

export type NhlFantasyBoardResponse = {
  view: string;
  fantasyVersion: string;
  scoringProfile: string;
  scoringMap: Record<string, number>;
  count: number;
  rows: NhlFantasyRow[];
  maxTeamGDrift: number | null;
  residualCap: number | null;
  goalieStartShareOk: boolean | null;
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

export async function fetchNhlFantasyBoard(options?: {
  view?: "season" | "slate";
  team?: string;
  limit?: number;
}): Promise<NhlFantasyBoardResponse> {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) {
    return {
      view: options?.view ?? "season",
      fantasyVersion: "nhl-fantasy-ch7-v1",
      scoringProfile: "kos_default_points",
      scoringMap: {},
      count: 0,
      rows: [],
      maxTeamGDrift: null,
      residualCap: null,
      goalieStartShareOk: null,
      error: "MODEL_SERVICE_URL not configured",
    };
  }

  const params = new URLSearchParams();
  params.set("view", options?.view ?? "season");
  if (options?.team) params.set("team", options.team);
  params.set("limit", String(options?.limit ?? 200));

  const url = `${base}/nhl/fantasy/board?${params.toString()}`;
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
        fantasyVersion: "nhl-fantasy-ch7-v1",
        scoringProfile: "kos_default_points",
        scoringMap: {},
        count: 0,
        rows: [],
        maxTeamGDrift: null,
        residualCap: null,
        goalieStartShareOk: null,
        error: `fantasy board HTTP ${res.status}`,
      };
    }
    const raw = (await res.json()) as Record<string, unknown>;
    const rowsRaw = Array.isArray(raw.rows) ? raw.rows : [];
    const rows: NhlFantasyRow[] = rowsRaw.map((row, idx) => {
      const r = row as Record<string, unknown>;
      return {
        rank: Number(r.rank ?? idx + 1),
        playerId: String(r.player_id ?? ""),
        playerName: String(r.player_name ?? ""),
        team: String(r.team ?? ""),
        playerType: String(r.player_type ?? "skater"),
        toi: toNumberOrNull(r.TOI),
        g: toNumberOrNull(r.G),
        a: toNumberOrNull(r.A),
        p: toNumberOrNull(r.P),
        sog: toNumberOrNull(r.SOG),
        startShare: toNumberOrNull(r.start_share),
        saves: toNumberOrNull(r.SAVES),
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
      fantasyVersion: String(raw.fantasy_version ?? "nhl-fantasy-ch7-v1"),
      scoringProfile: String(raw.scoring_profile ?? "kos_default_points"),
      scoringMap,
      count: rows.length,
      rows,
      maxTeamGDrift: toNumberOrNull(raw.max_team_g_drift),
      residualCap: toNumberOrNull(raw.NHL_TEAM_REBASE_RESIDUAL_CAP),
      goalieStartShareOk:
        typeof raw.goalie_start_share_ok === "boolean"
          ? raw.goalie_start_share_ok
          : null,
      message: typeof raw.message === "string" ? raw.message : undefined,
    };
  } catch (err) {
    return {
      view: options?.view ?? "season",
      fantasyVersion: "nhl-fantasy-ch7-v1",
      scoringProfile: "kos_default_points",
      scoringMap: {},
      count: 0,
      rows: [],
      maxTeamGDrift: null,
      residualCap: null,
      goalieStartShareOk: null,
      error: err instanceof Error ? err.message : "fantasy fetch failed",
    };
  }
}
