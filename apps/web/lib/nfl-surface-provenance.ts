/**
 * NFL Enterprise Green — cross-surface customer-truth envelope.
 *
 * Authority: PE Edges cert-bind + cross-surface + Mobile M1 papers
 * and PE addendum v1.1 (Q1/Q2 CONCUR; E-1..E-3; X-1..X-5; M-1..M-2; N-1).
 *
 * Names frozen. Adapters map legacy fields only. No invented run_id / sha.
 * Coming Soon stays ON; NFL_EDGE_BOARD_PUBLIC_ENABLED stays false.
 * Shared Fair Lines certified artifact ONLY (Q1). Edges derives; no
 * Edges-own freeze. PR-4 / D-11 edge-language is NOT adopted (E-2).
 */

import {
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  NFL_EDGES_CERTIFIED_AT,
  NFL_EDGES_CERTIFIED_RUN_ID,
  NFL_EDGES_CERTIFIED_SHA256,
  NFL_EDGES_PUBLIC_ML_ENABLED,
  NFL_EDGES_PUBLIC_SPREAD_ENABLED,
  NFL_EDGES_PUBLIC_TOTAL_ENABLED,
  NFL_FAIR_LINES_CERTIFIED_AT,
  NFL_FAIR_LINES_CERTIFIED_RUN_ID,
  NFL_FAIR_LINES_CERTIFIED_SHA256,
  bindNflFairLinesCertifiedRun,
  isFootballPublicNumbersDisabled,
  isNflEdgeBoardInternalOverride,
  isNflFairLinesCertifiedPublicPaintAllowed,
  isNflFairLinesMarketPublicEnabled,
  type NflFairLinesCertBindReason,
  type NflFairLinesCertObserved,
  type NflFairLinesMarket,
} from "@/lib/cfb-edge-board-public";

/** Allowed cert_status values. No silent defaults. Missing ⇒ NOT_CERTIFIED. */
export type NflCertStatus =
  | "CERTIFIED"
  | "NOT_CERTIFIED"
  | "NOT_CERTIFIABLE";

export type NflCertStatusByMarket = {
  spread: NflCertStatus;
  total: NflCertStatus;
  ml: NflCertStatus;
};

/**
 * Shared customer-truth envelope (X-2). Canonical UI field is linesAsOf.
 * runId + sha256 are the certified Fair Lines identity — never invented.
 * linesAsOf is ISO market vintage from book/row capture — never clock.
 */
export type NflSurfaceProvenance = {
  runId: string | null;
  sha256: string | null;
  linesAsOf: string | null;
  source: string | null;
  certStatus: NflCertStatusByMarket;
};

export type NflSurfaceProvenanceSource =
  | "fair"
  | "desk"
  | "assemble"
  | "props";

export type NflCrossSurfaceReason =
  | "ok"
  | "unbound_certified_slot"
  | "missing_provenance"
  | "run_id_mismatch"
  | "sha256_mismatch"
  | "lines_as_of_mismatch"
  | "missing_lines_as_of"
  | "governed_lines_as_of_forbidden"
  | "cert_status_not_certified"
  | "market_hard_blocked"
  | "edge_language_not_adopted"
  | "props_absent"
  | NflFairLinesCertBindReason;

export type NflCrossSurfaceCheck = {
  ok: boolean;
  reason: NflCrossSurfaceReason;
};

export type NflEdgesPropsStatus = "unavailable";

/** PR-4 / D-11 edge-language is not adopted. Not a CLEAR. */
export const NFL_EDGES_EDGE_LANGUAGE_ADOPTED = false;

/**
 * First-build props contract (N-1 / X-4 / Q3). Applies now — not only
 * after #632 merges. Props stay absent from certified surfaces.
 */
export const NFL_EDGES_PROPS_STATUS: NflEdgesPropsStatus = "unavailable";

const CERT_STATUS_VALUES = new Set<NflCertStatus>([
  "CERTIFIED",
  "NOT_CERTIFIED",
  "NOT_CERTIFIABLE",
]);

function isCertStatus(value: unknown): value is NflCertStatus {
  return (
    typeof value === "string" && CERT_STATUS_VALUES.has(value as NflCertStatus)
  );
}

/**
 * Resolve one market's cert_status from the certified artifact.
 * Missing / invalid ⇒ NOT_CERTIFIED (E-1 / X-2). total + ml are then
 * HARD-BLOCKED to NOT_CERTIFIABLE irrespective of switches (E-1.4).
 */
