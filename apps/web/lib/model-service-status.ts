/**
 * Shared rules for model-service board errors vs honest empty / partial states.
 * Avoid "unreachable" banners when the desk still has usable content or an honest empty slate.
 */

import { UpstreamTimeoutError } from "@/lib/upstream-fetch";

export const HONEST_EMPTY_SLATE_STATUSES = new Set([
  "offseason_empty",
  "no_projections_yet",
  "empty",
  "no_slate",
  "preseason_empty",
  "no_reg_week_games",
  "schema_not_ready",
]);

/** NFL preseason window before regular-season Week 1 pricing desks are expected. */
export function isNflPreseasonDeskWindow(now = new Date()): boolean {
  const month = now.getUTCMonth(); // 0-indexed
  const day = now.getUTCDate();
  // Aug–early Sep: camp / PRE — REG week boards may legitimately be empty.
  if (month === 7) return true;
  if (month === 8 && day <= 10) return true;
  return false;
}

export function isTransportFailureMessage(error?: string | null): boolean {
  if (!error?.trim()) return false;
  const lower = error.toLowerCase();
  return (
    lower.includes("unable to reach model") ||
    lower.includes("model service returned") ||
    lower.includes("timed out") ||
    lower.includes("upstream timed out") ||
    lower.includes("aborted") ||
    lower.includes("fetch failed")
  );
}

/**
 * When the model shell loads but REG-week boards are empty (preseason), treat
 * transport failures as honest empty rather than degraded outage banners.
 */
export function inferHonestEmptySlateStatus(opts: {
  season?: number;
  error?: string | null;
  cause?: unknown;
  /** Explicit API slate_status when available */
  apiStatus?: string | null;
}): string | null {
  const api = opts.apiStatus?.trim();
  if (api && HONEST_EMPTY_SLATE_STATUSES.has(api)) return api;

  const season = opts.season ?? new Date().getFullYear();
  const currentYear = new Date().getFullYear();
  const inPreseasonWindow = isNflPreseasonDeskWindow();
  const futureOrCurrentSeason = season >= currentYear;

  if (!isTransportFailureMessage(opts.error) && !(opts.cause instanceof UpstreamTimeoutError)) {
    return null;
  }

  // Real upstream errors (503/502) stay degraded unless explicitly schema-not-ready.
  if (
    opts.error?.includes("503") ||
    opts.error?.includes("502") ||
    opts.error?.includes("500")
  ) {
    if (opts.error?.includes("schema_not_ready")) {
      return "schema_not_ready";
    }
    return null;
  }

  if (futureOrCurrentSeason && inPreseasonWindow) {
    return "preseason_empty";
  }

  if (opts.error?.includes("schema_not_ready")) {
    return "schema_not_ready";
  }

  return null;
}

export function shouldShowModelUnreachableBanner(opts: {
  error?: string | null;
  hasContent?: boolean;
  slateStatus?: string | null;
}): boolean {
  if (!opts.error?.trim()) return false;
  if (opts.hasContent) return false;
  const status = opts.slateStatus?.trim();
  if (status && HONEST_EMPTY_SLATE_STATUSES.has(status)) return false;
  if (
    inferHonestEmptySlateStatus({
      error: opts.error,
      apiStatus: status,
    })
  ) {
    return false;
  }
  return true;
}

export function honestEmptySlateCopy(status?: string | null): string {
  switch (status?.trim()) {
    case "preseason_empty":
    case "no_reg_week_games":
      return "No regular-season games in this window yet — expected during camp and early preseason. Use Camp Desk, Fantasy Mock, Survivor, Game Boxes, and Power Ratings now; KosEdge does not invent fair lines or edges until the REG slate posts.";
    case "offseason_empty":
    case "no_slate":
      return "No slate games in the current window. Check back when the season schedule is live.";
    case "no_projections_yet":
    case "schema_not_ready":
      return "Projections are not posted for this window yet. The desk shell is live — model rows will populate when the pipeline publishes.";
    default:
      return "No board rows in the current window yet.";
  }
}

export function modelUnreachableCopy(error?: string | null): string {
  if (error?.includes("MODEL_SERVICE_URL")) {
    return "Model service is not configured for this environment.";
  }
  return "Model service is temporarily unreachable. Retry shortly — local fallbacks may still load below.";
}
