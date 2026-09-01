import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type NbaPropBoardRow = {
  playerId: string;
  playerName: string;
  team: string;
  marketKey: string;
  line: number | null;
  modelMean: number | null;
  modelStd: number | null;
  overProb: number | null;
  underProb: number | null;
  edgeOver: number | null;
  edgeUnder: number | null;
  confidence: number | null;
  tag: string;
  tagSide: string | null;
  reason: string | null;
  stakeEligible: false;
};

export type NbaPropsBoardResponse = {
  asOfDate: string;
  modelVersion: string;
  workerBuildId: string;
  count: number;
  lines: NbaPropBoardRow[];
  ouBalance?: {
    play_n?: number;
    play_over?: number;
    play_under?: number;
    play_under_pct?: number | null;
    balanced?: boolean;
  };
  phase?: string;
  darkOnly?: boolean;
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

/** Ch6 dark: never surface PLAY/WATCH even if upstream mis-tags. */
function darkTag(raw: unknown): "PASS" {
  void raw;
  return "PASS";
}

export async function fetchNbaPropsBoard(options?: {
  marketKey?: string;
  tag?: string;
  limit?: number;
}): Promise<NbaPropsBoardResponse> {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) {
    return {
      asOfDate: new Date().toISOString().slice(0, 10),
      modelVersion: "nba-props-ch6-dark-v1",
      workerBuildId: "",
      count: 0,
      lines: [],
      darkOnly: true,
      error: "MODEL_SERVICE_URL not configured",
    };
  }

  const params = new URLSearchParams();
  params.set("source", "season_engine");
  if (options?.marketKey) params.set("market_key", options.marketKey);
  if (options?.tag) params.set("tag", options.tag);
  params.set("limit", String(options?.limit ?? 200));

  const url = `${base}/nba/props/board?${params.toString()}`;
  try {
    const res = await upstreamFetch(url, {
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      headers: env.INTERNAL_API_SECRET
        ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
        : undefined,
    });
    if (!res.ok) {
      return {
        asOfDate: new Date().toISOString().slice(0, 10),
        modelVersion: "nba-props-ch6-dark-v1",
        workerBuildId: "",
        count: 0,
        lines: [],
        darkOnly: true,
        error: `props board HTTP ${res.status}`,
      };
    }
    const raw = (await res.json()) as Record<string, unknown>;
    const linesRaw = Array.isArray(raw.lines) ? raw.lines : [];
    const lines: NbaPropBoardRow[] = linesRaw.map((row) => {
      const r = row as Record<string, unknown>;
      const diag = (r.diagnostics || {}) as Record<string, unknown>;
      return {
        playerId: String(r.player_id ?? ""),
        playerName: String(r.player_name ?? ""),
        team: String(r.team ?? ""),
        marketKey: String(r.market_key ?? ""),
        line: toNumberOrNull(r.line),
        modelMean: toNumberOrNull(r.model_mean),
        modelStd: toNumberOrNull(r.model_std),
        overProb: toNumberOrNull(r.over_prob),
        underProb: toNumberOrNull(r.under_prob),
        edgeOver: toNumberOrNull(r.edge_over),
        edgeUnder: toNumberOrNull(r.edge_under),
        confidence: toNumberOrNull(r.confidence),
        tag: darkTag(diag.tag ?? r.tag),
        tagSide: null,
        reason: typeof diag.reason === "string" ? diag.reason : null,
        stakeEligible: false,
      };
    });
    return {
      asOfDate: String(raw.as_of_date ?? "").slice(0, 10),
      modelVersion: String(raw.model_version ?? "nba-props-ch6-dark-v1"),
      workerBuildId: String(raw.worker_build_id ?? ""),
      count: lines.length,
      lines,
      ouBalance: {
        play_n: 0,
        play_over: 0,
        play_under: 0,
        play_under_pct: null,
        balanced: true,
      },
      phase: typeof raw.phase === "string" ? raw.phase : "ch6_dark",
      darkOnly: true,
      message: typeof raw.message === "string" ? raw.message : undefined,
    };
  } catch (err) {
    return {
      asOfDate: new Date().toISOString().slice(0, 10),
      modelVersion: "nba-props-ch6-dark-v1",
      workerBuildId: "",
      count: 0,
      lines: [],
      darkOnly: true,
      error: err instanceof Error ? err.message : "props fetch failed",
    };
  }
}
