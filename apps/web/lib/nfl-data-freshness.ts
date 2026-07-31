import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type NflDataFreshnessPayload = {
  status: "ok" | "degraded" | "failed" | string;
  in_season?: boolean;
  season?: number | null;
  week?: number | null;
  blockers?: string[];
  warnings?: string[];
  product_guidance?: {
    fair_lines_board?: string;
    play_stake_tags?: string;
    subscription_claim?: string;
  };
  checked_at?: string;
  error?: string;
};

export async function fetchNflDataFreshness(): Promise<NflDataFreshnessPayload> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      status: "failed",
      error: "MODEL_SERVICE_URL is not configured.",
      blockers: ["model_service_unconfigured"],
    };
  }
  try {
    const res = await upstreamFetch(
      `${base.replace(/\/$/, "")}/health/nfl-data-freshness`,
      {
        cache: "no-store",
        next: { revalidate: 0 },
        timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
      },
    );
    const body = (await res
      .json()
      .catch(() => ({}))) as NflDataFreshnessPayload & {
      detail?: NflDataFreshnessPayload;
    };
    if (!res.ok) {
      const detail =
        body.detail && typeof body.detail === "object" ? body.detail : body;
      return {
        status: String(detail.status || "degraded"),
        in_season: detail.in_season,
        season: detail.season,
        week: detail.week,
        blockers: detail.blockers || ["freshness_http_error"],
        warnings: detail.warnings,
        product_guidance: detail.product_guidance,
        checked_at: detail.checked_at,
        error: detail.error,
      };
    }
    return body;
  } catch (err) {
    return {
      status: "failed",
      error: err instanceof Error ? err.message : "freshness_fetch_failed",
      blockers: ["freshness_fetch_failed"],
    };
  }
}