export function resolveNflCertStatusField(
  raw: unknown,
  market: NflFairLinesMarket,
): NflCertStatus {
  const resolved: NflCertStatus = isCertStatus(raw) ? raw : "NOT_CERTIFIED";
  if (market === "total" || market === "ml") return "NOT_CERTIFIABLE";
  return resolved;
}

/**
 * Unbound / no-artifact cert_status (E-1.5). Spread is NOT CERTIFIED
 * (no prospective n). Total and ML are NOT CERTIFIABLE (6f1a95b9 3T/3M).
 */
export function unboundNflCertStatus(): NflCertStatusByMarket {
  return {
    spread: resolveNflCertStatusField(undefined, "spread"),
    total: resolveNflCertStatusField(undefined, "total"),
    ml: resolveNflCertStatusField(undefined, "ml"),
  };
}

/**
 * Source cert_status from the certified Fair Lines artifact.
 * Do not invent values. Unbound artifact → unboundNflCertStatus().
 */
export function resolveNflCertStatus(
  artifact?: Partial<NflCertStatusByMarket> | null,
): NflCertStatusByMarket {
  if (!artifact) return unboundNflCertStatus();
  return {
    spread: resolveNflCertStatusField(artifact.spread, "spread"),
    total: resolveNflCertStatusField(artifact.total, "total"),
    ml: resolveNflCertStatusField(artifact.ml, "ml"),
  };
}

export function emptyNflSurfaceProvenance(
  source: NflSurfaceProvenanceSource | string | null = null,
): NflSurfaceProvenance {
  return {
    runId: null,
    sha256: null,
    linesAsOf: null,
    source,
    certStatus: unboundNflCertStatus(),
  };
}

function normalizeIsoToken(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const n = value.trim();
  return n ? n : null;
}

function normalizeIdentityToken(
  value: string | null | undefined,
): string | null {
  if (typeof value !== "string") return null;
  const n = value.trim();
  return n ? n : null;
}

function normalizeSha(value: string | null | undefined): string | null {
  const n = normalizeIdentityToken(value);
  return n ? n.toLowerCase() : null;
}

/** Fair Lines oddsAsOf → canonical linesAsOf (name mapping only). */
export function linesAsOfFromFairLinesOddsAsOf(
  oddsAsOf: string | null | undefined,
): string | null {
  return normalizeIsoToken(oddsAsOf);
}

/** Edges marketAsOf → canonical linesAsOf (name mapping only). */
export function linesAsOfFromEdgesMarketAsOf(
  marketAsOf: string | null | undefined,
): string | null {
  return normalizeIsoToken(marketAsOf);
}

/** Assemble linesAsOf → canonical linesAsOf (unchanged). */
export function linesAsOfFromAssemble(
  linesAsOf: string | null | undefined,
): string | null {
  return normalizeIsoToken(linesAsOf);
}

/**
 * X-3: never substitute governed.linesAsOf to keep a board lit.
 * Capture-only. Missing capture → null (caller fail-closes).
 */
export function resolveNflAssembleLinesAsOfFromCapture(
  capturedLinesAsOf: string | null | undefined,
  governedLinesAsOf?: string | null,
): { linesAsOf: string | null; reason: NflCrossSurfaceReason } {
  const captured = normalizeIsoToken(capturedLinesAsOf);
  if (captured) {
    return { linesAsOf: captured, reason: "ok" };
  }
  const governed = normalizeIsoToken(governedLinesAsOf);
  if (governed) {
    return {
      linesAsOf: null,
      reason: "governed_lines_as_of_forbidden",
    };
  }
  return { linesAsOf: null, reason: "missing_lines_as_of" };
}

/**
 * E-3 / X-5: per-row linesAsOf from capture only. Desk-level as-of MUST
 * NOT be inherited onto a missing or older row. Staleness threshold is
 * undefined ⇒ missing/older fail closed (no invented threshold).
 */
export function resolveNflRowLinesAsOf(opts: {
  rowLinesAsOf?: string | null;
  deskLinesAsOf?: string | null;
}): { linesAsOf: string | null; reason: NflCrossSurfaceReason } {
  const row = normalizeIsoToken(opts.rowLinesAsOf);
  if (!row) {
    return { linesAsOf: null, reason: "missing_lines_as_of" };
  }
  const desk = normalizeIsoToken(opts.deskLinesAsOf);
  if (desk) {
    const rowMs = Date.parse(row);
    const deskMs = Date.parse(desk);
    if (
      Number.isFinite(rowMs) &&
      Number.isFinite(deskMs) &&
      rowMs < deskMs
    ) {
      return { linesAsOf: null, reason: "lines_as_of_mismatch" };
    }
  }
  return { linesAsOf: row, reason: "ok" };
}

