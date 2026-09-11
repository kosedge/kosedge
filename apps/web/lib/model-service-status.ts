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
  "not_connected",
  "no_odds_yet",
]);

/**
 * True only when REG Week pricing desks are not expected yet.
 * Soft launch 2026: Week 1 REG fair-lines / Edge Board are live — do not mask
 * model-service transport failures as "expected empty" during camp.
 */
export function isNflPreseasonDeskWindow(_now = new Date()): boolean {
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

  if (
    !isTransportFailureMessage(opts.error) &&
    !(opts.cause instanceof UpstreamTimeoutError)
  ) {
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
      return "No games currently scheduled for this slate. Model lines will appear when they are available.";
    case "offseason_empty":
    case "no_slate":
      return "No slate games in the current window. Check back when the season schedule is live.";
    case "no_projections_yet":
    case "schema_not_ready":
      return "Projections are not posted for this window yet. The desk shell is live — model rows will populate when the pipeline publishes.";
    case "not_connected":
    case "no_odds_yet":
      return "Not connected / no odds yet — we do not invent book prices or KEI lines.";
    default:
      return "No board rows in the current window yet.";
  }
}

export const MODEL_DATA_UNAVAILABLE_COPY =
  "Model data temporarily unavailable.";

export const LEGITIMATE_EMPTY_SLATE_COPY =
  "No games currently scheduled for this slate.";

export function modelUnreachableCopy(_error?: string | null): string {
  return MODEL_DATA_UNAVAILABLE_COPY;
}
