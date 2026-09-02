import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type NhlPropBoardRow = {
  playerId: string;
  playerName: string;
  team: string;
  playerType: "skater" | "goalie" | string;
  marketKey: string;
  /** Trusted Best only; cleared to null (UI —) when untrusted/missing/starter-unknown. */
  line: number | null;
  best: number | null;
  modelMean: number | null;
  modelStd: number | null;
  /** mean − trusted Best; null when Best cleared. */
  edge: number | null;
  overProb: number | null;
  underProb: number | null;
  edgeOver: number | null;
  edgeUnder: number | null;
  confidence: number | null;
  tag: "PASS";
  tagSide: null;
  reason: string | null;
  stakeEligible: false;
  bestTrusted: boolean;
};

export type NhlPropsBoardResponse = {
  asOfDate: string;
  modelVersion: string;
  workerBuildId: string;
  count: number;
  lines: NhlPropBoardRow[];
  phase?: string;
  darkOnly?: boolean;
  starterGate?: string;
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

/** Ch6 dark: never surface PLAY/LEAN even if upstream mis-tags. */
function darkTag(_raw: unknown): "PASS" {
  return "PASS";
}

export async function fetchNhlPropsBoard(options?: {
  marketKey?: string;
  tag?: string;
  limit?: number;
}): Promise<NhlPropsBoardResponse> {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) {
    return {
      asOfDate: new Date().toISOString().slice(0, 10),
      modelVersion: "nhl-props-ch6-dark-v1",
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

  const url = `${base}/nhl/props/board?${params.toString()}`;
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
        modelVersion: "nhl-props-ch6-dark-v1",
        workerBuildId: "",
        count: 0,
        lines: [],
        darkOnly: true,
        error: `Model service returned ${res.status}`,
      };
    }
    const payload = (await res.json()) as Record<string, unknown>;
    const rawLines = Array.isArray(payload.lines) ? payload.lines : [];
    const lines: NhlPropBoardRow[] = rawLines.map((row) => {
      const r = row as Record<string, unknown>;
      const diag =
        r.diagnostics && typeof r.diagnostics === "object"
          ? (r.diagnostics as Record<string, unknown>)
          : {};
      return {
        playerId: String(r.player_id ?? ""),
        playerName: String(r.player_name ?? ""),
        team: String(r.team ?? ""),
        playerType: String(r.player_type ?? "skater"),
        marketKey: String(r.market_key ?? ""),
        line: toNumberOrNull(r.line),
        best: toNumberOrNull(r.best),
        modelMean: toNumberOrNull(r.model_mean),
        modelStd: toNumberOrNull(r.model_std),
        edge: toNumberOrNull(r.edge),
        overProb: toNumberOrNull(r.over_prob),
        underProb: toNumberOrNull(r.under_prob),
        edgeOver: toNumberOrNull(r.edge_over),
        edgeUnder: toNumberOrNull(r.edge_under),
        confidence: toNumberOrNull(r.confidence),
        tag: darkTag(r.tag),
        tagSide: null,
        reason: diag.reason != null ? String(diag.reason) : null,
        stakeEligible: false,
        bestTrusted: Boolean(diag.best_trusted),
      };
    });
    return {
      asOfDate: String(
        payload.as_of_date ?? new Date().toISOString().slice(0, 10),
      ),
      modelVersion: String(payload.model_version ?? "nhl-props-ch6-dark-v1"),
      workerBuildId: String(payload.worker_build_id ?? ""),
      count: lines.length,
      lines,
      phase: payload.phase != null ? String(payload.phase) : "ch6_dark",
      darkOnly: true,
      starterGate:
        payload.STARTER_GATE != null ? String(payload.STARTER_GATE) : "unknown",
      message: payload.message != null ? String(payload.message) : undefined,
    };
  } catch (err) {
    return {
      asOfDate: new Date().toISOString().slice(0, 10),
      modelVersion: "nhl-props-ch6-dark-v1",
      workerBuildId: "",
      count: 0,
      lines: [],
      darkOnly: true,
      error: err instanceof Error ? err.message : "fetch failed",
    };
  }
}