/**
 * X-3 leakage gate: linesAsOf must be ≤ model as-of and ≤ kickoff.
 * Closing / post-close lines are not shown as available. Missing proofs
 * fail closed (no invented threshold / no clock).
 */
export function nflLinesAsOfLeakageReason(opts: {
  linesAsOf?: string | null;
  modelAsOf?: string | null;
  kickoff?: string | null;
}): NflCrossSurfaceReason {
  const linesAsOf = normalizeIsoToken(opts.linesAsOf);
  if (!linesAsOf) return "missing_lines_as_of";
  const linesMs = Date.parse(linesAsOf);
  if (!Number.isFinite(linesMs)) return "missing_lines_as_of";

  const modelAsOf = normalizeIsoToken(opts.modelAsOf);
  if (modelAsOf) {
    const modelMs = Date.parse(modelAsOf);
    if (!Number.isFinite(modelMs) || linesMs > modelMs) {
      return "lines_as_of_mismatch";
    }
  }

  const kickoff = normalizeIsoToken(opts.kickoff);
  if (kickoff) {
    const kickMs = Date.parse(kickoff);
    if (!Number.isFinite(kickMs) || linesMs > kickMs) {
      return "lines_as_of_mismatch";
    }
  }

  return "ok";
}

export function nflSurfaceProvenanceFromFairLines(opts: {
  oddsAsOf?: string | null;
  runId?: string | null;
  sha256?: string | null;
  certStatus?: Partial<NflCertStatusByMarket> | null;
}): NflSurfaceProvenance {
  return {
    runId: normalizeIdentityToken(opts.runId),
    sha256: normalizeSha(opts.sha256),
    linesAsOf: linesAsOfFromFairLinesOddsAsOf(opts.oddsAsOf),
    source: "fair",
    certStatus: resolveNflCertStatus(opts.certStatus),
  };
}

export function nflSurfaceProvenanceFromEdgesDesk(opts: {
  marketAsOf?: string | null;
  runId?: string | null;
  sha256?: string | null;
  certStatus?: Partial<NflCertStatusByMarket> | null;
}): NflSurfaceProvenance {
  return {
    runId: normalizeIdentityToken(opts.runId),
    sha256: normalizeSha(opts.sha256),
    linesAsOf: linesAsOfFromEdgesMarketAsOf(opts.marketAsOf),
    source: "desk",
    certStatus: resolveNflCertStatus(opts.certStatus),
  };
}

export function nflSurfaceProvenanceFromAssemble(opts: {
  linesAsOf?: string | null;
  runId?: string | null;
  sha256?: string | null;
  source?: string | null;
  certStatus?: Partial<NflCertStatusByMarket> | null;
}): NflSurfaceProvenance {
  return {
    runId: normalizeIdentityToken(opts.runId),
    sha256: normalizeSha(opts.sha256),
    linesAsOf: linesAsOfFromAssemble(opts.linesAsOf),
    source: opts.source ?? "assemble",
    certStatus: resolveNflCertStatus(opts.certStatus),
  };
}

/**
 * Observed Fair Lines identity for bind. Unbound production emits nulls —
 * do not copy certified-slot placeholders onto observed, and do not invent.
 */
export function nflFairLinesObservedIdentity(opts?: {
  runId?: string | null;
  sha256?: string | null;
}): NflFairLinesCertObserved {
  return {
    runId: normalizeIdentityToken(opts?.runId),
    sha256: normalizeSha(opts?.sha256),
  };
}

/** Q1: Edges binds the SAME Fair Lines certified run — derive-only. */
export function bindNflEdgesToFairLinesCertifiedRun(
  observed: NflFairLinesCertObserved = {},
) {
  return bindNflFairLinesCertifiedRun(observed);
}

export function isNflMarketHardBlocked(
  market: NflFairLinesMarket,
): boolean {
  return market === "total" || market === "ml";
}

/**
 * Independent Edges toggles may only further RESTRICT (AND-gate), never
 * enable (Q2). Defaults are false.
 */
