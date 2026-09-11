/**
 * CFB Edge Board current-market acquire.
 *
 * Prod 2026-09-10/11: Vercel-side The Odds API pull yields 0 priced rows
 * (compare `/api/odds/cfb/compare` empty in <400ms — same `getOddsApiKeys()`
 * gate). NFL still prices because assemble reads Railway fair-lines /
 * odds_snapshots (model-service has ODDS_API_KEY).
 *
 * Order: Vercel live pull → Railway current observations → fail closed.
 * July 31 NFT fallback is stale Week 0 and must never paint as current MARKET.
 * Never derive Open/Best from KosEdge Fair/KEI.
 */

import "server-only";

import type { EdgeBoardRow } from "@kosedge/contracts";
import { env } from "@/lib/config/env";
import { loadEdgeBoardFallbackMeta } from "@/lib/edge-board-fallback";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import {
  edgeBoardRowsFromOddsEvents,
  fetchEdgeBoard,
  type OddsEvent,
} from "@/lib/odds-api";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

/** Max age for a CFB market observation to count as current. */
export const CFB_MARKET_MAX_AGE_MS = 6 * 60 * 60 * 1000;

export type CfbMarketSource =
  | "vercel_live"
  | "model_service"
  | "fallback"
  | "none";

export type CfbMarketAcquire = {
  rows: EdgeBoardRow[];
  source: CfbMarketSource;
  capturedAt: string | null;
  reason: string;
};

function parseIsoMs(raw: string | null | undefined): number | null {
  if (raw == null || !String(raw).trim()) return null;
  const ms = Date.parse(String(raw).trim());
  return Number.isFinite(ms) ? ms : null;
}

export function countPricedCfbMarketRows(
  rows: readonly EdgeBoardRow[],
): number {
  return rows.filter((r) => Boolean(r.best || r.open)).length;
}

function latestRowAsOf(rows: readonly EdgeBoardRow[]): string | null {
  let best: string | null = null;
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const row of rows) {
    const raw = (row as { linesAsOf?: string | null }).linesAsOf;
    const ms = parseIsoMs(raw);
    if (ms == null) continue;
    if (ms >= bestMs) {
      bestMs = ms;
      best = String(raw).trim();
    }
  }
  return best;
}

/**
 * Trustworthy *current* CFB market: priced + book vintage within max age.
 * Missing vintage or stale capture → reject (fail closed to no_market).
 */
export function acceptFreshCfbMarketRows(
  rows: readonly EdgeBoardRow[],
  nowMs: number = Date.now(),
  maxAgeMs: number = CFB_MARKET_MAX_AGE_MS,
): { rows: EdgeBoardRow[]; capturedAt: string | null; reason: string } {
  const priced = rows.filter((r) => Boolean(r.best || r.open));
  if (priced.length === 0) {
    return { rows: [], capturedAt: null, reason: "unpriced" };
  }
  const capturedAt = latestRowAsOf(priced);
  const capturedMs = parseIsoMs(capturedAt);
  if (capturedMs == null) {
    return { rows: [], capturedAt: null, reason: "missing_vintage" };
  }
  if (nowMs - capturedMs > maxAgeMs) {
    return { rows: [], capturedAt, reason: "stale" };
  }
  return { rows: [...rows], capturedAt, reason: "ok" };
}

export function loadFreshCfbEdgeBoardFallback(
  nowMs: number = Date.now(),
): CfbMarketAcquire {
  const bundle = loadEdgeBoardFallbackMeta("cfb");
  if (!bundle) {
    return {
      rows: [],
      source: "none",
      capturedAt: null,
      reason: "fallback_missing",
    };
  }
  const accepted = acceptFreshCfbMarketRows(bundle.rows, nowMs);
  if (accepted.reason === "ok") {
    return {
      rows: accepted.rows,
      source: "fallback",
      capturedAt: accepted.capturedAt,
      reason: "ok",
    };
  }
  // Rows may lack per-row linesAsOf — honor bundle capturedAt provenance.
  const bundleMs = parseIsoMs(bundle.capturedAt);
  if (
    accepted.reason === "missing_vintage" &&
    bundleMs != null &&
    nowMs - bundleMs <= CFB_MARKET_MAX_AGE_MS &&
    countPricedCfbMarketRows(bundle.rows) > 0
  ) {
    return {
      rows: bundle.rows,
      source: "fallback",
      capturedAt: bundle.capturedAt,
      reason: "ok",
    };
  }
  const reason =
    bundleMs != null && nowMs - bundleMs > CFB_MARKET_MAX_AGE_MS
      ? "fallback_stale"
      : `fallback_${accepted.reason}`;
  return {
    rows: [],
    source: "none",
    capturedAt: bundle.capturedAt || accepted.capturedAt,
    reason,
  };
}

async function pullVercelLiveCfbRows(): Promise<EdgeBoardRow[]> {
  const keys = getOddsApiKeys();
  for (const key of keys) {
    try {
      const rows = await fetchEdgeBoard("cfb", key);
      if (countPricedCfbMarketRows(rows) > 0) return rows;
    } catch {
      // try next key
    }
  }
  return [];
}

async function pullModelServiceCfbEvents(
  timeoutMs: number,
): Promise<{ events: OddsEvent[]; capturedAt: string | null }> {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) return { events: [], capturedAt: null };
  const url = `${base}/cfb/edge-board-odds`;
  try {
    const res = await upstreamFetch(url, {
      cache: "no-store",
      timeoutMs,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!res.ok) return { events: [], capturedAt: null };
    const payload = (await res.json()) as {
      events?: OddsEvent[];
      captured_at?: string | null;
      capturedAt?: string | null;
    };
    const events = Array.isArray(payload.events) ? payload.events : [];
    const capturedAt =
      (typeof payload.captured_at === "string" && payload.captured_at) ||
      (typeof payload.capturedAt === "string" && payload.capturedAt) ||
      null;
    return { events, capturedAt };
  } catch {
    return { events: [], capturedAt: null };
  }
}

/**
 * Acquire current CFB book observations for Edge Board.
 * Fail closed when no trustworthy current priced row exists.
 */
export async function loadCfbCurrentMarketRows(options?: {
  timeoutMs?: number;
  nowMs?: number;
}): Promise<CfbMarketAcquire> {
  const nowMs = options?.nowMs ?? Date.now();
  const timeoutMs = options?.timeoutMs ?? UPSTREAM_TIMEOUT_MS.pageData;

  const live = await pullVercelLiveCfbRows();
  const liveOk = acceptFreshCfbMarketRows(live, nowMs);
  if (liveOk.reason === "ok") {
    return {
      rows: liveOk.rows,
      source: "vercel_live",
      capturedAt: liveOk.capturedAt,
      reason: "ok",
    };
  }

  const remote = await pullModelServiceCfbEvents(timeoutMs);
  const remoteRows = edgeBoardRowsFromOddsEvents("cfb", remote.events);
  const remoteOk = acceptFreshCfbMarketRows(remoteRows, nowMs);
  if (remoteOk.reason === "ok") {
    return {
      rows: remoteOk.rows,
      source: "model_service",
      capturedAt: remoteOk.capturedAt,
      reason: "ok",
    };
  }

  // Explicit freshness contract — stale shipped snapshot is not current MARKET.
  return loadFreshCfbEdgeBoardFallback(nowMs);
}
