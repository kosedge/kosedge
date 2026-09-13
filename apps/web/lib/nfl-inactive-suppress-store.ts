/**
 * Interim Product store for NFL inactive fair suppress (SOP v1.1).
 *
 * Server-only. SI→builder auto-detect is out of scope.
 *
 * Set a per-game flag (Product owner), then remat success / CoS clear revokes:
 *
 * 1. Edit `data/ops/nfl-inactive-suppress.json` (`games[gameId]`)
 * 2. Or env `NFL_INACTIVE_SUPPRESS_JSON` (inline store JSON)
 * 3. Or env `NFL_INACTIVE_SUPPRESS` (comma-separated gameIds / AWAY@HOME aliases)
 * 4. Or env `NFL_INACTIVE_SUPPRESS_PATH` (alternate JSON file)
 *
 * Canonical gameId: NFL fair-lines / schedule `game_id` (e.g. `2026-W01-ATL@PIT`).
 * Revoke: set `rematRunId` to the remat receipt, or `clearedBy: "cos"`.
 */

import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  emptyNflInactiveSuppressStore,
  NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
  NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
  type NflInactiveSuppressFlag,
  type NflInactiveSuppressStore,
} from "@/lib/nfl-inactive-fair-suppress";

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    if (existsSync(path.join(current, "data", "ops"))) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function defaultStorePath(): string | null {
  const repoRoot = findRepoRoot();
  if (!repoRoot) return null;
  return path.join(repoRoot, "data", "ops", "nfl-inactive-suppress.json");
}

function asRecord(raw: unknown): Record<string, unknown> | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function parseFlag(raw: unknown): NflInactiveSuppressFlag | null {
  const o = asRecord(raw);
  if (!o) return null;
  const markets = Array.isArray(o.markets)
    ? o.markets.map((m) => String(m))
    : undefined;
  const players = Array.isArray(o.players)
    ? o.players.map((p) => String(p))
    : undefined;
  const classes = Array.isArray(o.classes)
    ? o.classes.map((c) => String(c))
    : undefined;
  const aliases = Array.isArray(o.aliases)
    ? o.aliases.map((a) => String(a))
    : undefined;
  return {
    markets,
    reason: typeof o.reason === "string" ? o.reason : undefined,
    players,
    classes,
    setBy: typeof o.setBy === "string" ? o.setBy : undefined,
    setAt: typeof o.setAt === "string" ? o.setAt : undefined,
    ttl:
      typeof o.ttl === "string" || typeof o.ttl === "number"
        ? o.ttl
        : undefined,
    ttlUntil: typeof o.ttlUntil === "string" ? o.ttlUntil : undefined,
    rematRunId:
      o.rematRunId === null
        ? null
        : typeof o.rematRunId === "string"
          ? o.rematRunId
          : undefined,
    clearedBy:
      o.clearedBy === null
        ? null
        : typeof o.clearedBy === "string"
          ? o.clearedBy
          : undefined,
    state:
      o.state === "CLEAR" || o.state === "SUPPRESSED" ? o.state : undefined,
    aliases,
  };
}

function parseGames(raw: unknown): Record<string, NflInactiveSuppressFlag> {
  const o = asRecord(raw);
  if (!o) return {};
  const out: Record<string, NflInactiveSuppressFlag> = {};
  for (const [key, value] of Object.entries(o)) {
    const flag = parseFlag(value);
    if (flag) out[String(key)] = flag;
  }
  return out;
}

export function parseNflInactiveSuppressStore(
  raw: unknown,
): NflInactiveSuppressStore {
  const o = asRecord(raw);
  if (!o) return emptyNflInactiveSuppressStore();
  const games = parseGames(o.games ?? o.nfl_inactive_suppress);
  return {
    version: typeof o.version === "number" ? o.version : 1,
    gameIdConvention: "nfl_fair_line_game_id",
    kickoffBufferMs:
      typeof o.kickoffBufferMs === "number" &&
      Number.isFinite(o.kickoffBufferMs)
        ? o.kickoffBufferMs
        : NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
    games,
  };
}

function storeFromIdList(csv: string): NflInactiveSuppressStore {
  const store = emptyNflInactiveSuppressStore();
  const now = new Date().toISOString();
  for (const token of csv.split(",")) {
    const gameId = token.trim();
    if (!gameId) continue;
    store.games![gameId] = {
      reason: NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
      classes: ["MAJOR"],
      setBy: "product",
      setAt: now,
      rematRunId: null,
    };
  }
  return store;
}

function readJsonFile(filePath: string): unknown | null {
  try {
    return JSON.parse(readFileSync(filePath, "utf8")) as unknown;
  } catch {
    return null;
  }
}

/**
 * Load the durable per-game flag store.
 * Precedence: inline JSON env → comma-id env → path env → repo ops JSON.
 */
export function loadNflInactiveSuppressStore(): NflInactiveSuppressStore {
  const inline = process.env.NFL_INACTIVE_SUPPRESS_JSON?.trim();
  if (inline) {
    try {
      return parseNflInactiveSuppressStore(JSON.parse(inline));
    } catch {
      return emptyNflInactiveSuppressStore();
    }
  }

  const ids = process.env.NFL_INACTIVE_SUPPRESS?.trim();
  if (ids) return storeFromIdList(ids);

  const pathOverride = process.env.NFL_INACTIVE_SUPPRESS_PATH?.trim();
  const filePath = pathOverride || defaultStorePath();
  if (!filePath || !existsSync(filePath)) {
    return emptyNflInactiveSuppressStore();
  }
  const parsed = readJsonFile(filePath);
  return parseNflInactiveSuppressStore(parsed);
}