export function isNflEdgesMarketRestrictEnabled(
  market: NflFairLinesMarket,
): boolean {
  if (market === "spread") return NFL_EDGES_PUBLIC_SPREAD_ENABLED;
  if (market === "ml") return NFL_EDGES_PUBLIC_ML_ENABLED;
  return NFL_EDGES_PUBLIC_TOTAL_ENABLED;
}

/**
 * Customer paint for one market (E-1 / X-2). Requires ALL of:
 * Coming Soon off, PUBLIC_ENABLED, inherited Fair Lines gate, shared bind
 * ok, cert_status=CERTIFIED. A successful run_id+sha bind is NOT
 * per-market certification. total/ml stay HARD-BLOCKED.
 */
export function isNflMarketCustomerPaintAllowed(
  market: NflFairLinesMarket,
  observed: NflFairLinesCertObserved = {},
): boolean {
  if (isFootballPublicNumbersDisabled("nfl")) return false;
  if (!NFL_EDGE_BOARD_PUBLIC_ENABLED) return false;
  if (isNflMarketHardBlocked(market)) return false;
  if (resolveNflCertStatus()[market] !== "CERTIFIED") return false;
  if (!isNflFairLinesMarketPublicEnabled(market)) return false;
  return isNflFairLinesCertifiedPublicPaintAllowed(observed, market);
}

/**
 * Edges public paint. Inherit Fair Lines gates, then AND-restrict.
 * Edge-language (PR-4) is not adopted ⇒ edge rows stay blocked (E-2)
 * even after a Fair Lines bind succeeds.
 */
export function isNflEdgesCertifiedPublicPaintAllowed(
  observed: NflFairLinesCertObserved = {},
  market: NflFairLinesMarket = "spread",
): boolean {
  if (!isNflMarketCustomerPaintAllowed(market, observed)) return false;
  if (!isNflEdgesMarketRestrictEnabled(market)) return false;
  if (!NFL_EDGES_EDGE_LANGUAGE_ADOPTED) return false;
  return bindNflEdgesToFairLinesCertifiedRun(observed).ok;
}

/**
 * Edges page / API first gate. Coming Soon remains first. INTERNAL is
 * QA only — not a CLEAR and not certified paint.
 */
export function isNflEdgesCustomerSurfaceClosed(
  observed: NflFairLinesCertObserved = {},
): boolean {
  if (isFootballPublicNumbersDisabled("nfl")) return true;
  // INTERNAL QA may inspect the desk. Not a CLEAR; certified paint stays off.
  if (isNflEdgeBoardInternalOverride()) return false;
  return !isNflEdgesCertifiedPublicPaintAllowed(observed);
}

export function nflCertifiedSlotIdentity(): {
  runId: string | null;
  sha256: string | null;
  certifiedAt: string | null;
} {
  return {
    runId: NFL_FAIR_LINES_CERTIFIED_RUN_ID,
    sha256: NFL_FAIR_LINES_CERTIFIED_SHA256,
    certifiedAt: NFL_FAIR_LINES_CERTIFIED_AT,
  };
}

/** Document-only: Edges-own slots stay null and are never the bind target. */
export function nflEdgesOwnCertifiedSlots(): {
  runId: string | null;
  sha256: string | null;
  certifiedAt: string | null;
} {
  return {
    runId: NFL_EDGES_CERTIFIED_RUN_ID,
    sha256: NFL_EDGES_CERTIFIED_SHA256,
    certifiedAt: NFL_EDGES_CERTIFIED_AT,
  };
}

function identityMissing(value: string | null): boolean {
  return value == null || value === "";
}

/**
 * X-1: exact equality of runId + sha256 + linesAsOf across surfaces that
 * paint a game+market. No tolerance (none frozen). Missing → fail-closed.
 */
export function compareNflSurfaceProvenance(
  a: NflSurfaceProvenance,
  b: NflSurfaceProvenance,
): NflCrossSurfaceCheck {
  if (
    identityMissing(a.runId) ||
    identityMissing(a.sha256) ||
    identityMissing(a.linesAsOf) ||
    identityMissing(b.runId) ||
    identityMissing(b.sha256) ||
    identityMissing(b.linesAsOf)
  ) {
    return { ok: false, reason: "missing_provenance" };
  }
  if (a.runId !== b.runId) {
    return { ok: false, reason: "run_id_mismatch" };
  }
  if (a.sha256 !== b.sha256) {
    return { ok: false, reason: "sha256_mismatch" };
  }
  if (a.linesAsOf !== b.linesAsOf) {
    return { ok: false, reason: "lines_as_of_mismatch" };
  }
  return { ok: true, reason: "ok" };
}

