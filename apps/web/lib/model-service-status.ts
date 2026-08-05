/**
 * Shared rules for model-service board errors vs honest empty / partial states.
 * Avoid "unreachable" banners when the desk still has usable content or an honest empty slate.
 */

export const HONEST_EMPTY_SLATE_STATUSES = new Set([
  "offseason_empty",
  "no_projections_yet",
  "empty",
  "no_slate",
]);

export function shouldShowModelUnreachableBanner(opts: {
  error?: string | null;
  hasContent?: boolean;
  slateStatus?: string | null;
}): boolean {
  if (!opts.error?.trim()) return false;
  if (opts.hasContent) return false;
  const status = opts.slateStatus?.trim();
  if (status && HONEST_EMPTY_SLATE_STATUSES.has(status)) return false;
  return true;
}

export function modelUnreachableCopy(error?: string | null): string {
  if (error?.includes("MODEL_SERVICE_URL")) {
    return "Model service is not configured for this environment.";
  }
  return "Model service is temporarily unreachable. Retry shortly — local fallbacks may still load below.";
}
