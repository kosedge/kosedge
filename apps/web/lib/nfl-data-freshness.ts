import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

/** Owned-data freshness is for Edge Board / KEI rails — not season-engine desks. */
export const NFL_SEASON_ENGINE_DESK_PATHS = [
  "/pro/nfl/model",
  "/pro/nfl/game-boxes",
  "/pro/nfl/survivor",
] as const;

/** Fail fast: Railway freshness hangs when Postgres is unreachable. */
export const NFL_DATA_FRESHNESS_TIMEOUT_MS = Math.min(
  UPSTREAM_TIMEOUT_MS.fast,
  3_000,
);

export type NflDataFreshnessPayload = {
  status: "ok" | "degraded" | "failed" | "probe_unavailable" | string;
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

const TRANSPORT_BLOCKERS = new Set([
  "freshness_fetch_failed",
  "freshness_timeout",
  "freshness_http_error",
  "model_service_unconfigured",
]);

/** Ops ownership/DR signals — real, but not "boards are stale" for guests. */
const OPS_ONLY_BLOCKER_PREFIXES = ["dr_backup:"] as const;

/** Expected gaps (packaged SoT injury book; weather is a KEI stub). Not board SLO failures. */
const RESIDUAL_HONESTY_BLOCKER_PREFIXES = ["injuries:"] as const;

export function isOpsOnlyFreshnessBlocker(blocker: string): boolean {
  return OPS_ONLY_BLOCKER_PREFIXES.some((prefix) => blocker.startsWith(prefix));
}

export function isResidualHonestyFreshnessBlocker(blocker: string): boolean {
  return RESIDUAL_HONESTY_BLOCKER_PREFIXES.some((prefix) =>
    blocker.startsWith(prefix),
  );
}

export function isNflSeasonEngineDeskPath(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  const path = pathname.split("?")[0] || "";
  return NFL_SEASON_ENGINE_DESK_PATHS.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}

/**
 * Show the amber banner only for real owned-data SLO failures.
 * Transport/timeout/DB-probe-unavailable must not look like "boards degraded".
 * Ops-only DR backup lag must not look like board data degradation.
 */
export function shouldShowNflDataFreshnessBanner(
  freshness: NflDataFreshnessPayload,
): boolean {
  if (freshness.status === "ok" || freshness.status === "probe_unavailable") {
    return false;
  }

  const blockers = freshness.blockers ?? [];
  if (blockers.length === 0) {
    // HTTP 503 with empty blockers still means the probe reported non-ok.
    return freshness.status === "degraded" || freshness.status === "failed";
  }

  const onlyTransport = blockers.every((b) => TRANSPORT_BLOCKERS.has(b));
  if (onlyTransport) return false;

  const boardBlockers = blockers.filter(
    (b) =>
      !TRANSPORT_BLOCKERS.has(b) &&
      !isOpsOnlyFreshnessBlocker(b) &&
      !isResidualHonestyFreshnessBlocker(b),
  );
  if (boardBlockers.length === 0) return false;

  return freshness.status === "degraded" || freshness.status === "failed";
}

export async function fetchNflDataFreshness(): Promise<NflDataFreshnessPayload> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      status: "probe_unavailable",
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
        timeoutMs: NFL_DATA_FRESHNESS_TIMEOUT_MS,
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
      const blockers = detail.blockers?.length
        ? detail.blockers
        : ["freshness_http_error"];
      // Empty/non-SLO 503 while DB is down → probe unavailable, not "degraded boards".
      if (
        blockers.every((b) => TRANSPORT_BLOCKERS.has(b)) ||
        (!detail.blockers?.length && !detail.in_season && detail.status == null)
      ) {
        return {
          status: "probe_unavailable",
          in_season: detail.in_season,
          season: detail.season,
          week: detail.week,
          blockers,
          warnings: detail.warnings,
          product_guidance: detail.product_guidance,
          checked_at: detail.checked_at,
          error: detail.error || `freshness HTTP ${res.status}`,
        };
      }
      return {
        status: String(detail.status || "degraded"),
        in_season: detail.in_season,
        season: detail.season,
        week: detail.week,
        blockers,
        warnings: detail.warnings,
        product_guidance: detail.product_guidance,
        checked_at: detail.checked_at,
        error: detail.error,
      };
    }
    return body;
  } catch (err) {
    const message = err instanceof Error ? err.message : "freshness_fetch_failed";
    const timedOut = /timed out/i.test(message);
    return {
      status: "probe_unavailable",
      error: message,
      blockers: [timedOut ? "freshness_timeout" : "freshness_fetch_failed"],
    };
  }
}