export function assertNflSurfacesAgree(
  surfaces: readonly NflSurfaceProvenance[],
): NflCrossSurfaceCheck {
  if (surfaces.length === 0) {
    return { ok: false, reason: "missing_provenance" };
  }
  const [first, ...rest] = surfaces;
  if (!first) return { ok: false, reason: "missing_provenance" };
  for (const next of rest) {
    const cmp = compareNflSurfaceProvenance(first, next);
    if (!cmp.ok) return cmp;
  }
  return { ok: true, reason: "ok" };
}

/**
 * Server-side check at assemble / desk construction (X-1.2).
 * Compare observed envelope to the certified Fair Lines slot + the
 * per-row linesAsOf. Mismatch / unbound / missing → fail-closed.
 */
export function checkNflObservedAgainstCertifiedSlot(opts: {
  observed: NflSurfaceProvenance;
  rowLinesAsOf?: string | null;
}): NflCrossSurfaceCheck {
  const slot = nflCertifiedSlotIdentity();
  if (identityMissing(slot.runId) || identityMissing(slot.sha256)) {
    return { ok: false, reason: "unbound_certified_slot" };
  }

  const bind = bindNflFairLinesCertifiedRun({
    runId: opts.observed.runId,
    sha256: opts.observed.sha256,
  });
  if (!bind.ok) {
    return { ok: false, reason: bind.reason };
  }

  const row = resolveNflRowLinesAsOf({
    rowLinesAsOf: opts.rowLinesAsOf ?? opts.observed.linesAsOf,
    deskLinesAsOf: opts.observed.linesAsOf,
  });
  if (row.reason !== "ok" || !row.linesAsOf) {
    return { ok: false, reason: row.reason };
  }
  if (opts.observed.linesAsOf && opts.observed.linesAsOf !== row.linesAsOf) {
    return { ok: false, reason: "lines_as_of_mismatch" };
  }

  return { ok: true, reason: "ok" };
}

export type NflEdgesCustomerRow = {
  marketType: "ml" | "spread" | "total" | "props";
  source: "fair-lines" | "edges-today" | "props";
  linesAsOf?: string | null;
};

/**
 * Customer-paint row filter for the Edges desk (E-1 / E-2 / E-3 / X-4).
 * Props omitted (N-1). Edge rows stay blocked after a Fair Lines bind
 * until PR-4 / D-11 is adopted. total/ml hard-blocked. Missing per-row
 * linesAsOf is not inherited from the desk stamp.
 */
export function selectNflEdgesCustomerPaintRows<T extends NflEdgesCustomerRow>(
  rows: readonly T[],
  opts?: {
    observed?: NflSurfaceProvenance;
    bindOk?: boolean;
  },
): T[] {
  const observed = opts?.observed ?? emptyNflSurfaceProvenance("desk");
  const bindOk =
    opts?.bindOk ??
    bindNflEdgesToFairLinesCertifiedRun({
      runId: observed.runId,
      sha256: observed.sha256,
    }).ok;

  const out: T[] = [];
  for (const row of rows) {
    if (row.marketType === "props" || row.source === "props") {
      continue;
    }
    if (row.source === "edges-today") {
      continue;
    }
    if (!NFL_EDGES_EDGE_LANGUAGE_ADOPTED) {
      continue;
    }
    if (row.marketType === "total" || row.marketType === "ml") {
      continue;
    }
    const rowAsOf = resolveNflRowLinesAsOf({
      rowLinesAsOf: row.linesAsOf,
      deskLinesAsOf: observed.linesAsOf,
    });
    if (!rowAsOf.linesAsOf) continue;
    if (!bindOk) continue;
    if (!isNflEdgesCertifiedPublicPaintAllowed(
      { runId: observed.runId, sha256: observed.sha256 },
      row.marketType,
    )) {
      continue;
    }
    const slot = checkNflObservedAgainstCertifiedSlot({
      observed,
      rowLinesAsOf: rowAsOf.linesAsOf,
    });
    if (!slot.ok) continue;
    out.push(row);
  }
  return out;
}

export function nflEdgesDeskIncompleteCopy(): {
  title: string;
  body: string;
} {
  return {
    title: "Desk incomplete",
    body: "Props are unavailable on this desk. Edge rows stay blocked until a separate edge-language rule is adopted. This is not a certified Edges surface and is not a full slate.",
  };
}
