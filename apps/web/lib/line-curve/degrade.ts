/**
 * Line-curve three-tier degrade (R7 / S6). Never live-pulls. Never fabricates prices.
 *
 * (1) job snapshot ≤ freshness TTL → fresh
 * (2) stale snapshot ≤ 24 h → STALE (optimize disabled)
 * (3) none → main-line model / researchOnly, reason alt_market_unavailable
 */

import { closed } from "@/lib/line-curve/guardrails";
import type { OddsAltSnapshot } from "@/lib/line-curve/types";

export const LINE_CURVE_FRESH_TTL_MS = 30 * 60 * 1000;
export const LINE_CURVE_NEAR_KICK_TTL_MS = 5 * 60 * 1000;
export const LINE_CURVE_NEAR_KICK_WINDOW_MS = 3 * 60 * 60 * 1000;
export const LINE_CURVE_STALE_MAX_MS = 24 * 60 * 60 * 1000;
export const LINE_CURVE_NONE_CACHE_MAX_MS = 60 * 1000;

export type LineCurveDegradeTier = "fresh" | "stale" | "none";

export type LineCurveDegradeResult = {
  tier: LineCurveDegradeTier;
  reason: "ok" | "stale" | "alt_market_unavailable";
  researchOnly: boolean;
  optimizeDisabled: boolean;
  label: string | null;
  asOf: string | null;
};

const degradeCounts = new Map<string, number>();

export function recordLineCurveDegrade(reason: string): void {
  degradeCounts.set(reason, (degradeCounts.get(reason) ?? 0) + 1);
}

export function getLineCurveDegradeCounts(): Record<string, number> {
  return Object.fromEntries(degradeCounts);
}

export function resetLineCurveDegradeCounts(): void {
  degradeCounts.clear();
}

export function classifyAltSnapshot(
  snapshot: OddsAltSnapshot | null | undefined,
  nowMs: number = Date.now(),
  commenceTime?: string | null,
): LineCurveDegradeResult {
  if (!snapshot?.capturedAt) {
    recordLineCurveDegrade("alt_market_unavailable");
    return {
      tier: "none",
      reason: "alt_market_unavailable",
      researchOnly: true,
      optimizeDisabled: true,
      label: "Market alt prices unavailable",
      asOf: null,
    };
  }
  const capturedMs = Date.parse(snapshot.capturedAt);
  if (!Number.isFinite(capturedMs)) {
    recordLineCurveDegrade("alt_market_unavailable");
    return {
      tier: "none",
      reason: "alt_market_unavailable",
      researchOnly: true,
      optimizeDisabled: true,
      label: "Market alt prices unavailable",
      asOf: snapshot.capturedAt,
    };
  }
  const age = nowMs - capturedMs;
  const kickMs = commenceTime ? Date.parse(commenceTime) : Number.NaN;
  const nearKick =
    Number.isFinite(kickMs) &&
    kickMs - nowMs <= LINE_CURVE_NEAR_KICK_WINDOW_MS &&
    kickMs - nowMs >= 0;
  const freshTtl = nearKick
    ? LINE_CURVE_NEAR_KICK_TTL_MS
    : LINE_CURVE_FRESH_TTL_MS;

  if (age >= 0 && age <= freshTtl) {
    recordLineCurveDegrade("fresh");
    return {
      tier: "fresh",
      reason: "ok",
      researchOnly: false,
      optimizeDisabled: false,
      label: null,
      asOf: snapshot.capturedAt,
    };
  }
  if (age >= 0 && age <= LINE_CURVE_STALE_MAX_MS) {
    recordLineCurveDegrade("stale");
    return {
      tier: "stale",
      reason: "stale",
      researchOnly: true,
      optimizeDisabled: true,
      label: "STALE",
      asOf: snapshot.capturedAt,
    };
  }
  recordLineCurveDegrade("alt_market_unavailable");
  return {
    tier: "none",
    reason: "alt_market_unavailable",
    researchOnly: true,
    optimizeDisabled: true,
    label: "Market alt prices unavailable",
    asOf: snapshot.capturedAt,
  };
}

export function lineCurveUnavailablePayload(message?: string) {
  return {
    researchOnly: true,
    reason: "alt_market_unavailable" as const,
    availability: "unavailable" as const,
    label: "Market alt prices unavailable",
    curve: closed(
      "unavailable_alt_market",
      message ?? "Market alt prices unavailable",
    ),
  };
}
