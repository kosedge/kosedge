/**
 * Fail-closed Line Curve guards.
 * No fabricated prices, no interpolation, no unbound model runs.
 */

import { isValidAmericanOdds } from "@/lib/line-curve/american";
import {
  LINE_CURVE_MAX_AGE_MS,
  type LineCurveClosed,
  type LineCurveFailureCode,
  type ModelMarginInput,
  type OddsAltSnapshot,
  type PostedAlt,
} from "@/lib/line-curve/types";

export function closed(
  code: LineCurveFailureCode,
  message: string,
): LineCurveClosed {
  return { ok: false, code, message, label: "INSUFFICIENT" };
}

export function isLineCurveClosed(value: unknown): value is LineCurveClosed {
  return Boolean(
    value &&
    typeof value === "object" &&
    (value as LineCurveClosed).ok === false &&
    (value as LineCurveClosed).label === "INSUFFICIENT",
  );
}

export function assertSnapshotFresh(
  snapshot: OddsAltSnapshot,
  nowMs: number = Date.now(),
): LineCurveClosed | null {
  if (snapshot.source === "research_fixture") return null;
  if (
    !snapshot.capturedAt ||
    !Number.isFinite(Date.parse(snapshot.capturedAt))
  ) {
    return closed("stale_odds", "Odds vintage missing or unparseable.");
  }
  const age = nowMs - Date.parse(snapshot.capturedAt);
  if (age < 0 || age > LINE_CURVE_MAX_AGE_MS) {
    return closed(
      "stale_odds",
      `Odds vintage is stale or in the future (max age ${LINE_CURVE_MAX_AGE_MS}ms).`,
    );
  }
  return null;
}

export function assertSnapshotIdentity(
  snapshot: OddsAltSnapshot,
): LineCurveClosed | null {
  if (!snapshot.eventId?.trim()) {
    return closed("missing_snapshot", "Odds snapshot is missing event_id.");
  }
  if (!snapshot.oddsSnapshotId?.trim()) {
    return closed(
      "missing_snapshot",
      "Odds snapshot is missing oddsSnapshotId.",
    );
  }
  if (!snapshot.book?.trim()) {
    return closed("missing_odds", "Odds snapshot is missing book.");
  }
  if (!snapshot.homeTeam?.trim() || !snapshot.awayTeam?.trim()) {
    return closed("missing_odds", "Odds snapshot is missing home/away teams.");
  }
  return null;
}

export function assertModelBound(
  model: ModelMarginInput | null | undefined,
  snapshot: OddsAltSnapshot,
): LineCurveClosed | null {
  if (!model || !model.modelRunId?.trim()) {
    return closed(
      "missing_model_run",
      "Model run/version is missing — refuse to price.",
    );
  }
  if (!model.eventId?.trim() || model.eventId !== snapshot.eventId) {
    return closed(
      "unbound_model_event",
      "Model run cannot be tied to this exact event.",
    );
  }
  if (
    !Number.isFinite(model.modelSpreadHome) ||
    !Number.isFinite(model.expectedHomeScore) ||
    !Number.isFinite(model.expectedAwayScore) ||
    !Number.isFinite(model.marginSd) ||
    model.marginSd <= 0
  ) {
    return closed(
      "missing_model_run",
      "Model fair margin / scores / uncertainty are incomplete.",
    );
  }
  return null;
}

export function assertAlternateMarketAvailable(
  alts: PostedAlt[],
  baseLine: number,
): LineCurveClosed | null {
  const distinct = new Set(alts.map((a) => a.line));
  const hasNonBase = [...distinct].some((line) => line !== baseLine);
  if (!hasNonBase) {
    return closed(
      "unavailable_alt_market",
      "Alternate-spread market is unavailable — refuse to invent a curve from the mainline only.",
    );
  }
  return null;
}

export function assertPostedAlts(alts: PostedAlt[]): LineCurveClosed | null {
  if (!alts.length) {
    return closed(
      "unavailable_alt_market",
      "No posted alternate spreads for this side.",
    );
  }
  const byLine = new Map<number, number>();
  for (const alt of alts) {
    if (!Number.isFinite(alt.line)) {
      return closed(
        "inconsistent_odds",
        "Alternate line is not a finite number.",
      );
    }
    if (!isValidAmericanOdds(alt.americanOdds)) {
      return closed(
        "invalid_american",
        `Invalid American odds ${String(alt.americanOdds)} at ${alt.line}.`,
      );
    }
    const prev = byLine.get(alt.line);
    if (prev != null && prev !== alt.americanOdds) {
      return closed(
        "duplicate_odds",
        `Duplicate disagreeing prices at ${alt.line}: ${prev} vs ${alt.americanOdds}.`,
      );
    }
    byLine.set(alt.line, alt.americanOdds);
  }
  return null;
}

export function assertBaseLine(
  baseLine: number | undefined,
  alts: PostedAlt[],
): LineCurveClosed | null {
  if (baseLine == null || !Number.isFinite(baseLine)) {
    return closed("missing_odds", "Base market spread is missing.");
  }
  if (!alts.some((a) => a.line === baseLine)) {
    return closed(
      "missing_odds",
      "Base market spread has no posted price on the alt surface (no interpolation).",
    );
  }
  return null;
}

export function uniqueAlts(alts: PostedAlt[]): PostedAlt[] {
  const byLine = new Map<number, PostedAlt>();
  for (const alt of alts) {
    const prev = byLine.get(alt.line);
    if (!prev) {
      byLine.set(alt.line, alt);
      continue;
    }
    if (prev.americanOdds !== alt.americanOdds) {
      throw new Error("duplicate_odds");
    }
  }
  return [...byLine.values()].sort((a, b) => a.line - b.line);
}
